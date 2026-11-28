# Protección contra apagar Printable — diseño

## Intención

En la PC del negocio hoy todos usan la misma cuenta de Windows, que es administradora. Cualquier empleado puede cerrar Printable desde el Administrador de tareas y entonces imprimir directo a la Epson o la HP sin que se registre ni se cobre. Luis quiere:

- que un empleado **no pueda** apagar el control, y
- que, si de alguna forma pasa, **quede registrado**.

## Decisiones de Luis

- Se queda con **el servicio vigilado + la auditoría**. **No** se le quitan permisos de impresora al usuario: basta con dirigir la impresión a «Printable» y que el vigilante cancele lo directo.
- Luis creará una cuenta estándar para los empleados. El sistema no crea cuentas.
- Descartado: ocultar el proceso (frágil y los antivirus lo marcan como malware).

## Objetivos

1. **Servicio de Windows «Printable Vigilante»:**
   - Cuenta LocalSystem, inicio automático, recuperación a los 5 s ante caídas, sin límite.
   - Corre la vigilancia de colas (cancelar lo que no lleve `Printable#<id>`), el latido y la auditoría.
   - Una cuenta estándar no puede detenerlo.
2. **La app web** (servidor, carpeta de entrada de clawPDF, ícono junto al reloj) sigue en la sesión del usuario como hoy, así los diálogos del driver siguen funcionando. Si un empleado la cierra no gana nada: el servicio sigue cancelando lo directo. El lanzador ya no arranca el hilo de colas, porque ahora lo hace el servicio.
3. **clawPDF por usuario.** La configuración vive en HKCU, y el instalador corre como administrador. Por eso, al iniciar sesión, cada usuario ejecuta un paso corto que deja configurado clawPDF para su cuenta: autoguardado en la carpeta de entrada, «Printable» como predeterminada y `LegacyDefaultPrinterMode`. El paso es idempotente. Así funciona también en la cuenta estándar.
4. **Auditoría:**
   - **Latido:** el servicio guarda uno cada 30 s en la base de datos. Al arrancar, si el último tiene más de 2 min, registra un «Periodo sin vigilancia» con inicio y fin.
   - **Registro de impresión de Windows:** el instalador activa el log `Microsoft-Windows-PrintService/Operational`. Cada 60 s, y al arrancar para cubrir el periodo sin vigilancia, el servicio lee los eventos 307 (documento impreso). Todo trabajo en una impresora real que no lleve `Printable#<id>` se guarda como «Impresión fuera del sistema»: fecha, impresora, documento, usuario de Windows y páginas. Lo que el vigilante canceló no genera 307.
   - **Alerta:** banner rojo en todas las pantallas mientras haya periodos o impresiones sin revisar. Solo el dueño puede marcarlas como revisadas. Historial muestra la lista y las páginas fuera del sistema del día.
5. **Instalador:**
   - Instala y arranca el servicio (pywin32, Python embebido).
   - Activa el log de PrintService.
   - Pone el paso de clawPDF por usuario en el inicio común.
   - Al final recuerda crear la cuenta estándar y ponerle contraseña a la del dueño.
   - Al desinstalar, detiene y quita el servicio.
   - `verificar` informa además el estado del servicio y si el log está activo.

## Fuera de alcance

- Crear o administrar cuentas de Windows.
- Ocultar procesos.
- Proteger contra alguien que use la cuenta de administrador: puede detener el servicio. La auditoría lo deja registrado.
- Cambiar permisos de impresora.
- CyberPlanet: si vuelve a estar instalado, chocará igual que antes.

## Restricciones

- Windows 10/11 con el Python embebido 3.12 y pywin32 ya incluidos en el instalador.
- Las pruebas de Django no pueden depender de Windows. Lo de servicio, permisos y registro de eventos queda detrás de interfaces con implementación falsa, como `impresora/falso.py`.
- Usuarios de la app sin cambios: el dueño (superusuario) descarta alertas; los empleados solo las ven.

## Enfoques considerados

- **Dos cuentas + servicio + permisos de impresora + auditoría.** Falla cerrado, pero quita los diálogos del driver a la cuenta estándar. Luis lo descartó: no hace falta quitar permisos.
- **Servicio vigilado + auditoría (elegido).** El vigilante no se puede detener desde la cuenta estándar, y todo lo que se escape queda registrado.
- **Solo auditoría.** Informa pero no impide.

## Riesgo

- Leer el log de PrintService y cancelar trabajos desde LocalSystem es lo estándar en Windows, pero hay que confirmarlo en la PC real.

## Para quien lo construya

- Pasos del instalador: nombres, orden, mensajes y detalles del módulo de servicio (pywin32 `ServiceFramework` o `pythonservice.exe`).
- Modelos y pantallas de la auditoría, siguiendo el estilo actual (Historial y banner en base.html).
