# Instalador de un clic — Diseño

Fecha: 2026-11-27 · Autor: Luis Del Orbe (con Claude) · Estado: borrador para aprobación

## 1. Intención

Hoy instalar Printable exige Python, un entorno virtual, `pip`, comandos de Django, configurar el
Programador de tareas y, aparte, instalar y configurar clawPDF a mano (`docs/instalacion.md`).
Luis quiere una instalación suave: **un solo `PrintableSetup.exe`** que deje todo funcionando,
**incluido clawPDF**, sin que la PC tenga Python ni Django.

Decisiones de Luis: Python incluido + Inno Setup (no PyInstaller); el instalador también instala y
configura clawPDF.

## 2. Objetivos

- G1. Doble clic en `PrintableSetup.exe` → Siguiente → Instalar → el sistema queda funcionando y se
  abre en el navegador. Ningún requisito previo salvo Windows 10/11 de 64 bits.
- G2. Instala y configura **clawPDF** en silencio: impresora "Printable", guardado automático en la
  carpeta de entrada del sistema, y "Printable" como impresora predeterminada.
- G3. Arranca solo al iniciar sesión, con un **ícono junto al reloj** (Abrir Printable / Salir).
- G4. **Primer uso guiado**: si no hay usuario, el sistema pide crear uno (sustituye `createsuperuser`).
- G5. **Actualizar = correr el instalador nuevo**; los datos (base, archivos, perfiles, tarifas)
  se conservan.
- G6. El instalador se construye solo en **GitHub Actions** al crear una etiqueta `v*` y queda en
  Releases. Esa misma ejecución **prueba la instalación de verdad** en un Windows.

## 3. No-objetivos

- Firma digital del instalador (requiere comprar un certificado). SmartScreen puede avisar la
  primera vez; se documenta "Más información → Ejecutar de todas formas".
- Actualización automática desde internet.
- Desinstalar clawPDF al desinstalar Printable (puede servir para otras cosas).

## 4. Anti-objetivos

- Que una actualización borre datos.
- Que el instalador deje la PC a medias sin decirlo (por ejemplo, Printable instalado pero clawPDF no
  configurado, y Ctrl+P sigue yendo directo a la impresora).
- Que haya dos copias del servidor corriendo a la vez.

## 5. Diseño

### 5.1 Contenido de `C:\Program Files\Printable`
- `python\`: **Python 3.12 embebible** oficial (amd64), con `import site` activado y las
  dependencias de `requirements-windows.txt` + `pystray` instaladas en `python\Lib\site-packages`.
- `app\`: el código del proyecto, con los estáticos ya recolectados (`collectstatic` al construir).
- `Printable.exe` no existe: los accesos directos apuntan a
  `python\pythonw.exe app\lanzador.py` (sin ventana de consola) con el ícono `printable.ico`.
- `terceros\clawPDF_<versión>_setup.msi` + su licencia (AGPL v3) y el enlace a su código fuente.

### 5.2 Datos en `C:\ProgramData\Printable`
- `db.sqlite3`, `media\`, `entrada\` (+ `rechazados\`), `logs\printable.log` (rotativo), `.clave_secreta`.
- `settings.py` lee `PRINTABLE_DATOS`; si no está definida usa `BASE_DIR` como hoy (desarrollo y
  pruebas no cambian). `CARPETA_ENTRADA` pasa a ser por defecto `<datos>\entrada`.
- El lanzador define `PRINTABLE_DATOS=%ProgramData%\Printable`.
- El instalador crea la carpeta con permiso de modificación para el grupo Usuarios.
- **El desinstalador no borra los datos.** Pregunta si se quieren borrar y por defecto responde No.

### 5.3 Lanzador (`lanzador.py`)
- **Una sola instancia**: si `127.0.0.1:8000` ya responde, solo abre el navegador y termina.
- Si no: migraciones, sincronizar impresoras, vigilante y waitress en un hilo (lo que hace hoy
  `config/servir.py`). Ícono en la bandeja con **pystray**: "Abrir Printable" (acción por defecto) y
  "Salir". Abre el navegador al arrancar si se ejecutó desde el acceso directo
  (`--abrir`), pero no al iniciar sesión.
- Los errores al arrancar se escriben en el log y se muestran en un cuadro de mensaje de Windows.

### 5.4 Primer uso (G4)
- Middleware: si no existe ningún superusuario, cualquier página redirige a `/primer-uso/`.
- Formulario: usuario, contraseña y repetir contraseña (con los validadores de Django). Crea el
  superusuario, inicia sesión y lleva a Impresoras.

### 5.5 Instalador Inno Setup (`instalador/printable.iss`)
Pasos, en orden, todos en modo silencioso y registrados en el log del instalador:
1. Copia `python\`, `app\` y `terceros\`; crea los datos y la carpeta de entrada.
2. Si existe una versión anterior en marcha, la cierra antes de copiar (pregunta).
3. **clawPDF**: `msiexec /i clawPDF_….msi /qn /norestart`, omitido si ya está instalado; luego
   `SetupHelper.exe /Printer=Add /Name=Printable`.
4. **Configuración de clawPDF como el usuario que instala** (`runasoriginaluser`, porque la
   configuración y la impresora predeterminada son por usuario):
   - `clawPDF.exe /Config=<printable-clawpdf.ini>`. El `.ini` se genera al instalar desde una
     plantilla, con guardado automático, carpeta `<datos>\entrada`, nombre
     `<Title>_<DateTime:yyyyMMddHHmmss>`, sin abrir el visor ni mostrar el progreso.
   - Pone "Printable" como impresora predeterminada y desactiva "Permitir que Windows administre
     mi impresora predeterminada".
5. En cada impresora real instalada activa "Iniciar la impresión después de que la última página
   se haya enviado a la cola" (`printui /Xs /n "<impresora>" attributes +queued`).
6. Accesos directos: escritorio ("Printable", con `--abrir`) e Inicio de Windows para todos los
   usuarios (sin `--abrir`).
7. Al terminar: casilla marcada "Abrir Printable ahora".
- Si el paso 3 o el 4 falla, el instalador **termina igual pero muestra un aviso claro**:
  "Printable quedó instalado, pero clawPDF no se pudo configurar; Ctrl+P no llegará al sistema",
  con los pasos manuales. El sistema también lo detecta: si no existe la impresora "Printable",
  la pantalla Imprimir lo avisa.

### 5.6 Construcción y prueba en GitHub Actions (G6)
Flujo `.github/workflows/instalador.yml`, en `windows-latest`, al crear una etiqueta `v*` (y a mano):
1. `instalador/construir.ps1`: descarga Python embebible 3.12 y el MSI de clawPDF, ambos en
   versiones fijas y **verificados por SHA-256**; instala dependencias; copia la app;
   `collectstatic`; compila con Inno Setup (`iscc`).
2. **Pruebas del proyecto en Windows**: `pytest` con el backend real disponible. Por primera vez
   corren las pruebas de `impresora/windows.py` contra "Microsoft Print to PDF".
3. **Prueba de instalación real**:
   - `PrintableSetup.exe /VERYSILENT`.
   - Arrancar el lanzador y comprobar que `http://127.0.0.1:8000` responde.
   - Imprimir una página a "Printable" con PowerShell y comprobar que el PDF llega a la carpeta de
     entrada y aparece como trabajo recibido.
   - Desinstalar y comprobar que los datos siguen ahí.
4. Publicar `PrintableSetup-<versión>.exe` en Releases.

### 5.7 Documentación
`docs/instalacion.md` se reduce a: descargar de Releases → ejecutar → (SmartScreen) → crear usuario.
Los pasos manuales quedan en un anexo "Instalación manual / solución de problemas".

## 6. Riesgos

| Riesgo | Mitigación |
|---|---|
| El formato del `.ini` de clawPDF no es el esperado | Lo valida la prueba de instalación real en Actions (paso 6.3); si falla, ajustar con una configuración exportada desde clawPDF |
| La configuración de clawPDF es por usuario: otro usuario de Windows no la tiene | Una sola PC y un usuario; documentado. El lanzador puede reaplicar el `.ini` si falta la impresora o el perfil |
| El antivirus bloquea `pythonw.exe` | Es el Python oficial firmado por la PSF; se documenta cómo permitirlo |
| Licencia AGPL de clawPDF | Se redistribuye sin modificar, con su licencia y el enlace a su código; Printable es un programa aparte que solo lee archivos PDF |
| El runner de Actions no permite cambiar la impresora predeterminada o instalar drivers | Si un paso no se puede probar ahí, se marca y se verifica a mano en la PC de Luis |

## 7. A criterio de quien lo construya
- Ícono del programa (simple, con los cuatro puntos de tinta).
- Detalles de Inno Setup (idioma español, imágenes, páginas).
- Versión exacta de Python 3.12.x y de clawPDF (la última estable al construir).

## 8. Decisiones tomadas por Claude (para revisar)
1. Datos en `C:\ProgramData\Printable` y la carpeta de entrada dentro de ellos (ya no `C:\printable\entrada`).
2. Inicio automático con un acceso directo en Inicio de Windows (más simple que el Programador de tareas).
3. Ícono junto al reloj con pystray.
4. Primer uso con un formulario propio.
5. El desinstalador conserva los datos salvo que se pida lo contrario.
6. El instalador activa "iniciar después de la última página" en las impresoras reales.
7. La prueba de instalación real corre en GitHub Actions.
