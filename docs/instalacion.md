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

## 5. Primeros pasos

1. **Tarifas** (menú → Tarifas, entra con tu usuario):
   - *Costos de hoja*: pon el costo y el precio mínimo de cada papel y tamaño que vendes.
   - *Costos de tinta*: pon el precio real de tus botellas. El costo por cm² inicial es un estimado; se afina con la calibración.
   - *Configuración*: margen (0.50 = 50 %) y redondeo (1 = al peso, 5 = de 5 en 5).
2. **Perfiles** → *Nuevo perfil*: ponle nombre (ej. "Foto glossy 4x6 alta"), tipo de papel y factor de tinta
   (1.00 documentos, 1.30 fotos en alta calidad). Luego **Abrir preferencias de Epson** y configura igual que en Word.
   Marca uno como **Predeterminado**.
3. **Imprimir**: arrastra el archivo, elige perfil, copias y páginas, revisa el precio y pulsa **Imprimir**.
4. **Calibración**: cada vez que rellenes un tanque, registra la recarga con el precio de la botella.
   Desde la segunda recarga de un color, el sistema sugiere el costo real de esa tinta.

## Si algo falla

- *"No se pudo abrir la impresora"*: revisa que la Epson esté encendida y que el nombre en Windows sea el mismo del perfil.
- Perfil con la insignia **Revisar**: se actualizó el driver; abre las preferencias de ese perfil y vuelve a guardarlas.
- *"No se pudo convertir el Word"*: instala Microsoft Office o LibreOffice.
