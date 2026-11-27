# Instalación en la PC principal (Windows)

## 1. Requisitos

1. **Python 3.12 o más nuevo** desde python.org. En el instalador marca **"Add python.exe to PATH"**.
2. **Driver oficial de la Epson L355** instalado, con una página de prueba que imprima bien desde Windows.
3. Para imprimir archivos Word: **Microsoft Office** o, si no lo tienes, **LibreOffice** (gratis).

## 2. Instalar el sistema

Abre *Símbolo del sistema* en la carpeta del proyecto (por ejemplo `C:\sistema-impresion`):

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements-windows.txt
python manage.py migrate
python manage.py createsuperuser
```

El usuario que crees con `createsuperuser` es el que usarás para entrar en **Tarifas** (el admin).

## 3. Probar que los perfiles conservan las opciones de Epson (una sola vez)

```bat
python scripts\spike_devmode.py
```

1. Se abre la ventana de preferencias de la Epson. Elige **Epson Premium Glossy**, calidad alta,
   tamaño **4x6 sin bordes**, y pulsa **Aceptar**.
2. **Reinicia la PC.**
3. Pon una hoja 4x6 glossy y ejecuta `python scripts\spike_devmode.py --imprimir`.
   Debe salir un degradado y cuatro franjas (cian, magenta, amarillo, negro), sin bordes y en calidad foto.
4. Ejecuta `python scripts\spike_devmode.py --revisar`: la ventana debe mostrar lo que elegiste.

Si algo de esto falla, no sigas: avísame con lo que se ve en la consola.

## 4. Arrancar solo al iniciar sesión

Para que la ventana de Epson pueda aparecer, el sistema **no** se instala como servicio de Windows:
se abre con tu sesión.

1. Abre el **Programador de tareas** → **Crear tarea…**
2. **General:** nombre "Sistema de impresión". Marca **"Ejecutar solo cuando el usuario haya iniciado sesión"**.
3. **Desencadenadores:** Nuevo → **"Al iniciar la sesión"** → tu usuario.
4. **Acciones:** Nuevo → Programa: `C:\sistema-impresion\scripts\iniciar.bat`
   (cambia la ruta si lo pusiste en otra carpeta).
5. **Condiciones:** desmarca "Iniciar la tarea solo si el equipo está conectado a la corriente alterna".
6. Acepta.

`iniciar.bat` arranca el sistema y abre el navegador en `http://127.0.0.1:8000`.
Crea también un acceso directo en el escritorio a esa dirección.

## 5. Impresora virtual «Printable» (Ctrl+P desde cualquier programa)

Con esto, todo lo que se imprima desde Word, un PDF o el navegador llega al sistema en vez de ir
directo al papel.

1. Descarga e instala **clawPDF** (gratis, de código abierto) desde su página oficial en GitHub.
2. Abre **clawPDF → Impresoras** y agrega una impresora llamada exactamente **Printable**.
3. En **Perfiles**, crea uno (por ejemplo "Sistema") y asígnalo a la impresora Printable:
   - **Guardar → Guardado automático: activado.**
   - **Carpeta de destino:** `C:\printable\entrada`
   - **Nombre del archivo:** `<Title>_<DateTime:yyyyMMddHHmmss>`
   - Formato: **PDF**.
   - Desactiva **"Abrir el archivo después de guardar"** y cualquier otra acción posterior.
4. En Windows: **Configuración → Bluetooth y dispositivos → Impresoras y escáneres**:
   - Desactiva **"Permitir que Windows administre mi impresora predeterminada"**.
   - Elige **Printable** → **Establecer como predeterminada**.
5. Si quieres otra carpeta, define la variable de entorno `PRINTABLE_ENTRADA` con la ruta.

## 6. Proteger las impresoras reales

El sistema cancela cualquier trabajo que llegue directo a la Epson o a la HP. Para que lo alcance
antes de que salga papel:

1. En **Impresoras y escáneres**, abre cada impresora real → **Propiedades de impresora** →
   pestaña **Opciones avanzadas**.
2. Marca **"Iniciar la impresión después de que la última página se haya enviado a la cola"**.
3. Acepta. Repite con la otra impresora.

En la pantalla **Impresoras** del sistema (pide tu usuario para cambiar algo) puedes ponerles un nombre corto (por ejemplo "Epson
fotos", "HP emergencia"), elegir la predeterminada y ver cuáles están **controladas**.

## 7. Comprobar que todo funciona

1. Desde Word, **Ctrl+P → Printable → Imprimir**. En unos segundos el documento aparece en
   **Imprimir → Trabajos recibidos**, con su perfil sugerido y su precio.
2. Desde el Bloc de notas, imprime directo a la **HP**. No debe salir papel, y en el sistema
   aparece el aviso "Se bloqueó «…» enviado directo a la HP".
3. Imprime algo desde el sistema en cada impresora: debe salir normalmente.

Si en la prueba 2 llega a salir papel, avísame.

## 8. Primeros pasos

1. **Impresoras**: pulsa "Buscar impresoras", ponles nombre corto y elige la predeterminada.
2. **Tarifas** (menú → Tarifas, entra con tu usuario). Cada impresora tiene sus propias tarifas;
   las de una impresora nueva empiezan en 0:
   - *Costos de hoja*: pon el costo y el precio mínimo de cada papel y tamaño que vendes.
   - *Costos de tinta*: pon el precio real de tus botellas. El costo por cm² inicial es un estimado; se afina con la calibración.
   - *Configuración*: margen (0.50 = 50 %) y redondeo (1 = al peso, 5 = de 5 en 5).
3. **Perfiles** → *Nuevo perfil*: elige la impresora, ponle nombre (ej. "Foto glossy 4x6 alta"), tipo de papel y factor de tinta
   (1.00 documentos, 1.30 fotos en alta calidad). Luego **Abrir preferencias de Epson** y configura igual que en Word.
   Marca uno como **Predeterminado**. En **Uso sugerido** marca un perfil "Para color" y otro
   "Para B/N" en cada impresora: el sistema los sugiere según el documento.
4. **Imprimir**: arrastra el archivo (o usa Ctrl+P → Printable desde cualquier programa), revisa la
   impresora y el perfil sugeridos, elige, copias y páginas, revisa el precio y pulsa **Imprimir**.
5. **Calibración** (por impresora): cada vez que rellenes un tanque, registra la recarga con el precio de la botella.
   Desde la segunda recarga de un color, el sistema sugiere el costo real de esa tinta.

## Si algo falla

- Una impresora aparece **Sin conexión** en la pantalla Impresoras: Windows la reporta apagada,
  sin papel o en modo "sin conexión". Mientras tanto no se ofrece para imprimir.
- Aviso **"No se pudo leer «…»"**: el PDF que llegó por Ctrl+P estaba dañado. Quedó en
  `C:\printable\entrada\rechazados`; vuelve a imprimirlo.
- Aviso **"Las tarifas de esta impresora están en 0"**: llena sus costos en Tarifas.

- *"No se pudo abrir la impresora"*: revisa que la Epson esté encendida y que el nombre en Windows sea el mismo del perfil.
- Perfil con la insignia **Revisar**: se actualizó el driver; abre las preferencias de ese perfil y vuelve a guardarlas.
- *"No se pudo convertir el Word"*: instala Microsoft Office o LibreOffice.
