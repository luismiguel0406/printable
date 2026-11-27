// Contadores regresivos de las consolas, barra de vida, avisos «READY? GO!» y «+30 MIN»,
// pitidos de los últimos 10 segundos y el «GAME OVER» al terminar.
// Todos los sonidos son originales (8 bits, generados con Web Audio): no copian los de ningún juego.
(function () {
  let audio = null;
  const yaSono = new Set(JSON.parse(sessionStorage.getItem("consolas-sonaron") || "[]"));
  const aviso = document.getElementById("activar-sonido");
  const ultimoPitido = {};
  const yaCayo = new Set();  // la caída de «GAME OVER» se ve una sola vez aunque htmx refresque la tarjeta

  function contexto() {
    if (!audio) audio = new (window.AudioContext || window.webkitAudioContext)();
    if (audio.state === "suspended") audio.resume();
    return audio;
  }
  ["click", "keydown"].forEach(ev => document.addEventListener(ev, () => { contexto(); aviso.hidden = true; }, { once: true }));

  function nota(ctx, frecuencia, inicio, duracion, tipo = "square", volumen = 0.12, hasta = null) {
    const osc = ctx.createOscillator(), gan = ctx.createGain();
    osc.type = tipo;
    osc.frequency.setValueAtTime(frecuencia, inicio);
    if (hasta) osc.frequency.exponentialRampToValueAtTime(hasta, inicio + duracion);
    gan.gain.setValueAtTime(volumen, inicio);
    gan.gain.exponentialRampToValueAtTime(0.0001, inicio + duracion);
    osc.connect(gan).connect(ctx.destination);
    osc.start(inicio);
    osc.stop(inicio + duracion + 0.02);
  }

  // Devuelve el contexto listo para sonar, o null (y muestra el aviso) si el navegador lo bloquea.
  function listo() {
    const ctx = contexto();
    if (ctx.state !== "running") { aviso.hidden = false; return null; }
    return ctx;
  }

  function gameOver() {
    const ctx = listo(); if (!ctx) return;
    let t = ctx.currentTime + 0.05;
    // Escalera que baja, un «uuuuh» que se desliza y dos golpes graves.
    [784, 698, 622, 523].forEach(f => { nota(ctx, f, t, 0.16); t += 0.17; });
    nota(ctx, 466, t, 0.9, "square", 0.12, 110); t += 0.95;
    nota(ctx, 98, t, 0.14, "triangle", 0.25); t += 0.2;
    nota(ctx, 73, t, 0.4, "triangle", 0.25);
  }

  function sonidoInicio() {
    const ctx = listo(); if (!ctx) return;
    let t = ctx.currentTime + 0.05;
    // «READY?»: dos notas medias; «GO!»: arpegio que sube.
    nota(ctx, 392, t, 0.12); t += 0.35;
    nota(ctx, 392, t, 0.12); t += 0.45;
    [523, 659, 784, 1047].forEach(f => { nota(ctx, f, t, 0.1, "square", 0.1); t += 0.07; });
    nota(ctx, 1047, t, 0.3, "square", 0.08);
  }

  function sonidoMoneda() {
    const ctx = listo(); if (!ctx) return;
    const t = ctx.currentTime + 0.03;
    nota(ctx, 988, t, 0.07, "square", 0.1);
    nota(ctx, 1319, t + 0.07, 0.35, "square", 0.1);
  }

  function pitido(final) {
    const ctx = listo(); if (!ctx) return;
    nota(ctx, final ? 1175 : 880, ctx.currentTime + 0.01, final ? 0.18 : 0.06, "square", 0.07);
  }

  function texto(ms) {
    const s = Math.max(0, Math.ceil(ms / 1000)), h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), seg = s % 60;
    const dos = n => String(n).padStart(2, "0");
    return h ? `${h}:${dos(m)}:${dos(seg)}` : `${dos(m)}:${dos(seg)}`;
  }

  function vida(tarjeta, el, restante) {
    const barra = tarjeta.querySelector(".vida");
    if (!barra || !el.dataset.inicio) return;
    const total = new Date(el.dataset.fin) - new Date(el.dataset.inicio);
    const fraccion = total > 0 ? Math.max(0, Math.min(1, restante / total)) : 0;
    barra.firstElementChild.style.width = `${(fraccion * 100).toFixed(2)}%`;
    barra.classList.toggle("media", fraccion <= 0.5 && fraccion > 0.2);
    barra.classList.toggle("baja", fraccion <= 0.2);
  }

  function tic() {
    document.querySelectorAll(".contador[data-fin]").forEach(el => {
      const restante = new Date(el.dataset.fin) - Date.now();
      const id = el.dataset.alquiler;
      el.textContent = texto(restante);
      const tarjeta = el.closest(".consola");
      vida(tarjeta, el, restante);
      tarjeta.classList.toggle("ultimos-minutos", restante > 0 && restante <= 5 * 60 * 1000);
      const segundos = Math.ceil(restante / 1000);
      if (segundos > 0 && segundos <= 10 && ultimoPitido[id] !== segundos) {
        ultimoPitido[id] = segundos;
        pitido(false);
      }
      if (restante <= 0) {
        if (yaCayo.has(id)) tarjeta.classList.add("sin-caida");
        tarjeta.classList.add("terminado");
        yaCayo.add(id);
        el.textContent = el.dataset.alTerminar || "00:00";
        if (!yaSono.has(id)) {
          yaSono.add(id);
          sessionStorage.setItem("consolas-sonaron", JSON.stringify([...yaSono]));
          gameOver();
        }
      }
    });
  }

  function mostrarAviso(tarjeta, clase, html, duracion) {
    const caja = tarjeta && tarjeta.querySelector(".aviso-evento");
    if (!caja) return;
    caja.className = "aviso-evento";
    void caja.offsetWidth;  // reinicia la animación
    caja.innerHTML = html;
    caja.style.animationDuration = `${duracion}ms`;
    caja.classList.add(clase);
    setTimeout(() => { caja.className = "aviso-evento"; caja.innerHTML = ""; }, duracion);
  }

  function tarjetaDe(alquiler) {
    const el = document.querySelector(`.contador[data-alquiler="${CSS.escape(alquiler)}"]`);
    return el && el.closest(".consola");
  }

  // Avisos que llegan en la URL después de iniciar o extender.
  function evento() {
    const params = new URLSearchParams(location.search);
    const tipo = params.get("evento"), alquiler = params.get("alquiler");
    if (!tipo || !alquiler) return;
    history.replaceState(null, "", location.pathname);
    const tarjeta = tarjetaDe(alquiler);
    if (tipo === "inicio") {
      mostrarAviso(tarjeta, "listo", "READY?", 900);
      sonidoInicio();
      setTimeout(() => mostrarAviso(tarjeta, "listo", "GO!", 1000), 850);
    } else if (tipo === "extender") {
      const minutos = parseInt(params.get("minutos"), 10) || 0;
      mostrarAviso(tarjeta, "moneda", `<span><span class="moneda-icono"></span>+${minutos} MIN</span>`, 1300);
      sonidoMoneda();
    }
  }

  document.getElementById("probar-sonido").addEventListener("click", gameOver);
  aviso.querySelector("button").addEventListener("click", () => { contexto(); aviso.hidden = true; });
  document.body.addEventListener("htmx:afterSwap", tic);
  setInterval(tic, 250);
  tic();
  evento();
})();
