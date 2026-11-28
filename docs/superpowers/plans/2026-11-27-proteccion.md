# Protección: vigilante como SYSTEM + auditoría — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que un empleado con cuenta estándar no pueda apagar el vigilante de colas, y que todo lo impreso por fuera mientras estuvo apagado quede registrado y alertado.

**Architecture:** Nueva app `auditoria`, con:
- modelos de latido, periodo sin vigilancia e impresión fuera del sistema;
- funciones puras para detectar huecos y filtrar eventos 307 del registro PrintService;
- un `Auditor` con lector inyectable.

Un script `vigilante_servicio.py` corre como SYSTEM (tarea programada al inicio, que se repite cada 5 min sin duplicarse) con el hilo de colas del `Vigilante` y el `Auditor`. La app web (lanzador) deja de vigilar colas. Además:
- un banner global vía context processor;
- el instalador crea la tarea, activa el log, da permisos a Usuarios sobre los datos y configura clawPDF por usuario al iniciar sesión.

**Tech Stack:** Django 5.2, SQLite, pywin32, `wevtutil`, `schtasks` (XML), Inno Setup.

**Spec:** `docs/superpowers/specs/2026-11-27-proteccion-design.md`

## Global Constraints

- Sin quitar permisos de impresora al usuario (decisión de Luis).
- Latido cada 30 s; hueco > 2 min ⇒ «Periodo sin vigilancia».
- Lectura de eventos 307 cada 60 s y, al arrancar, desde el inicio del hueco.
- Solo el dueño (`config.permisos.solo_dueno`) marca alertas como revisadas.
- Las pruebas de Django no dependen de Windows; lo de Windows va detrás de funciones puras o con implementación falsa.
- Textos de la interfaz en español, tono actual.

## Review Focus

1. Evento 307 de un trabajo `Printable#<id> …` ⇒ no es alerta.
2. Evento 307 en la impresora virtual «Printable» o en otra virtual ⇒ no es alerta.
3. El mismo evento leído dos veces (relectura tras reinicio) ⇒ una sola fila (único por `id_registro`).
4. Primera vez sin latido previo (instalación nueva) ⇒ no se crea periodo.
5. Lanzador y servicio a la vez ⇒ el lanzador no cancela colas (solo un vigilante de colas).

---

### Task 1: App `auditoria`: modelos y funciones puras

**Files:**
- Create: `auditoria/__init__.py`, `auditoria/apps.py`, `auditoria/models.py`, `auditoria/servicios.py`, `auditoria/eventos.py`, `auditoria/migrations/0001_initial.py` (makemigrations)
- Modify: `config/settings.py` (INSTALLED_APPS)
- Test: `tests/auditoria/test_auditoria.py`

**Interfaces:**
- Produces:
  - `Latido` (singleton pk=1): `ultimo: DateTimeField(null)`, `eventos_hasta: DateTimeField(null)`.
  - `PeriodoSinVigilancia(inicio, fin, revisado=False)`.
  - `ImpresionFuera(id_registro: BigInteger unique, fecha, impresora, documento, usuario, paginas, revisado=False)`.
  - `servicios.latir(ahora) -> PeriodoSinVigilancia | None`.
  - `servicios.registrar_eventos(eventos: list[EventoImpresion]) -> list[ImpresionFuera]`.
  - `servicios.pendientes() -> int`.
  - `eventos.EventoImpresion(id_registro:int, fecha:datetime, documento:str, usuario:str, impresora:str, paginas:int)`.
  - `eventos.parsear(xml: str) -> list[EventoImpresion]`: la salida de `wevtutil qe … /f:xml` envuelta en `<Eventos>`. Del bloque `UserData/DocumentPrinted` toma Param2 (documento), Param3 (usuario), Param5 (impresora) y Param8 (páginas); de `System` toma `EventRecordID` y `TimeCreated/@SystemTime`.

- [ ] Step 1: tests:
  - `test_primer_latido_no_crea_periodo`
  - `test_hueco_mayor_a_2_min_crea_periodo` (inicio = último latido, fin = ahora)
  - `test_hueco_corto_no_crea_periodo` (90 s)
  - `test_registrar_ignora_trabajos_del_sistema` (documento «Printable#5 foto.jpg»)
  - `test_registrar_ignora_impresoras_virtuales` («Printable», «Microsoft Print to PDF» y una `Impresora(virtual=True)`)
  - `test_registrar_no_duplica` (mismo `id_registro` dos veces ⇒ 1 fila)
  - `test_parsear_evento_307` (XML de muestra con Param2=«Factura.docx», Param3=«Caja», Param5=«EPSON L355 Series», Param8=«3», EventRecordID=812 ⇒ un `EventoImpresion` con esos valores y fecha aware)
  - `test_pendientes_cuenta_no_revisados`
- [ ] Step 2: `pytest tests/auditoria -q`. Expected: falla (no existe el módulo).
- [ ] Step 3: Implementar. Para «virtual» usar `instalador.configurar.es_impresora_real(nombre)` o `Impresora.objects.filter(nombre_windows=…, virtual=True)`.
- [ ] Step 4: `pytest -q`. Expected: todo verde.
- [ ] Step 5: Commit `feat(auditoria): latido, periodos sin vigilancia e impresiones fuera del sistema`.

### Task 2: `Auditor` y lector de Windows

**Files:**
- Create: `auditoria/motor.py`
- Test: `tests/auditoria/test_motor.py`

**Interfaces:**
- Consumes: Task 1.
- Produces:
  - `Auditor(lector: Callable[[datetime], str], reloj=timezone.now)`.
  - `.arrancar()`: latir; leer eventos desde `min(eventos_hasta, inicio del periodo nuevo)`, o desde ahora − 1 día si no hay nada.
  - `.ciclo()`: latir cada vez; leer eventos si pasaron ≥ 60 s desde la última lectura.
  - Actualiza `Latido.eventos_hasta`. Un lector que lanza excepción se registra con log y no tumba el ciclo.
  - `motor.leer_windows(desde: datetime) -> str`: ejecuta `wevtutil qe Microsoft-Windows-PrintService/Operational /q:"*[System[(EventID=307) and TimeCreated[@SystemTime>='<desde ISO Z>']]]" /f:xml` y envuelve la salida en `<Eventos>…</Eventos>`.
  - `motor.comando_wevtutil(desde) -> list[str]`: función pura que se prueba.
- [ ] Step 1: tests:
  - `test_arrancar_tras_hueco_lee_desde_inicio_del_hueco` (el lector falso guarda el `desde` recibido)
  - `test_ciclo_lee_eventos_cada_60s`
  - `test_lector_que_falla_no_rompe`
  - `test_comando_wevtutil_formato` (contiene `EventID=307` y la fecha en UTC con `Z`)
- [ ] Step 2: verlos fallar.
- [ ] Step 3: implementar.
- [ ] Step 4: `pytest -q` verde.
- [ ] Step 5: commit.

### Task 3: Separar el vigilante de colas y el script como SYSTEM

**Files:**
- Modify: `trabajos/vigilancia.py` (`iniciar(self, *, colas=True, carpeta=True)`), `config/servir.py` (`preparar(colas: bool = True)`), `lanzador.py` (llama `preparar(colas=False)`)
- Create: `vigilante_servicio.py` (raíz). Hace:
  - prepara el entorno igual que el lanzador y `django.setup()`, sin migrar;
  - log a `logs/vigilante.log`;
  - `Vigilante(CARPETA_ENTRADA).iniciar(colas=True, carpeta=False)`;
  - `Auditor(leer_windows).arrancar()`;
  - bucle con `ciclo()` cada 30 s;
  - exclusión de instancia única con un mutex con nombre (`Global\PrintableVigilante`) vía `win32event.CreateMutex`: si ya existe, sale con código 0.
- Test: `tests/trabajos/test_vigilancia.py` (agregar)

- [ ] Step 1: tests:
  - `test_iniciar_solo_carpeta_no_crea_hilo_de_colas` (nombres de hilos)
  - `test_preparar_sin_colas` (con monkeypatch de `Vigilante.iniciar`, verificar `colas=False`)
- [ ] Step 2: verlos fallar.
- [ ] Step 3: implementar.
- [ ] Step 4: `pytest -q` verde.
- [ ] Step 5: commit.

### Task 4: Banner y lista en Historial

**Files:**
- Modify: `config/contexto.py` (nuevo `alertas(request)` ⇒ `{"alertas_pendientes": n}` solo si está autenticado), `config/settings.py` (context processor), `templates/base.html` (banner rojo al inicio de `<main>` con enlace a `/historial/#fuera`), `trabajos/views.py` (`historial` agrega `periodos`, `fuera` (últimas 100) y `paginas_fuera_hoy`), `trabajos/templates/trabajos/historial.html` (sección `id="fuera"` con dos tablas y botón «Marcar como revisado» solo si `user.is_superuser`)
- Create: `auditoria/views.py` (`revisar`: POST + `solo_dueno` ⇒ marca todo revisado y redirige a historial), `auditoria/urls.py`, ruta `auditoria/` en `config/urls.py`
- Test: `tests/auditoria/test_vistas.py`

- [ ] Step 1: tests:
  - `test_banner_aparece_con_pendientes`
  - `test_banner_no_aparece_sin_pendientes`
  - `test_historial_lista_impresiones_fuera_y_paginas_de_hoy`
  - `test_empleado_no_puede_revisar` (`cliente_empleado` ⇒ 403 o redirección, sigue pendiente)
  - `test_dueno_revisa_y_banner_desaparece`
- [ ] Step 2: verlos fallar.
- [ ] Step 3: implementar. Texto del banner: «⚠ Hubo impresiones fuera del sistema o el vigilante estuvo apagado. Revisar».
- [ ] Step 4: `pytest -q` verde.
- [ ] Step 5: commit.

### Task 5: Instalador

**Files:**
- Modify: `instalador/configurar.py`, `instalador/printable.iss`, `instalador/probar_instalacion.ps1`, `docs/instalacion.md`
- Create: `instalador/tarea_vigilante.xml.tpl`. Es una plantilla de Task Scheduler:
  - Principal: `S-1-5-18` (SYSTEM), RunLevel HighestAvailable.
  - Triggers: BootTrigger, más un TimeTrigger con Repetition cada PT5M indefinido.
  - Settings: MultipleInstancesPolicy IgnoreNew, `ExecutionTimeLimit` PT0S, `DisallowStartIfOnBatteries` false, `RestartOnFailure` PT1M × 999.
  - Action: `{python}\pythonw.exe "{app}\vigilante_servicio.py"`.
- Test: `tests/instalador/test_configurar.py` (agregar)

**Interfaces:**
- Pasos nuevos de `configurar.py`:
  - `permisos`: `icacls <datos> /grant *S-1-5-32-545:(OI)(CI)M /T`.
  - `vigilante`: genera el XML en `%TEMP%`, ejecuta `schtasks /Create /TN "Printable\Vigilante" /XML <archivo> /F` y luego `schtasks /Run`.
  - `registro`: `wevtutil sl Microsoft-Windows-PrintService/Operational /e:true`.
  - `quitar`: `schtasks /End` + `/Delete /F`.
- Funciones puras probadas: `comando_permisos(d)`, `xml_tarea(python_dir, app_dir) -> str`, `comandos_vigilante(xml_path)`, `comando_registro()`, `comandos_quitar()`.
- `verificar` agrega `vigilante` (resultado de `schtasks /Query /TN "Printable\Vigilante"` con código 0) y `registro_impresion` (`wevtutil gl …` contiene `enabled: true`). Ambos cuentan para `ok`.

- [ ] Step 1: tests:
  - `test_xml_tarea_corre_como_system_y_se_repite` (contiene `S-1-5-18`, `PT5M`, `IgnoreNew`, la ruta de `vigilante_servicio.py`; parsea como XML)
  - `test_comando_permisos_usuarios_modificar`
  - `test_comando_registro`
  - `test_comandos_quitar`
- [ ] Step 2: verlos fallar.
- [ ] Step 3: implementar. En `printable.iss`:
  - Después de «Protegiendo las impresoras reales», agregar los pasos «Permisos de datos para todos los usuarios» (`permisos`), «Activando el registro de impresiones» (`registro`) e «Instalando el vigilante» (`vigilante`), los tres como admin.
  - Nueva entrada `{commonstartup}\Printable Ctrl+P`, con `pythonw configurar.py clawpdf` para cada usuario al iniciar sesión.
  - En `InitializeUninstall`, ejecutar `quitar` antes de `DetenerPrintable`.
  - Mensaje final (`ssDone`, salvo en modo silencioso): «Crea una cuenta estándar de Windows para los empleados y ponle contraseña a la tuya. Así nadie podrá apagar el vigilante.»
  - En `probar_instalacion.ps1`, después de instalar, esperar ≤ 60 s a que exista un proceso `pythonw` corriendo como SYSTEM con `vigilante_servicio.py` en la línea de comando, y a que el latido no sea nulo: `prueba_humo.py latido` devuelve 0 si `Latido.ultimo` tiene menos de 2 min. Agregar ese subcomando a `prueba_humo.py`.
  - En `docs/instalacion.md`, una sección «Cuenta para los empleados» con los pasos de Windows.
- [ ] Step 4: `pytest -q` verde.
- [ ] Step 5: commit, push y correr el workflow (`workflow_dispatch` sobre la rama). Revisar que pasen los pasos de instalación y vigilante. El paso de captura de clawPDF ya falla en CI desde antes y no bloquea.
