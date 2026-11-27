# Control total, perfil sugerido y varias impresoras — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que toda impresión pase por el sistema (Ctrl+P → impresora virtual → bandeja; impresiones directas canceladas), que se sugiera perfil B/N o color, y que se manejen varias impresoras con tarifas propias.

**Architecture:** Nuevo modelo `Impresora` (app `impresora`) del que dependen perfiles, tarifas, recargas y trabajos. Un `Vigilante` (hilo arrancado por `config/servir.py`) captura PDFs de la carpeta de clawPDF y cancela trabajos ajenos en las colas reales mediante dos métodos nuevos del `ControladorImpresora`. La clasificación B/N/color se hace al crear el trabajo y alimenta una función de sugerencia pura.

**Tech Stack:** igual que la v1 (Django 5.2, SQLite, htmx, Pillow, PyMuPDF, pywin32).

**Spec:** `docs/superpowers/specs/2026-11-27-control-total-design.md` (amplía `2026-11-26-sistema-impresion-design.md`)

## Global Constraints

- Todo lo de la v1 sigue vigente (español, RD$ con `Decimal`, solo `impresora/` toca Windows, backend falso en pruebas).
- Prefijo de documento de los trabajos del sistema: `Printable#<id> ` (con espacio), `id` = `Trabajo.pk`.
- `settings.CARPETA_ENTRADA = Path(os.environ.get("PRINTABLE_ENTRADA", r"C:\printable\entrada"))`; rechazados en `CARPETA_ENTRADA / "rechazados"`.
- `settings.IMPRESORAS_VIRTUALES = ["Printable", "Microsoft Print to PDF", "Microsoft XPS Document Writer", "OneNote", "Fax"]` (coincidencia por "contiene", sin mayúsculas).
- Intervalos: carpeta 1 s; colas 0.5 s; sincronizar impresoras 30 s; bandeja htmx cada 3 s.
- Clasificación de color: render a 50 ppp; página color si > 0.5 % de píxeles con `max(R,G,B) − min(R,G,B) > 40`.
- PDF ilegible pasados 60 s → `rechazados/`.

## Review Focus

1. **El vigilante nunca cancela un trabajo del sistema**, aunque el `Trabajo` se esté imprimiendo en ese momento → prueba en Task 5.
2. **PDF a medio escribir** en la carpeta de entrada no se captura → prueba en Task 5.
3. **Impresora desconectada** (HP apagada/desinstalada): queda inactiva, sus perfiles no se ofrecen, nada da error 500 → pruebas en Task 1 y Task 4.
4. **Documento escaneado "B/N" con leve tinte** (grises con ±10 de diferencia entre canales) se clasifica B/N; foto en escala de grises también → prueba en Task 3.
5. **Dos PDFs capturados con el mismo nombre** no se pisan → prueba en Task 5.

---

## Estructura de archivos

```
impresora/models.py, impresora/servicios.py (sincronizar), impresora/admin.py
impresora/base.py (+ TrabajoCola, listar_trabajos, cancelar_trabajo), falso.py, windows.py
impresora/views.py, urls.py, templates/impresora/lista.html       # pantalla Impresoras
perfiles/models.py (FK impresora, uso_sugerido), perfiles/sugerencia.py
tarifas/models.py (FK impresora), precio.py (cargar_tarifas(impresora)), calibracion.py, views.py
trabajos/models.py (impresora, origen, paginas_color, Bloqueo), trabajos/color.py
trabajos/vigilancia.py, trabajos/views.py (+ bandeja, perfiles de impresora), templates
config/servir.py, docs/instalacion.md
```

---

### Task 1: Modelo Impresora y detección

**Files:** Create `impresora/models.py`, `impresora/servicios.py`, `impresora/admin.py`, `impresora/migrations/0001_initial.py`, `0002_epson_inicial.py` · Test `tests/impresora/test_sincronizar.py`

**Interfaces:**
- Produces:
  - `Impresora(nombre_windows: CharField unique, alias: CharField blank, controlada: bool=True, virtual: bool=False, predeterminada: bool=False, activa: bool=True)`; `__str__` → alias o nombre; `Impresora.predeterminada_o_primera() -> Impresora | None` (activas, no virtuales); `Impresora.disponibles()` → QuerySet activas no virtuales.
  - `servicios.es_virtual(nombre: str) -> bool`
  - `servicios.sincronizar_impresoras() -> list[Impresora]` (las creadas); maneja `ErrorImpresora` devolviendo `[]` sin tocar nada.
  - `servicios.marcar_predeterminada(imp: Impresora) -> None`
  - Migración 0002 crea "EPSON L355 Series" (`predeterminada=True`).

- [ ] **Step 1: Pruebas que fallan**

```python
def test_crea_nuevas_y_marca_virtuales(db, controlador_falso):
    controlador_falso.impresoras = ["EPSON L355 Series", "HP DeskJet 2700", "Printable", "Microsoft Print to PDF"]
    creadas = sincronizar_impresoras()
    assert {i.nombre_windows for i in creadas} == {"HP DeskJet 2700", "Printable", "Microsoft Print to PDF"}
    p = Impresora.objects.get(nombre_windows="Printable")
    assert p.virtual and not p.controlada
    assert Impresora.objects.get(nombre_windows="HP DeskJet 2700").controlada

def test_desinstalada_queda_inactiva_y_vuelve(db, controlador_falso):
    controlador_falso.impresoras = ["EPSON L355 Series", "HP DeskJet 2700"]; sincronizar_impresoras()
    controlador_falso.impresoras = ["EPSON L355 Series"]; sincronizar_impresoras()
    assert not Impresora.objects.get(nombre_windows="HP DeskJet 2700").activa
    assert list(Impresora.disponibles().values_list("nombre_windows", flat=True)) == ["EPSON L355 Series"]
    controlador_falso.impresoras = ["EPSON L355 Series", "HP DeskJet 2700"]; sincronizar_impresoras()
    assert Impresora.objects.get(nombre_windows="HP DeskJet 2700").activa

def test_error_del_controlador_no_toca_nada(db, controlador_falso, monkeypatch):
    monkeypatch.setattr(controlador_falso, "listar_impresoras", lambda: (_ for _ in ()).throw(ErrorImpresora("x")))
    assert sincronizar_impresoras() == [] and Impresora.objects.get(nombre_windows="EPSON L355 Series").activa

def test_una_sola_predeterminada(db): ...  # marcar_predeterminada(hp) deja solo hp
```

- [ ] **Step 2:** RED. **Step 3:** Implementar; `ControladorFalso` gana atributo `impresoras: list[str]` (por defecto `[IMPRESORA]`) y `_validar` acepta cualquiera de la lista. **Step 4:** GREEN (suite completa). **Step 5:** Commit `feat: modelo Impresora y detección automática`.

---

### Task 2: Todo depende de la impresora

**Files:** Modify `perfiles/models.py`, `perfiles/servicios.py`, `perfiles/forms.py`, `perfiles/views.py`, templates de perfiles, `tarifas/models.py`, `tarifas/precio.py`, `tarifas/calibracion.py`, `tarifas/views.py`, plantilla de calibración, `tarifas/admin.py`, `trabajos/models.py`, `trabajos/servicios.py`, `trabajos/views.py`, `tests/conftest.py` y pruebas existentes · Create migraciones (perfiles 0002–0003, tarifas 0005, trabajos 0004)

**Interfaces:**
- Consumes: `Impresora` (Task 1).
- Produces:
  - `PerfilImpresion.impresora: FK Impresora PROTECT related_name="perfiles"`; `uso_sugerido: CharField choices ("", "—"), ("color", "Para color"), ("bn", "Para B/N")`, constraint único `(impresora, uso_sugerido)` condicionado a `uso_sugerido != ""`.
  - `CostoTinta`, `CostoHoja`, `RecargaTinta`: `impresora: FK Impresora CASCADE`; únicos `(impresora, canal)` y `(impresora, tipo_papel, tamano)`.
  - `tarifas.servicios.crear_tarifas_para(imp: Impresora) -> None` (4 `CostoTinta` con costo 0 y los `CostoHoja` de la predeterminada con costo 0 / mínimo 0; idempotente). Se llama desde `sincronizar_impresoras` para impresoras no virtuales nuevas.
  - `cargar_tarifas(impresora: Impresora) -> Tarifas`; `cm2_impresos_entre(impresora, canal, desde, hasta)`; `sugerir_costo_cm2(impresora, canal)`.
  - `Trabajo.impresora: FK Impresora SET_NULL null`, `origen: choices ("subido","capturado") default "subido"`, `paginas_color: JSONField list[bool] default list`.
  - Calibración: URLs `tarifas:calibracion` acepta `?impresora=<pk>`; `recarga` y `aplicar` reciben `impresora` (POST / ruta `calibracion/<int:impresora>/<str:canal>/aplicar/`).
  - Toda llamada al controlador usa `perfil.impresora.nombre_windows`.
  - `crear_perfil(nombre, impresora: Impresora, tipo_papel, factor_calidad)`; `NuevoPerfilForm.impresora` = `ModelChoiceField(Impresora.disponibles())`; `EditarPerfilForm` añade `uso_sugerido`.

Migración de perfiles: `AddField impresora_ref` (null) → `RunPython` (crea/obtiene `Impresora` por el texto de `impresora`) → `RemoveField impresora` → `RenameField impresora_ref → impresora` → `AlterField` no nulo. Tarifas/recargas existentes → la Epson.

- [ ] **Step 1: Pruebas que fallan**

```python
def test_tarifas_separadas_por_impresora(db, epson, hp):
    CostoTinta.objects.filter(impresora=hp, canal="K").update(costo_cm2=Decimal("0.5"))
    assert cargar_tarifas(epson).costo_cm2["K"] != cargar_tarifas(hp).costo_cm2["K"]
def test_impresora_nueva_recibe_tarifas_en_cero(db, controlador_falso):
    controlador_falso.impresoras = ["EPSON L355 Series", "HP DeskJet 2700"]; sincronizar_impresoras()
    hp = Impresora.objects.get(nombre_windows="HP DeskJet 2700")
    assert CostoTinta.objects.filter(impresora=hp).count() == 4
    assert CostoHoja.objects.filter(impresora=hp).count() == CostoHoja.objects.filter(impresora__nombre_windows="EPSON L355 Series").count()
def test_uso_sugerido_unico_por_impresora(crear_perfil): ...  # dos "color" en la Epson → IntegrityError; uno "color" en la HP → OK
def test_calibracion_por_impresora(db, epson, hp): ...  # recargas K en hp no afectan sugerir_costo_cm2(epson, "K")
def test_estimar_usa_tarifas_de_la_impresora_del_perfil(perfil_glossy_4x6, perfil_hp, doc_foto): ...  # mismos datos, totales distintos
```

Fixtures nuevas en `tests/conftest.py`: `epson`, `hp` (crea `Impresora` y `crear_tarifas_para`), `crear_perfil(..., impresora=epson)`, `perfil_hp`.

- [ ] **Step 2:** RED. **Step 3:** Implementar y adaptar las pruebas existentes al nuevo FK. **Step 4:** GREEN — suite completa. **Step 5:** Commit `feat: perfiles, tarifas y trabajos por impresora`.

---

### Task 3: Clasificación B/N o color y sugerencia

**Files:** Create `trabajos/color.py`, `perfiles/sugerencia.py` · Test `tests/trabajos/test_color.py`, `tests/perfiles/test_sugerencia.py`

**Interfaces:**
- Produces:
  - `es_color(img: Image.Image) -> bool` (umbral de Global Constraints)
  - `paginas_con_color(doc: Documento) -> list[bool]` (render 50 ppp al tamaño natural de cada página; fotos: 1 elemento)
  - `@dataclass Sugerencia: impresora: Impresora | None, perfil: PerfilImpresion | None, motivo: str`
  - `sugerir(paginas_color: list[bool], paginas: list[int], impresora: Impresora | None = None) -> Sugerencia` — `impresora=None` → `Impresora.predeterminada_o_primera()`; elige perfil `color` si alguna página seleccionada tiene color, si no `bn`, si no el predeterminado de esa impresora, si no el primero. `motivo`: `"Sugerido: B/N — ninguna página tiene color"` / `"Sugerido: Color — páginas 2 y 5"` / `"Sugerido: Color — la imagen tiene color"` (1 página) ; si no hay perfil de ese uso: añade `" (no hay perfil «para B/N» en esta impresora)"`.

- [ ] **Step 1: Pruebas que fallan**

```python
def test_blanco_negro_y_grises(): assert not es_color(Image.new("RGB", (50, 50), (128, 128, 128)))
def test_tinte_leve_es_bn():  # escaneo amarillento
    assert not es_color(Image.new("RGB", (50, 50), (240, 235, 228)))
def test_foto_escala_grises_es_bn(): assert not es_color(Image.linear_gradient("L").convert("RGB"))
def test_logo_pequeno_es_color():
    img = Image.new("RGB", (100, 100), "white"); img.paste((220, 20, 20), (0, 0, 10, 10))  # 1 %
    assert es_color(img)
def test_punto_rojo_minimo_no_cuenta():
    img = Image.new("RGB", (100, 100), "white"); img.paste((220, 20, 20), (0, 0, 2, 2))  # 0.04 %
    assert not es_color(img)
def test_paginas_pdf(): assert paginas_con_color(doc_pdf_mixto) == [False, True]  # fixture nueva mixto.pdf

def test_sugiere_bn(perfil_bn_carta, perfil_glossy_4x6):  # marcados uso bn / color en la Epson
    s = sugerir([False, False], [1, 2]); assert s.perfil == perfil_bn_carta and "ninguna página" in s.motivo
def test_sugiere_color_por_pagina_seleccionada(...):
    assert sugerir([False, True], [2]).perfil == perfil_glossy_4x6
    assert sugerir([False, True], [1]).perfil == perfil_bn_carta
def test_respeta_impresora_elegida(perfil_hp, ...): assert sugerir([True], [1], hp).perfil.impresora == hp
def test_sin_perfil_de_ese_uso_usa_predeterminado(...): ...  # y el motivo lo dice
def test_sin_impresoras(db): assert sugerir([True], [1]) == Sugerencia(None, None, "No hay impresoras disponibles")
```

- [ ] **Step 2:** RED. **Step 3:** Implementar (`ImageChops.lighter/darker`, `point(lambda v: 255 if v > 40 else 0)`, histograma). **Step 4:** GREEN. **Step 5:** Commit `feat: clasificación B/N o color y perfil sugerido`.

---

### Task 4: Pantalla Imprimir con impresora y sugerencia; pantalla Impresoras

**Files:** Modify `trabajos/views.py`, `trabajos/forms.py`, `trabajos/servicios.py`, `trabajos/urls.py`, `trabajos/templates/trabajos/imprimir.html`, `_estimacion.html`, `templates/base.html` · Create `trabajos/templates/trabajos/_perfiles.html`, `impresora/views.py`, `impresora/urls.py`, `impresora/templates/impresora/lista.html` · Test `tests/trabajos/test_views_imprimir.py` (ampliar), `tests/impresora/test_views.py`

**Interfaces:**
- Consumes: `sugerir`, `paginas_con_color`, `Impresora.disponibles()`.
- Produces:
  - Al guardar subida (`_guardar_subida`) se calcula `paginas_color`; `crear_trabajo_desde(ruta: Path, nombre: str, origen: str) -> Trabajo` en `trabajos/servicios.py` (lo usan la subida y el vigilante; normaliza, clasifica, guarda; lanza `ArchivoNoValido`).
  - `OpcionesForm.impresora = ModelChoiceField(Impresora.disponibles(), empty_label=None)`; `perfil` filtrado por impresora (en `__init__` según `data`/`initial`); campo oculto `perfil_manual` ("0"/"1").
  - URL `trabajos:perfiles <pk>` (GET htmx, param `impresora`, `paginas`): devuelve `_perfiles.html` con el `<select>` de perfiles de esa impresora, preseleccionando `sugerir(...)`, y el texto del motivo.
  - En `estimacion`: si `perfil.impresora_id != impresora.pk` → error "El perfil no es de esta impresora"; si `perfil_manual == "0"` se reemplaza el perfil por la sugerencia del rango actual.
  - Miniaturas con etiqueta "Color" / "B/N" por página.
  - `imprimir_trabajo` usa nombre de documento `f"Printable#{trabajo.pk} {trabajo.nombre_original}"` y guarda `trabajo.impresora`.
  - Pantalla `impresora:lista` (`/impresoras/`): tabla con alias (editable), estado (Activa / Desconectada), controlada (sí/no, editable salvo virtuales), botón "Predeterminada", botón "Buscar impresoras" (POST → `sincronizar_impresoras`). Menú: añadir "Impresoras".

- [ ] **Step 1: Pruebas que fallan**

```python
def test_documento_bn_sugiere_perfil_bn(client, perfil_bn_carta, perfil_glossy_4x6):
    subir(client, "una.pdf", ...)  # una.pdf es B/N
    html = client.get(f"/?trabajo={t.pk}").content.decode()
    assert "Sugerido: B/N" in html and f'value="{perfil_bn_carta.pk}" selected' in html
def test_cambiar_impresora_filtra_perfiles(client, trabajo, perfil_hp, perfil_glossy_4x6, hp):
    html = client.get(reverse("trabajos:perfiles", args=[trabajo.pk]), {"impresora": hp.pk}).content.decode()
    assert perfil_hp.nombre in html and perfil_glossy_4x6.nombre not in html
def test_perfil_de_otra_impresora_rechazado(client, trabajo, perfil_hp, epson): ...  # "no es de esta impresora"
def test_impresora_desconectada_no_se_ofrece(client, trabajo, hp): ...  # hp.activa=False → no aparece, sin 500
def test_nombre_documento_lleva_prefijo(client, trabajo_estimado, controlador_falso):
    confirmar(...); assert controlador_falso.impresos[0][3].startswith(f"Printable#{trabajo_estimado.pk} ")
def test_pantalla_impresoras(client, epson, hp): ...  # lista, renombrar alias, marcar predeterminada
```

- [ ] **Step 2:** RED. **Step 3:** Implementar. **Step 4:** GREEN (suite). **Step 5:** Commit `feat: elegir impresora y perfil sugerido al imprimir`.

---

### Task 5: Vigilante — captura de Ctrl+P y bloqueo de impresiones directas

**Files:** Modify `impresora/base.py`, `impresora/falso.py`, `trabajos/models.py` (+ `Bloqueo`), `trabajos/views.py`, `trabajos/urls.py`, templates (bandeja, historial), `config/settings.py`, `config/servir.py` · Create `trabajos/vigilancia.py` · Test `tests/trabajos/test_vigilancia.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) TrabajoCola: id: int, documento: str, usuario: str`
  - Protocol: `listar_trabajos(impresora: str) -> list[TrabajoCola]`, `cancelar_trabajo(impresora: str, id: int) -> None`
  - Falso: `self.colas: dict[str, list[TrabajoCola]]`; `encolar(impresora, documento, usuario="cliente") -> int`; `cancelar_trabajo` lo quita y lo anota en `self.cancelados`.
  - `Bloqueo(impresora: FK Impresora SET_NULL null, impresora_nombre, documento, usuario, fecha auto_now_add, visto: bool=False)`
  - `es_del_sistema(documento: str) -> bool` — regex `^Printable#(\d+) ` y `Trabajo.objects.filter(pk=id).exists()`
  - `class Vigilante`: `__init__(carpeta: Path, controlador)`, `revisar_carpeta(ahora: float) -> list[Trabajo]`, `revisar_colas() -> list[Bloqueo]`, `iniciar() -> None` (hilo daemon con los intervalos de Global Constraints; cada ciclo atrapa y registra excepciones en `logging`, nunca muere), `detener()`.
  - Reglas de `revisar_carpeta`: solo `*.pdf` en la raíz; captura cuando el tamaño es igual al de la revisión anterior **y** > 0 **y** `crear_trabajo_desde` funciona; el original se mueve (no copia) a `media/trabajos/AAAA/MM/` con nombre único (`FileSystemStorage.get_available_name`); `ArchivoNoValido` → se reintenta hasta 60 s desde que se vio por primera vez, luego se mueve a `rechazados/`. Nombre del trabajo: título del PDF (`doc.metadata["title"]`) o nombre del archivo sin el sufijo `_<fecha>` de clawPDF.
  - `config/servir.py`: arranca `Vigilante(settings.CARPETA_ENTRADA, obtener_controlador()).iniciar()` (crea las carpetas) y además llama `sincronizar_impresoras()` cada 30 s desde el mismo hilo.
  - URL `trabajos:bandeja` (GET htmx cada 3 s): trabajos `origen="capturado"`, `estado="estimado"` y `total == 0` (aún sin abrir) + bloqueos `visto=False`; botón "Entendido" marca `visto`.
  - Historial: sección "Impresiones bloqueadas" (últimos 100).

- [ ] **Step 1: Pruebas que fallan**

```python
def test_captura_pdf_estable(db, tmp_path, controlador_falso, settings): 
    copiar("una.pdf", entrada / "Factura_20261127.pdf"); v = Vigilante(entrada, controlador_falso)
    assert v.revisar_carpeta(0) == []          # primera vez: solo mide
    [t] = v.revisar_carpeta(1); assert t.origen == "capturado" and t.total_paginas == 1
    assert not (entrada / "Factura_20261127.pdf").exists()
def test_pdf_a_medio_escribir_no_se_captura(...):
    escribir_mitad(); v.revisar_carpeta(0); completar(); assert v.revisar_carpeta(1) == []  # tamaño cambió
    assert len(v.revisar_carpeta(2)) == 1
def test_pdf_ilegible_va_a_rechazados_tras_60s(...): ...  # a t=30 sigue ahí; a t=61 está en rechazados/
def test_mismo_nombre_dos_veces_no_se_pisa(...): ...  # dos capturas con archivo de igual nombre → dos rutas distintas, ambas existen
def test_bloquea_trabajo_directo(db, epson, controlador_falso):
    controlador_falso.encolar("EPSON L355 Series", "Tarea.docx - Word", "pedro")
    [b] = Vigilante(tmp, controlador_falso).revisar_colas()
    assert b.documento == "Tarea.docx - Word" and controlador_falso.cancelados
def test_no_cancela_trabajos_del_sistema(db, epson, trabajo, controlador_falso):
    controlador_falso.encolar("EPSON L355 Series", f"Printable#{trabajo.pk} foto.jpg")
    assert Vigilante(...).revisar_colas() == [] and not controlador_falso.cancelados
def test_prefijo_con_id_inexistente_se_bloquea(...): ...  # "Printable#99999 x" → bloqueado
def test_no_vigila_no_controladas_ni_virtuales(...): ...
def test_bandeja_muestra_capturados_y_bloqueos(client, ...): ...
```

- [ ] **Step 2:** RED. **Step 3:** Implementar. **Step 4:** GREEN (suite). **Step 5:** Commit `feat: vigilante de Ctrl+P e impresiones directas`.

---

### Task 6: Backend Windows para colas + guía de instalación

**Files:** Modify `impresora/windows.py`, `docs/instalacion.md` · Test `tests/impresora/test_windows.py` (skip fuera de Windows)

**Interfaces:**
- Consumes: Protocol de Task 5.
- Produces: `ControladorWindows.listar_trabajos` con `win32print.EnumJobs(h, 0, 999, 1)` (claves `JobId`, `pDocument`, `pUserName`); `cancelar_trabajo` con `win32print.SetJob(h, id, 0, None, win32print.JOB_CONTROL_DELETE)`; ambos con `@envolver_errores`; `OpenPrinter(nombre, {"DesiredAccess": win32print.PRINTER_ALL_ACCESS})` y, si falla por permisos, `PRINTER_ACCESS_USE` (cancelar trabajos de otros usuarios necesita el primero).

- [ ] **Step 1:** Prueba Windows: `test_listar_trabajos_devuelve_lista` (lista, tipos correctos).
- [ ] **Step 2:** Implementar; `python -m py_compile impresora/windows.py` → OK.
- [ ] **Step 3:** `docs/instalacion.md`: sección "Impresora virtual Printable (clawPDF)": instalar clawPDF; crear impresora "Printable"; perfil con **guardado automático**, carpeta `C:\printable\entrada`, nombre `<Title>_<DateTime:yyyyMMddHHmmss>`; desactivar "abrir el archivo al terminar"; ponerla como predeterminada de Windows (y desactivar "Permitir que Windows administre mi impresora predeterminada"). Sección "Proteger las impresoras reales": en Propiedades → Opciones avanzadas de la Epson y la HP marcar "Iniciar la impresión después de que la última página se haya enviado a la cola". Sección de verificación manual: (a) Ctrl+P desde Word → aparece en la bandeja; (b) imprimir directo a la HP desde el Bloc de notas → no sale papel y aparece el bloqueo; (c) imprimir desde el sistema → sale normalmente.
- [ ] **Step 4:** Suite completa → PASS. **Step 5:** Commit `feat: colas de Windows y guía de clawPDF`.
