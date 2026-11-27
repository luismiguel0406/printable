# Instalador de un clic — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `PrintableSetup.exe` que instala Printable con Python propio, configura clawPDF y arranca solo, construido y probado en GitHub Actions.

**Architecture:** Python 3.12 embebible + dependencias en `{app}\python`, código en `{app}\app`, datos en `%ProgramData%\Printable` (variable `PRINTABLE_DATOS`). Un lanzador con ícono en la bandeja reemplaza a `iniciar.bat`. Un script `instalador/configurar.py` (ejecutado por Inno Setup con el Python incluido) hace los pasos de sistema: datos, clawPDF, impresora predeterminada y colas. Lo que se puede probar en Linux tiene pruebas pytest; lo de Windows se prueba en el workflow `windows-latest`.

**Tech Stack:** Inno Setup 6, Python 3.12 embeddable amd64, pystray, clawPDF MSI, PowerShell, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-27-instalador-design.md`

## Global Constraints

- Sin `PRINTABLE_DATOS`, todo se comporta como hoy (desarrollo y pruebas no cambian).
- Con `PRINTABLE_DATOS=<d>`: base `<d>\db.sqlite3`, `MEDIA_ROOT=<d>\media`, clave `<d>\.clave_secreta`, log `<d>\logs\printable.log` (rotativo, 1 MB × 5), `CARPETA_ENTRADA=<d>\entrada` (salvo `PRINTABLE_ENTRADA`), `STATIC_ROOT` sigue en el código (se recolecta al construir).
- Descargas del build con versión fija y SHA-256 verificado; el build falla si no coincide.
- El desinstalador no borra `%ProgramData%\Printable` salvo confirmación explícita.
- Textos del instalador en español.

## Review Focus

1. **Actualizar sobre una instalación existente** conserva base y archivos → prueba de instalación en Actions (instalar, crear dato, reinstalar, comprobar).
2. **Segunda ejecución del lanzador** con el servidor ya corriendo: solo abre el navegador → prueba en Task 3.
3. **Primer uso con una contraseña débil o que no coincide**: mensaje claro, no crea usuario → prueba en Task 2.
4. **clawPDF no quedó configurado** (no existe la impresora "Printable"): la pantalla Imprimir avisa → prueba en Task 3.
5. **Ruta de datos con espacios o tildes** → prueba en Task 1.

---

### Task 1: Datos fuera del código (`PRINTABLE_DATOS`) y log
**Files:** `config/settings.py` · Test `tests/test_datos.py`
- Pruebas: con `PRINTABLE_DATOS` (ruta con espacio y tilde) recargando settings vía `importlib.reload` en subproceso → rutas esperadas; sin la variable → rutas actuales; `LOGGING` escribe en `<d>\logs`.
- Commit `feat: carpeta de datos configurable para la instalación`.

### Task 2: Primer uso
**Files:** `config/primer_uso.py` (middleware + vista + form), `templates/primer_uso.html`, `config/urls.py`, `config/settings.py` · Test `tests/test_primer_uso.py`
- `PrimerUsoMiddleware`: si no hay superusuario y la ruta no empieza por `/primer-uso/` ni `/static/` → redirige a `/primer-uso/`. Cachea "ya hay usuario" en memoria del proceso cuando es verdad.
- Pruebas: redirige sin usuario; crea usuario + inicia sesión + redirige a `/impresoras/`; contraseña débil o distinta → error y no crea; con usuario existente `/primer-uso/` redirige a `/`; las pruebas existentes no se ven afectadas (fixture autouse crea un superusuario salvo en `test_primer_uso.py`).
- Commit `feat: primer uso guiado`.

### Task 3: Lanzador y aviso de clawPDF
**Files:** `lanzador.py` (raíz), `config/servir.py` (extraer `arrancar_servidor(abrir: bool) -> None` y `servidor_activo(puerto=8000) -> bool`), `trabajos/views.py`, `imprimir.html`, `requirements-windows.txt` (+pystray) · Test `tests/test_lanzador.py`, ampliar `tests/trabajos/test_impresora_y_sugerencia.py`
- `lanzador.main(argv)`: si `servidor_activo()` → abre navegador y retorna 0. Si no, arranca servidor en hilo y el ícono (pystray importado dentro de la función para no requerirlo en Linux).
- Imprimir: si no existe `Impresora(nombre_windows="Printable", activa=True)` → aviso "La impresora virtual Printable no está instalada: Ctrl+P no llegará al sistema".
- Pruebas: `servidor_activo` con un socket escuchando / sin; `main` con servidor activo llama a `webbrowser.open` y no arranca otro; aviso presente/ausente.
- Commit `feat: lanzador con ícono y aviso de clawPDF`.

### Task 4: Configuración de sistema (`instalador/configurar.py`)
**Files:** `instalador/configurar.py`, `instalador/clawpdf.py` · Test `tests/test_configurar.py`
- `clawpdf.valores_perfil(carpeta: Path) -> dict[str, dict[str, str]]`: subclaves de registro → valores para `HKCU\Software\clawSoft\clawPDF\Settings` (perfil 0 con `AutoSave\Enabled=True`, `TargetDirectory`, `EnsureUniqueFilenames=True`, `FileNameTemplate=<Title>_<DateTime:yyyyMMddHHmmss>`, `OpenViewer=False`, `ShowProgress=False`, `SkipPrintDialog=True`, `OutputFormat=Pdf`; mapeo de impresora "Printable" → ese perfil). Prueba pura.
- `configurar.py` subcomandos: `datos` (crea carpetas, migra), `clawpdf` (SetupHelper si falta la impresora, escribe registro, predeterminada, `LegacyDefaultPrinterMode=1`), `colas` (`printui /Xs ... attributes +queued` para cada impresora real), `verificar` (imprime JSON con el estado; código ≠ 0 si falta algo). Funciones de Windows detrás de `sys.platform`.
- Pruebas puras de `valores_perfil` y del armado de comandos (`comando_colas(nombre) -> list[str]`).
- Commit `feat: script de configuración del instalador`.

### Task 5: Build, Inno Setup y workflow
**Files:** `instalador/construir.ps1`, `instalador/printable.iss`, `instalador/printable.ico`, `instalador/probar_instalacion.ps1`, `.github/workflows/instalador.yml`
- Workflow: checkout → construir → `pytest` en Windows → `probar_instalacion.ps1` (instalar `/VERYSILENT`, `configurar.py verificar`, arrancar lanzador, HTTP 200, imprimir a Printable y esperar el PDF en la carpeta de entrada y el trabajo en `/bandeja/`, reinstalar y comprobar que la base sigue, desinstalar y comprobar que los datos quedan) → subir artefacto → Release en etiquetas.
- Verificación: el workflow pasa en GitHub (se itera leyendo `gh run view --log-failed`).
- Commit `build: instalador con Inno Setup y prueba en Windows`.

### Task 6: Documentación
**Files:** `docs/instalacion.md`, `README.md`
- Instalación = descargar de Releases y ejecutar; anexo manual; cómo publicar una versión (`git tag v1.0.0 && git push --tags`).
- Commit `docs: instalación con PrintableSetup.exe`.
