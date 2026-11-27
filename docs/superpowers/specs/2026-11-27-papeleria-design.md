# Papelería — Diseño

Fecha: 2026-11-27 · Estado: aprobado en la conversación

## Intención
Vender los artículos de papelería desde Printable y sumar esas ventas al día. «De momento»: nombre,
precio y vender. Sin inventario, códigos de barra, fiado ni descuentos (quedan para después).

## Diseño
- App `papeleria`: `Articulo(nombre, precio, activo)`, `Venta(fecha, usuario, total, anulada)`,
  `LineaVenta(venta, articulo [SET_NULL], nombre, precio_unitario, cantidad, subtotal)`.
  Las líneas guardan nombre y precio del momento: cambiar el precio no altera ventas viejas.
- Pantalla **Papelería** (`/papeleria/`): buscador sobre los artículos activos; un clic agrega
  (o suma 1); cantidades editables; total; **Cobrar**. Debajo, ventas de hoy y su total.
  El servidor recalcula todo con los precios de la base (no confía en el navegador).
- **Artículos** (`/papeleria/articulos/`, solo el dueño): agregar, editar nombre y precio,
  desactivar o activar. Nombres únicos sin importar mayúsculas; precio ≥ 0.
- **Anular venta**: solo el dueño; no cuenta en los totales.
- **Resumen del día** (`trabajos/resumen.py`): impresiones (trabajos impresos hoy), copias
  (no anuladas) y papelería (no anuladas), por separado y en total. Se muestra en Papelería y en
  Historial. Las consolas se sumarán cuando existan.
- Cantidad por línea: 1–999.

## Decisiones de Claude
1. Catálogo en la página con filtro instantáneo (catálogo pequeño, sin esperas).
2. La venta se arma en el navegador y se envía como `articulo_<id>=<cantidad>`.
3. Anular: solo el dueño (igual que las copias).
