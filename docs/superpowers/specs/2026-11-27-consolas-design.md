# Alquiler de consolas — Diseño

Fecha: 2026-11-27 · Estado: pedido por Luis («seria eso mientras tanto»)

## Intención
Cobrar el alquiler de consolas por **hora o media hora**, con un **contador regresivo** por consola
que al terminar suena un **«game over» de estilo videojuego**. Cada consola muestra **su imagen**;
en reposo, la imagen va de fondo en su tarjeta.

## Diseño
- App `consolas`: `Consola(nombre, imagen, precio_hora, precio_media_hora, activa, orden)` y
  `Alquiler(consola, inicio, fin, minutos, total, estado [activo|terminado|cancelado], terminado_en, usuario)`.
- **Se paga al empezar** (el contador es regresivo). Bloques de 30 minutos, de 30 a 720.
  Precio: `horas × precio_hora + (media hora restante × precio_media_hora)`.
- **Extender** (+30 min / +1 h) suma tiempo y cobro al mismo alquiler. **Terminar** libera la consola
  (no devuelve dinero). **Cancelar** (solo el dueño) anula el cobro.
- Pantalla **Consolas**: una tarjeta por consola.
  - Libre: imagen de fondo y botones «30 min · RD$», «1 h · RD$», «2 h · RD$».
  - Ocupada: contador grande mm:ss sobre la imagen oscurecida, hora de fin, +30 min, +1 h, Terminar.
  - Al llegar a 0: la tarjeta parpadea, dice «Tiempo terminado» y suena el «game over».
  El contador corre en el navegador con la hora de fin del servidor; la página se resincroniza cada 15 s.
- **Sonido**: melodía **original** de 8 bits generada con Web Audio (sin archivos de audio). No se
  usa el sonido de Mario ni de otros juegos (tienen derechos de autor). Si el navegador bloquea el
  sonido hasta que se toque la página, se muestra «Activar sonido».
- **Consolas y precios** (solo el dueño): agregar, editar (nombre, imagen, precios), desactivar.
  Sin imagen se muestra un control de juego dibujado.
- **Hoy en caja** suma las consolas (alquileres de hoy que no estén cancelados).
- Cualquier usuario inicia, extiende y termina. Solo el dueño cancela y cambia consolas o precios.
