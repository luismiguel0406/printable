# Protección contra apagar Printable — diseño

## Intención

En la PC del negocio hoy todos usan la misma cuenta de Windows, que es administradora. Cualquier empleado puede cerrar Printable desde el Administrador de tareas y entonces imprimir directo a la Epson o la HP sin que se registre ni se cobre. Luis quiere:

- que un empleado **no pueda** apagar el control, y
- que, si de alguna forma pasa, **quede registrado**.

## Decisiones de Luis

- **A + C** (elegido en la conversación):
  - **A:** dos cuentas de Windows. La de Luis queda administradora y con contraseña. Una cuenta **estándar** («Caja») queda para el día a día. Printable pasa a correr como servicio de Windows, y solo el servicio tiene permiso de imprimir en las impresoras reales.
  - **C:** auditoría. Printable detecta cuándo estuvo apagado y qué se imprimió por fuera mientras tanto, y lo muestra como alerta.
- Luis crea la cuenta estándar él mismo. El sistema no crea cuentas.
- Descartado: ocultar el proceso. Es frágil y los antivirus lo marcan como malware.

## Objetivos

1. El servidor web y el vigilante corren como **servicio de Windows** («Printable»):
   - Cuenta LocalSystem, inicio automático.
   - Recuperación: reiniciar a los 5 s ante cualquier caída, sin límite de reintentos.
   - Un usuario estándar no puede detenerlo ni matarlo.
2. **Permisos de impresora (falla cerrado).** En cada impresora real (`es_impresora_real`):
   - Se quita «Imprimir» a Everyone y a Usuarios.
   - Quedan con permiso SYSTEM y Administradores.
   - La impresora virtual «Printable» (clawPDF) sigue abierta para todos.
   - Resultado: desde «Caja» solo se puede imprimir a «Printable». Si el servicio no corre, no sale nada en papel.
3. **clawPDF por usuario.** Su configuración vive en HKCU, así que el instalador (que corre como administrador) no alcanza a la cuenta «Caja». Al iniciar sesión, cualquier usuario ejecuta un paso corto que configura clawPDF para su cuenta. Ese paso es idempotente y queda en el inicio común. Así se cubren:
   - autoguardado en la carpeta de entrada,
   - impresora predeterminada «Printable»,
   - `LegacyDefaultPrinterMode`.
   La carpeta `%ProgramData%\Printable\entrada` da permiso de escritura a Usuarios. Las demás carpetas de datos (base de datos, logs) quedan solo para SYSTEM y Administradores.
4. **El ícono junto al reloj** sigue en la sesión del usuario, pero ya no levanta el servidor: solo abre el navegador y muestra si el servicio responde.
5. **Auditoría (C):**
   - **Latido:** el servicio guarda un latido cada 30 s en la base de datos. Al arrancar, si el último latido tiene más de 2 min, se registra un **«Periodo sin control»** con inicio, fin y motivo («apagado / reinicio de la PC / servicio detenido»). El motivo es lo que se pueda saber y, si no, «desconocido».
   - **Registro de impresión de Windows:** el instalador activa el log `Microsoft-Windows-PrintService/Operational`. El servicio lee cada 60 s los eventos 307 (documento impreso) y, al arrancar, los del periodo sin control. Todo trabajo que llegó a una impresora real y que **no** lleva el prefijo `Printable#<id>` queda guardado como «Impresión fuera del sistema». Se guardan fecha, impresora, documento, usuario de Windows y páginas. Si el vigilante ya lo canceló, no cuenta: el 307 solo aparece en trabajos impresos.
   - **Alerta:** banner rojo en todas las pantallas mientras haya periodos o impresiones sin revisar. Lo descarta solo el dueño. Historial muestra la lista y el total de páginas fuera del sistema del día.
6. **Instalador:**
   - Registra y arranca el servicio (con `pywin32`, `win32serviceutil`, sobre el Python embebido).
   - Aplica los permisos de impresora, activa el log de PrintService y ajusta los permisos de carpetas.
   - Muestra al final una nota: «Crea una cuenta estándar para los empleados y pon contraseña a la tuya» (con un enlace a la guía en docs/instalacion.md).
   - Al desinstalar, devuelve los permisos de impresora a los de Windows por defecto.
   - `verificar` informa, además de lo actual, el estado del servicio, los permisos de cada impresora y el log activo.

## Fuera de alcance

- Crear o administrar cuentas de Windows.
- Ocultar procesos.
- Proteger contra alguien que use la cuenta de administrador. Desde esa cuenta todo se puede deshacer, y la auditoría (C) es lo único que lo cubre.
- CyberPlanet: si vuelve a estar instalado, chocará igual que antes.

## Restricciones

- Windows 10/11 con el Python embebido 3.12 y pywin32 ya incluidos en el instalador.
- Las pruebas de Django no pueden depender de Windows. Lo de servicio, permisos y registro de eventos queda detrás de interfaces con implementación falsa, como `impresora/falso.py`.
- Usuarios de la app sin cambios: el dueño (superusuario) descarta alertas; los empleados solo las ven.

## Enfoques considerados

- **A + C: dos cuentas + servicio + permisos + auditoría (elegido).** Es el único que impide de verdad apagar el control. Cuesta preparar una cuenta estándar.
- **B + C: una sola cuenta, servicio con reinicio y «vigilante del vigilante».** Solo frena al curioso, porque un administrador lo detiene igual.
- **Solo C.** No impide nada, solo informa.

## Consecuencias que Luis debe conocer

- **Preferencias del driver (perfiles).** El diálogo nativo de Epson y HP se abre en la sesión del usuario y necesita permiso sobre la impresora. Desde «Caja» ya no se puede abrir. **Crear o editar las preferencias del driver de un perfil se hace desde la cuenta de Luis.** Usar los perfiles para imprimir sigue igual desde «Caja».
- **Imprimir desde la cuenta de Luis** directo a la Epson sigue siendo posible por permisos, pero el vigilante lo cancela como hoy.
- Imprimir desde el servicio (sesión 0) con el driver de la Epson L355: es lo estándar en Windows, pero hay que confirmarlo en la PC real. Si un driver falla en sesión 0, el respaldo es que el servicio delegue la impresión al ícono del reloj del usuario. Eso queda como riesgo, no como trabajo de este diseño.

## Para quien lo construya

- Pasos del instalador: nombres, orden, mensajes y detalles del módulo de servicio (pywin32 `ServiceFramework` o `pythonservice.exe`).
- Cómo aplicar los permisos de impresora: `SetPrinter` nivel 3 con un descriptor de seguridad.
- Modelos y pantallas de la auditoría, siguiendo el estilo actual (Historial y banner en base.html).
