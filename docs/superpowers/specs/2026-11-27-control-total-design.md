# Control total de impresión, perfil sugerido y varias impresoras — Diseño

Fecha: 2026-11-27 · Autor: Luis Del Orbe (con Claude) · Estado: borrador para aprobación
Amplía: `2026-11-26-sistema-impresion-design.md`

## 1. Intención y porqué

Luis revisó la primera versión y pidió tres cambios:

1. **No se puede imprimir fuera del sistema.** Hoy, Ctrl+P en Word o en un PDF va directo a la
   impresora sin cobrarse. Cualquier impresión debe pasar por el sistema.
2. **Perfil sugerido según el color.** Si el documento es B/N o a color, el sistema sugiere el perfil
   adecuado, y el usuario puede elegir otro.
3. **Varias impresoras.** La PC tiene la Epson L355 y una **HP de poca capacidad para emergencias**.
   El sistema debe detectarlas, controlarlas todas y dejar elegir en cuál imprimir.

Decisiones de Luis:
- Ctrl+P se **desvía al sistema** mediante una impresora virtual, en lugar de solo retener el trabajo.
- **Tarifas y calibración separadas por impresora.**
- Impresora virtual: **clawPDF** (gratis, de código abierto, basado en PDFCreator), en modo
  autoguardado (opción A).

## 2. Objetivos

- G7. Todo lo que se imprime con Ctrl+P desde cualquier programa llega al sistema como trabajo,
  con vista previa, perfil sugerido y precio, igual que un archivo subido.
- G8. Cualquier trabajo que llegue directo a una impresora real sin pasar por el sistema se
  **cancela** y queda registrado como bloqueo visible.
- G9. Cada página se clasifica como B/N o color y el sistema preselecciona el perfil adecuado.
- G10. Hay un selector de impresora; los perfiles, las tarifas y la calibración son de cada impresora.
- G11. Las impresoras nuevas de Windows se detectan solas y quedan controladas.

## 3. No-objetivos

- Impedir que un usuario con conocimientos técnicos desactive el sistema (cerrarlo, cambiar
  permisos de Windows). Esto cubre el uso normal del negocio.
- Precio por color de trabajos bloqueados: se cancelan; para imprimirlos se usa Ctrl+P hacia
  "Printable".
- Reportes (siguen pendientes, ya acordado).

## 4. Anti-objetivos

- Que el sistema **cancele sus propios trabajos**.
- Que un trabajo capturado se **pierda** (por ejemplo, porque se leyó el PDF a medio escribir).
- Que se sugiera un perfil de otra impresora, o que se cobre con tarifas de la impresora equivocada.

## 5. Diseño

### 5.1 Impresoras (G10, G11)
Nuevo modelo `Impresora`:
- `nombre_windows` (único)
- `alias`, por ejemplo "Epson fotos" o "HP emergencia"
- `controlada` (bool, por defecto sí)
- `virtual` (bool)
- `predeterminada` (bool, solo una)
- `activa` (sigue instalada en Windows)

Detección: al arrancar y cada 30 s, `listar_impresoras()` crea las que falten. Se marcan como
`virtual` y no controladas las que coinciden con `IMPRESORAS_VIRTUALES` (por defecto: "Printable",
"Microsoft Print to PDF", "Microsoft XPS Document Writer", "OneNote", "Fax"). Las que ya no están
quedan `activa=False`. Una pantalla **Impresoras** permite poner alias y elegir la predeterminada.

Lo que pasa a depender de la impresora:
- `PerfilImpresion.impresora` pasa de texto a FK `Impresora`.
- `CostoTinta`, `CostoHoja` y `RecargaTinta` llevan FK `impresora`, y su unicidad incluye la impresora.
- `Trabajo` lleva FK `impresora`.
- Migración de datos: se crea la `Impresora` "EPSON L355 Series" y todo lo existente se asigna a ella.
  Para una impresora nueva, las tarifas se crean copiando las de la predeterminada con costo 0 y
  precio mínimo 0, y Luis las llena.

### 5.2 Impresora virtual y captura (G7)
- Luis instala **clawPDF** y crea la impresora "Printable" en modo **guardado automático**, en
  `C:\printable\entrada`, con nombre `<Title>_<DateTime>.pdf`. Queda como impresora predeterminada
  de Windows. Los pasos van en `docs/instalacion.md`.
- **Vigilante** (`vigilancia.py`): un hilo que arranca junto con el servidor (`config/servir.py`).
  Cada 1 s revisa la carpeta de entrada:
  - Un PDF se toma solo cuando su tamaño no cambia en 2 lecturas seguidas y se abre bien con
    PyMuPDF; así no se lee a medio escribir.
  - Se mueve a `media/trabajos/AAAA/MM/` y se crea el `Trabajo` con `origen="capturado"`. El nombre
    viene del título del PDF, o del nombre del archivo si no tiene título.
  - Un PDF que no se puede leer después de 60 s se mueve a `entrada/rechazados/` y queda un aviso.
- Pantalla **Imprimir**: una bandeja "Trabajos recibidos" que se actualiza cada 3 s (htmx) con los
  trabajos capturados pendientes. Al abrir uno se ve la misma pantalla que con un archivo subido.

### 5.3 Bloqueo de impresiones directas (G8)
- Cada trabajo que envía el sistema lleva el nombre de documento `Printable#<id> <nombre>`.
- El vigilante revisa cada 0.5 s las colas de las impresoras `controlada=True`
  (`EnumJobs`, nivel 1). Si un trabajo no empieza con `Printable#<id>` de un `Trabajo` existente,
  lo cancela (`SetJob ... JOB_CONTROL_DELETE`) y crea un `Bloqueo` (impresora, documento,
  usuario de Windows, fecha).
- Para tener margen, la guía de instalación indica activar en cada impresora real "Iniciar la
  impresión después de que la última página se haya enviado a la cola". Así el trabajo queda en la
  cola hasta terminar de llegar y el vigilante lo alcanza antes de que salga papel. Se configura a
  mano porque requiere permisos de administrador.
- Los bloqueos se ven como un aviso en la pantalla Imprimir ("Se bloqueó «X» enviado directo a la
  HP: imprímelo con Ctrl+P → Printable") y como una sección del Historial.

### 5.4 B/N o color y perfil sugerido (G9)
- Al crear el trabajo (subido o capturado), cada página se renderiza a 50 ppp y se mide la
  **saturación**: `max(R,G,B) − min(R,G,B)` por píxel. La página es **color** si más del 0.5 % de
  sus píxeles tiene saturación > 40. Se guarda en `Trabajo.paginas_color` (lista de bool).
- `PerfilImpresion.uso_sugerido`: `""`, `"color"` o `"bn"`, con a lo sumo uno de cada uso por
  impresora.
- Sugerencia:
  - Impresora: la predeterminada, o la del último trabajo si sigue activa.
  - Perfil: el `color` de esa impresora si alguna página seleccionada es color; si no, el `bn`; si
    falta, el perfil predeterminado de esa impresora; si tampoco hay, el primero.
- La pantalla muestra "Sugerido: B/N — ninguna página tiene color" o "Sugerido: Color — páginas
  2 y 5", y marca las miniaturas con color. Luis puede cambiar impresora y perfil libremente.
- Si cambia el rango de páginas, la sugerencia se recalcula solo si el usuario no eligió el perfil
  a mano.

### 5.5 Pantalla Imprimir (cambios)
- Selector **Impresora**, con solo las activas y no virtuales. Al cambiarla se recargan sus perfiles
  y se re-sugiere.
- Selector **Perfil**, con solo los de esa impresora.
- El precio usa las tarifas de esa impresora.

## 6. Riesgos

| Riesgo | Mitigación |
|---|---|
| El trabajo directo sale antes de que el vigilante lo cancele | "Iniciar después de la última página" + revisión cada 0.5 s; verificación manual en la PC |
| El vigilante cancela un trabajo del sistema | Prefijo `Printable#<id>` y comprobación de que el `Trabajo` existe; pruebas |
| PDF capturado leído a medio escribir | Tamaño estable en 2 lecturas + apertura correcta |
| clawPDF muestra un diálogo | Guía con la configuración exacta de autoguardado; verificación manual |
| El sistema cerrado = sin control | Arranque automático al iniciar sesión (ya existe) |

## 7. A criterio de quien lo construya
- Estructura del vigilante (hilo único o dos), siempre que exista un backend falso para probarlo.
- Umbrales exactos de saturación (con pruebas sobre páginas B/N, gris y con poco color).
- Diseño visual de la bandeja y los avisos.

## 8. Decisiones tomadas por Claude (para revisar)
1. Las impresoras se detectan solas; las virtuales conocidas no se controlan.
2. Cancelar, no pausar, los trabajos directos; queda registro en `Bloqueo`.
3. La clasificación B/N/color se hace al crear el trabajo, a 50 ppp, con umbral de saturación.
4. Uso sugerido "color" / "bn" como atributo del perfil, uno de cada uno por impresora.
5. La impresora sugerida es la predeterminada, o la del último trabajo.
6. Las tarifas de una impresora nueva se crean en 0 para que Luis las llene.
7. Los PDF capturados que no se pueden leer van a `entrada/rechazados/`.
