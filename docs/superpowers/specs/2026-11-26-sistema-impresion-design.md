# Sistema de impresión local — Diseño

Fecha: 2026-11-26 · Autor: Luis Del Orbe (con Claude) · Estado: borrador para aprobación

## 1. Intención y porqué

Luis quiere un sistema propio, inspirado en CyberPlanet, hecho en Django, para controlar
**totalmente** su impresora desde la PC principal del negocio (la única PC; desde ella se
imprime todo). Hoy tiene dos problemas:

1. **No puede acceder a las "Preferencias de impresora"** desde el flujo que usaba, así que no
   puede subir la calidad ni elegir papel glossy u otros tipos.
2. **No tiene una forma de estimar el precio** de una impresión según el color que lleva
   (cuánta tinta y en qué tamaño).

Ambas cosas son prioridad. Le gustó la idea de **perfiles de impresión guardados**.

Impresora: **Epson L355** (EcoTank, 4 tintas: C, M, Y, K; tamaño máximo A4/Carta).
Archivos de clientes: **fotos (JPG/PNG), PDF y Word**.

## 2. Objetivos

- G1. Abrir la **ventana nativa de preferencias del driver Epson** desde el sistema, con todas
  sus opciones (calidad, tipo de papel, sin bordes, etc.).
- G2. Guardar esa configuración como **perfil con nombre** ("Foto glossy 4x6 alta", "Documento
  B/N borrador") y reutilizarla con un clic, sin volver a abrir la ventana.
- G3. Cargar un archivo (foto, PDF o Word), verlo en vista previa, elegir perfil, copias y
  páginas, y **ver el precio estimado antes de imprimir**.
- G4. El precio se calcula por página según **tamaño del papel, tipo de papel y cobertura de
  cada tinta (C, M, Y, K)**, con tarifas que Luis configura.
- G5. Imprimir **exactamente con la configuración del perfil**.
- G6. Registrar cada trabajo impreso (archivo, perfil, páginas, copias, precio estimado).

## 3. No-objetivos (por ahora)

- Reportes, cierre de caja, ventas de productos (fase posterior, ya acordado).
- Control de tiempo y bloqueo de PCs, cuentas de clientes con saldo (no aplica: una sola PC).
- Pedidos desde celular u otras PCs (la arquitectura no lo impide, ver §6).
- Medición *exacta* de tinta consumida: es una estimación calibrable.

## 4. Anti-objetivos (sería un fracaso aunque "funcione")

- Que un perfil guardado **pierda opciones propias de Epson** (tipo de papel Epson, calidad
  "Foto") y la impresión salga distinta a lo configurado.
- Que el precio mostrado no corresponda a lo que realmente se imprime (otro tamaño, otra escala,
  otras páginas).
- Que usarlo sea más lento que imprimir desde Windows como antes.

## 5. Restricciones

- Windows en la PC principal; impresora Epson L355 instalada con su driver oficial.
- Stack: Python + Django (Luis lo domina).
- La ventana del driver solo puede abrirse desde un proceso que corra **en la sesión de escritorio
  del usuario** (no como servicio de Windows).
- Interfaz en español.

## 6. Enfoques considerados

| Enfoque | Ventajas | Desventajas |
|---|---|---|
| **A. Django local + interfaz web en la misma PC** ✅ | Una sola tecnología; admin de Django; Luis lo domina; puede abrir la ventana nativa de Epson | La ventana de Epson aparece aparte del navegador |
| B. App de escritorio (PySide6) + Django para datos | Más nativa, vista previa integrada | Dos tecnologías; UI más costosa |
| C. Servidor Django + agente de impresión aparte | Permite pedidos desde otros dispositivos | Complejidad innecesaria para una PC |

**Elegido: A** (decisión de Luis). Para llegar a C más adelante, todo el código que toca la
impresora vive en un módulo aislado (`impresora/`), que después puede convertirse en agente.

## 7. Diseño

### 7.1 Ejecución
- Django servido con **waitress** en `127.0.0.1:8000`, arrancado por el **Programador de tareas
  de Windows al iniciar sesión** (corre en la sesión del usuario → puede mostrar la ventana del
  driver). Un acceso directo abre el navegador en esa dirección. *(Decisión de Claude.)*
- Base de datos **SQLite** (una sola PC, un solo operador). *(Decisión de Claude; reemplaza la
  mención anterior de PostgreSQL.)*
- Interfaz con plantillas de Django + **htmx** para actualizar precio y vista previa sin recargar.
  *(Decisión de Claude.)*

### 7.2 Módulos (apps de Django)
- `impresora/` — único lugar que usa `pywin32`: listar impresoras, abrir preferencias,
  serializar/restaurar DEVMODE, imprimir páginas rasterizadas.
- `perfiles/` — modelo `PerfilImpresion`.
- `trabajos/` — carga de archivos, conversión, vista previa, estimación, impresión, historial.
- `tarifas/` — configuración de precios.

### 7.3 Perfiles (G1, G2)
Flujo "Nuevo perfil" / "Editar perfil":
1. El usuario elige impresora y pulsa **"Abrir preferencias de Epson"**.
2. `impresora.abrir_preferencias(nombre, devmode_actual)` llama a
   `win32print.DocumentProperties(..., DM_IN_PROMPT | DM_IN_BUFFER | DM_OUT_BUFFER)` → aparece
   la ventana real del driver. La petición HTTP espera hasta que se cierre.
3. Si el usuario acepta, se guarda el **DEVMODE completo**: campos públicos y la parte privada
   del driver (`DriverData`), donde Epson guarda tipo de papel, calidad "Foto", etc.

Modelo `PerfilImpresion`:
- `nombre`, `impresora` (nombre en Windows), `devmode` (bytes, completo), `version_driver`
- Campos leídos del DEVMODE para mostrar y calcular precio: `tamano_papel`, `color` (sí/no),
  `calidad`, `orientacion`
- `tipo_papel` (FK a `TipoPapel` de tarifas; lo elige el usuario al guardar, porque el tipo de
  papel Epson está en la parte privada y no se puede leer de forma fiable)
- `factor_calidad` (multiplicador de tinta; p. ej. 1.0 normal, 1.3 foto alta)
- `predeterminado` (bool)

Si cambia la versión del driver, el sistema avisa que conviene revisar los perfiles.

### 7.4 Trabajos (G3, G5, G6)
1. **Cargar archivo**: JPG/PNG, PDF, DOC/DOCX.
2. **Normalizar a PDF/imagen**: los Word se convierten a PDF con Word por COM (`docx2pdf`) si hay
   Office instalado; si no, con LibreOffice en modo headless. Las fotos se usan tal cual.
3. **Rasterizar** cada página (PyMuPDF para PDF, Pillow para imágenes) al área imprimible del
   tamaño de papel del perfil. Escalado: **"Ajustar a la página"** por defecto; opción
   **"Tamaño real"** y **"Llenar (recortar)"** para fotos. *(Decisión de Claude.)*
4. **Vista previa**: miniaturas de las páginas tal como se imprimirán.
5. **Opciones**: perfil, copias, rango de páginas.
6. **Precio** (ver §7.5), actualizado al cambiar cualquier opción.
7. **Imprimir**: se crea un DC de la impresora con el DEVMODE del perfil
   (`win32ui.CreateDC` + `CreateDC(... devmode)`), `StartDoc`, y por cada página se dibuja el
   mapa de bits a la resolución de la impresora (`StretchDIBits`). Así lo impreso es **la misma
   imagen** sobre la que se calculó el precio.
8. **Registrar** el `Trabajo`: archivo, perfil usado, páginas, copias, cobertura por página,
   precio estimado, fecha, estado (`impreso` / `error`).

Un solo camino de impresión (todo → imagen → GDI) garantiza que el perfil y el precio
correspondan a lo impreso.

### 7.5 Estimación de precio (G4)
Por página:
1. Rasterizar a ~100–150 ppp (suficiente para medir).
2. Convertir RGB → CMYK con perfil ICC (Pillow `ImageCms`; si no hay ICC disponible,
   conversión simple). Calcular la **cobertura media** de C, M, Y, K (0–100 %).
3. `tinta = Σ_canal (cobertura_canal × área_papel_cm² × costo_tinta_canal_por_cm²) × factor_calidad`
4. `papel = costo_hoja[tipo_papel, tamaño]`
5. `costo = papel + tinta`
6. `precio = max(precio_minimo[tipo_papel, tamaño], costo × (1 + margen))`, redondeado según
   configuración (p. ej. al peso entero).

Total = Σ páginas seleccionadas × copias.

Si el perfil es B/N, toda la cobertura se convierte a K (gris → negro).

**Tarifas configurables** (modelos editables en el admin):
- `TipoPapel`: nombre (Bond, Glossy, Mate, Cartulina…).
- `CostoHoja`: tipo de papel × tamaño → costo por hoja, precio mínimo.
- `CostoTinta`: por canal C, M, Y, K → costo por cm² al 100 % de cobertura.
- `Configuracion`: margen, regla de redondeo, moneda (RD$).

**Calibración** *(decisión de Claude)*: una pantalla para registrar, al rellenar una botella,
cuántas páginas y qué cobertura total se imprimieron con ella; el sistema sugiere un nuevo
`costo_tinta_por_cm²` para ese canal. Hasta entonces se usan valores iniciales a partir del
precio de la botella Epson y su rendimiento declarado.

### 7.6 Interfaz (pantallas)
- **Imprimir** (pantalla principal): arrastrar archivo → vista previa → perfil / copias /
  páginas / escala → desglose del precio → botón Imprimir.
- **Perfiles**: lista, nuevo, editar (abre ventana Epson), duplicar, eliminar, marcar como
  predeterminado.
- **Historial**: trabajos recientes (sin reportes todavía).
- **Tarifas**: vía admin de Django en esta fase.

## 8. Riesgos y primera verificación

| Riesgo | Mitigación |
|---|---|
| El DEVMODE serializado no restaura las opciones privadas de Epson | **Prueba temprana (spike)**: guardar perfil "Glossy foto", reiniciar, imprimir y comprobar en la cola/impresión que se respetó. Si falla, alternativa: guardar el DEVMODE como bytes crudos con `ctypes` |
| La ventana del driver no aparece desde el proceso de Django | Arrancar waitress en la sesión del usuario (no como servicio); si hace falta, pasar el handle de la ventana del escritorio |
| La estimación de tinta difiere de lo real | Factor de calidad por perfil + pantalla de calibración |
| Conversión de Word altera el formato | Preferir Word por COM cuando esté instalado; vista previa antes de imprimir |

## 9. Qué queda a criterio de quien lo construya
- Estructura interna de las apps, nombres exactos de modelos y URLs.
- Resolución exacta para medir cobertura y para imprimir (siempre que respete la del driver).
- Valores iniciales de tarifas (Luis los ajusta en el admin).
- Estilo visual de la interfaz.
- Pruebas: la lógica de precio y cobertura con pruebas unitarias; lo que toca `pywin32` detrás
  de una interfaz que se pueda simular.

## 10. Decisiones tomadas por Claude (para revisar)
1. waitress + Programador de tareas al iniciar sesión (no servicio de Windows).
2. SQLite en vez de PostgreSQL.
3. Plantillas de Django + htmx (sin React).
4. Todo se imprime rasterizado vía GDI para que precio e impresión coincidan.
5. Escalado por defecto "Ajustar a la página".
6. El tipo de papel del perfil se elige a mano para el precio (no se lee del driver).
7. Pantalla de calibración de tinta.
8. Moneda RD$ y redondeo configurable.
