// Contadores regresivos de las consolas y el «game over» al terminar.
// La melodía es original (8 bits, generada con Web Audio): no copia la de ningún juego.
(function () {
  let audio = null;
  const yaSono = new Set(JSON.parse(sessionStorage.getItem("consolas-sonaron") || "[]"));
  const aviso = document.getElementById("activar-sonido");

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

  function gameOver() {
    const ctx = contexto();
    if (ctx.state !== "running") { aviso.hidden = false; return; }
    let t = ctx.currentTime + 0.05;
    // Escalera que baja, un «uuuuh» que se desliza y dos golpes graves.
    [784, 698, 622, 523].forEach(f => { nota(ctx, f, t, 0.16); t += 0.17; });
    nota(ctx, 466, t, 0.9, "square", 0.12, 110); t += 0.95;
    nota(ctx, 98, t, 0.14, "triangle", 0.25); t += 0.2;
    nota(ctx, 73, t, 0.4, "triangle", 0.25);
  }

  function texto(ms) {
    const s = Math.max(0, Math.ceil(ms / 1000)), h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), seg = s % 60;
    const dos = n => String(n).padStart(2, "0");
    return h ? `${h}:${dos(m)}:${dos(seg)}` : `${dos(m)}:${dos(seg)}`;
  }

  function tic() {
    document.querySelectorAll(".contador[data-fin]").forEach(el => {
      const restante = new Date(el.dataset.fin) - Date.now();
      el.textContent = texto(restante);
      const tarjeta = el.closest(".consola");
      tarjeta.classList.toggle("ultimos-minutos", restante > 0 && restante <= 5 * 60 * 1000);
      if (restante <= 0) {
        tarjeta.classList.add("terminado");
        el.textContent = "¡Tiempo!";
        const id = el.dataset.alquiler;
        if (!yaSono.has(id)) {
          yaSono.add(id);
          sessionStorage.setItem("consolas-sonaron", JSON.stringify([...yaSono]));
          gameOver();
        }
      }
    });
  }

  document.getElementById("probar-sonido").addEventListener("click", gameOver);
  aviso.querySelector("button").addEventListener("click", () => { contexto(); aviso.hidden = true; });
  document.body.addEventListener("htmx:afterSwap", tic);
  setInterval(tic, 1000);
  tic();
})();
