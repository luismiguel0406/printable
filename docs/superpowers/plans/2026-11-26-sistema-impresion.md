# Sistema de impresión local — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** App Django local para una PC con Windows que abre las preferencias nativas de la Epson L355, guarda perfiles de impresión, estima el precio por cobertura de tinta e imprime exactamente con el perfil.

**Architecture:** Un solo proyecto Django servido con waitress en `127.0.0.1:8000` dentro de la sesión del usuario. Todo acceso a Windows vive detrás de la interfaz `ControladorImpresora` (`impresora/base.py`), con un backend falso para pruebas y desarrollo en cualquier SO y uno real (`ctypes` + `pywin32` + `Pillow.ImageWin`) para Windows. Cada archivo se normaliza (PDF o imagen), se rasteriza al área imprimible del perfil, se mide la cobertura CMYK de esa misma imagen para el precio y se imprime esa imagen vía GDI.

**Tech Stack:** Python 3.12, Django 5.2 LTS, SQLite, htmx 2 (copiado en `static/`, sin CDN), Pillow, PyMuPDF, pywin32 + docx2pdf (solo Windows), waitress, pytest + pytest-django.

**Spec:** `docs/superpowers/specs/2026-11-26-sistema-impresion-design.md`

## Global Constraints

- Interfaz y mensajes en español; `LANGUAGE_CODE = "es"`, `TIME_ZONE = "America/Santo_Domingo"`.
- Moneda RD$; todo dinero en `Decimal`, nunca `float`.
- Solo el paquete `impresora/` importa `win32*`, `ctypes.windll` o `PIL.ImageWin`. Las pruebas corren en Linux con `IMPRESORA_BACKEND = "falso"`.
- `IMPRESORA_BACKEND` en settings: `"windows"` si `sys.platform == "win32"`, si no `"falso"`; sobreescribible por variable de entorno.
- Resolución de medición de cobertura: `DPI_MEDICION = 100`. Resolución de impresión: `DPI_IMPRESION = 360` (resolución de entrada nativa de Epson; GDI escala al dispositivo).
- Se guarda siempre el **DEVMODE completo en bytes crudos** (público + privado del driver). Antes de imprimir se fuerza `dmCopies = 1`; las copias las controla el sistema.
- El servidor escucha solo en `127.0.0.1`.
- Archivos aceptados: `.jpg .jpeg .png .pdf .doc .docx`. Tamaño máximo de subida: 50 MB.

## Review Focus

1. **Foto con rotación EXIF** (las de celular): debe verse e imprimirse derecha → prueba en Task 6.
2. **Foto horizontal con perfil vertical**: se rota automáticamente para aprovechar la hoja → prueba en Task 6.
3. **PDF corrupto, protegido con contraseña o archivo no soportado**: mensaje claro en pantalla, sin error 500 → pruebas en Task 5 y Task 9.
4. **Rango de páginas inválido** (`"3-1"`, `"0"`, `"9"` en un PDF de 4 páginas, `"a"`): error de validación con mensaje → prueba en Task 8.
5. **Falla al imprimir** (impresora apagada/desconectada, perfil de otra impresora): el trabajo queda con estado `error` y mensaje visible, sin cobrar como impreso → prueba en Task 9.

---

## Estructura de archivos

```
manage.py, pyproject.toml, requirements.txt, requirements-windows.txt
config/settings.py, config/urls.py
static/js/htmx.min.js, templates/base.html
impresora/
  base.py        # dataclasses + Protocol ControladorImpresora
  devmode.py     # leer/modificar campos públicos de DEVMODEW en bytes (puro Python)
  papeles.py     # tamaños conocidos y reconocimiento por mm
  falso.py       # backend falso
  windows.py     # backend real
  __init__.py    # obtener_controlador()
tarifas/  models.py admin.py precio.py calibracion.py views.py urls.py migrations/
perfiles/ models.py forms.py servicios.py views.py urls.py templates/perfiles/
trabajos/ models.py conversion.py raster.py cobertura.py rangos.py servicios.py views.py urls.py templates/trabajos/
scripts/spike_devmode.py, scripts/iniciar.bat
docs/instalacion.md
tests/ (uno por módulo)
```

---

### Task 1: Proyecto base y tarifas

**Files:**
- Create: `manage.py`, `config/settings.py`, `config/urls.py`, `pyproject.toml`, `requirements.txt`, `requirements-windows.txt`, `templates/base.html`, `static/js/htmx.min.js`
- Create: `tarifas/models.py`, `tarifas/admin.py`, `tarifas/migrations/0001_initial.py`, `tarifas/migrations/0002_datos_iniciales.py`
- Test: `tests/tarifas/test_models.py`

**Interfaces:**
- Produces:
  - `TipoPapel(nombre: CharField unique)`
  - `CostoHoja(tipo_papel: FK TipoPapel, tamano: CharField, costo: Decimal, precio_minimo: Decimal)`, único `(tipo_papel, tamano)`
  - `CostoTinta(canal: CharField choices "C","M","Y","K" unique, costo_cm2: Decimal(max_digits=12, decimal_places=8), precio_botella: Decimal, rendimiento_paginas: int)`
  - `Configuracion` (singleton, `Configuracion.obtener() -> Configuracion`): `margen: Decimal` (0.50 = 50 %), `redondeo: Decimal` (1.00 = al peso), `moneda: CharField = "RD$"`

- [ ] **Step 1:** Crear proyecto `config`, apps `tarifas`, `perfiles`, `trabajos`, `impresora` (esta sin modelos). Settings según Global Constraints; `pyproject.toml` con `[tool.pytest.ini_options] DJANGO_SETTINGS_MODULE = "config.settings"`. `requirements.txt`: Django>=5.2,<6, Pillow, PyMuPDF, waitress, pytest, pytest-django. `requirements-windows.txt`: `-r requirements.txt`, pywin32, docx2pdf. `base.html` con menú: Imprimir, Perfiles, Historial, Tarifas (admin), Calibración.
- [ ] **Step 2: Pruebas que fallan**

```python
def test_configuracion_obtener_es_singleton(db):
    a = Configuracion.obtener(); b = Configuracion.obtener()
    assert a.pk == b.pk and Configuracion.objects.count() == 1

def test_costo_hoja_unico_por_papel_y_tamano(db):
    bond = TipoPapel.objects.get(nombre="Bond")
    with pytest.raises(IntegrityError):
        CostoHoja.objects.create(tipo_papel=bond, tamano="Carta", costo=1, precio_minimo=1)  # ya sembrado

def test_datos_iniciales(db):
    assert set(TipoPapel.objects.values_list("nombre", flat=True)) >= {"Bond", "Glossy", "Mate", "Cartulina"}
    assert CostoTinta.objects.count() == 4
    k = CostoTinta.objects.get(canal="K")
    # costo_cm2 = precio_botella / (rendimiento * area_carta_cm2 * 0.05)
    assert k.costo_cm2 == (k.precio_botella / (Decimal(k.rendimiento_paginas) * Decimal("603.22") * Decimal("0.05"))).quantize(Decimal("0.00000001"))
```

- [ ] **Step 3:** Run `pytest tests/tarifas -v` → FAIL.
- [ ] **Step 4:** Implementar modelos, admin (todos editables) y migración de datos. Valores iniciales (Luis los ajusta en el admin): botellas Epson 664 a RD$600; rendimiento K 4000 páginas, C/M/Y 6500; cobertura de referencia 5 % sobre Carta (603.22 cm²). `CostoHoja` para Bond/Glossy/Mate/Cartulina × Carta, A4, 4x6, 5x7 con costo 0 y precio mínimo 0 (a llenar). Margen 0.50, redondeo 1.00.
- [ ] **Step 5:** `pytest tests/tarifas -v` → PASS.
- [ ] **Step 6:** Commit `feat: proyecto base y modelos de tarifas`.

---

### Task 2: Interfaz de impresora, DEVMODE y tamaños de papel

**Files:**
- Create: `impresora/base.py`, `impresora/devmode.py`, `impresora/papeles.py`, `impresora/falso.py`, `impresora/__init__.py`
- Test: `tests/impresora/test_devmode.py`, `tests/impresora/test_papeles.py`, `tests/impresora/test_falso.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) InfoPapel: ancho_mm: float, alto_mm: float, imprimible_x_mm: float, imprimible_y_mm: float, imprimible_ancho_mm: float, imprimible_alto_mm: float` (del DC del dispositivo; con sin bordes el imprimible = hoja)
  - `@dataclass(frozen=True) CamposDevmode: tamano_codigo: int, ancho_decimas_mm: int, alto_decimas_mm: int, orientacion: int, calidad: int, color: bool, copias: int, version_driver: int`
  - `class ErrorImpresora(Exception)`
  - `class ControladorImpresora(Protocol)`:
    - `listar_impresoras() -> list[str]`
    - `devmode_predeterminado(impresora: str) -> bytes`
    - `abrir_preferencias(impresora: str, devmode: bytes) -> bytes | None` (None = canceló)
    - `info_papel(impresora: str, devmode: bytes) -> InfoPapel`
    - `version_driver(impresora: str) -> str`
    - `imprimir(impresora: str, devmode: bytes, paginas: Iterable[Image.Image], nombre_documento: str) -> None` (lanza `ErrorImpresora`)
  - `devmode.leer_campos(raw: bytes) -> CamposDevmode`; `devmode.con_copias(raw: bytes, copias: int) -> bytes` (lanza `ValueError` si `len(raw) < 220`)
  - `papeles.TAMANOS: dict[str, tuple[float, float]]` = Carta (215.9, 279.4), A4 (210, 297), Oficio (215.9, 355.6), 4x6 (101.6, 152.4), 5x7 (127, 177.8), 8x10 (203.2, 254)
  - `papeles.reconocer(ancho_mm: float, alto_mm: float) -> str` → nombre o `"Personalizado"`; tolerancia ±2 mm; acepta orientación invertida.
  - `impresora.obtener_controlador() -> ControladorImpresora` (según `settings.IMPRESORA_BACKEND`)
  - `ControladorFalso`: una impresora `"EPSON L355 Series"`; `abrir_preferencias` devuelve el devmode recibido con `calidad` cambiada a 600 (o `None` si `self.cancelar = True`); `imprimir` guarda `self.impresos: list[tuple[str, bytes, list[Image], str]]` y lanza `ErrorImpresora("Impresora desconectada")` si `self.fallar = True`. Los cambios a `cancelar`/`fallar` aplican a la instancia que devuelve `obtener_controlador()` (en el backend falso es un singleton por proceso; las pruebas lo reinician con un fixture).

Layout de DEVMODEW (offsets en bytes, little-endian): `dmDriverVersion` 66 (WORD), `dmSize` 68, `dmDriverExtra` 70, `dmOrientation` 76 (short), `dmPaperSize` 78, `dmPaperLength` 80, `dmPaperWidth` 82, `dmCopies` 86, `dmPrintQuality` 90, `dmColor` 92 (1 = mono, 2 = color).

- [ ] **Step 1: Pruebas que fallan**

```python
def _raw(**campos) -> bytes:  # helper de prueba: 220 bytes + 40 privados, con struct.pack_into en los offsets de arriba
    ...

def test_leer_campos():
    c = leer_campos(_raw(paper=1, length=2794, width=2159, orient=1, quality=-4, color=2, copies=3, drv=0x0400))
    assert c == CamposDevmode(1, 2159, 2794, 1, -4, True, 3, 0x0400)

def test_con_copias_no_toca_parte_privada():
    raw = _raw(copies=5); nuevo = con_copias(raw, 1)
    assert leer_campos(nuevo).copias == 1 and nuevo[220:] == raw[220:] and len(nuevo) == len(raw)

def test_devmode_corto():
    with pytest.raises(ValueError): leer_campos(b"\x00" * 10)

@pytest.mark.parametrize("w,h,esperado", [(215.9, 279.4, "Carta"), (279.4, 215.9, "Carta"), (101, 153, "4x6"), (100, 100, "Personalizado")])
def test_reconocer(w, h, esperado): assert reconocer(w, h) == esperado

def test_falso_imprimir_y_fallar(controlador_falso):
    controlador_falso.fallar = True
    with pytest.raises(ErrorImpresora): controlador_falso.imprimir("EPSON L355 Series", b"x" * 260, [], "doc")
```

- [ ] **Step 2:** `pytest tests/impresora -v` → FAIL.
- [ ] **Step 3:** Implementar. `devmode.py` usa solo `struct`. Fixture `controlador_falso` en `tests/conftest.py` que reinicia el singleton.
- [ ] **Step 4:** `pytest tests/impresora -v` → PASS.
- [ ] **Step 5:** Commit `feat: interfaz de impresora, devmode y tamaños`.

---

### Task 3: Backend real de Windows + prueba en la PC (spike)

**Files:**
- Create: `impresora/windows.py`, `scripts/spike_devmode.py`
- Test: `tests/impresora/test_windows.py` (todo con `pytest.mark.skipif(sys.platform != "win32")`)

**Interfaces:**
- Consumes: `ControladorImpresora`, `InfoPapel`, `ErrorImpresora`, `con_copias` (Task 2)
- Produces: `ControladorWindows` implementando el Protocol.

Implementación (decisiones fijas):
- `listar_impresoras`: `win32print.EnumPrinters(PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS)`.
- `devmode_predeterminado` y `abrir_preferencias`: `ctypes.windll.winspool.DocumentPropertiesW` con `OpenPrinter`. Primero con `fMode=0` para saber el tamaño, buffer `ctypes.create_string_buffer(n)`, luego `DM_OUT_BUFFER` (y para preferencias `DM_IN_PROMPT | DM_IN_BUFFER | DM_OUT_BUFFER` con el devmode de entrada y `hWnd = user32.GetForegroundWindow()`). Retorno `IDOK (1)` → bytes del buffer; `IDCANCEL (2)` → `None`; negativo → `ErrorImpresora`.
- `info_papel`: `gdi32.CreateDCW(None, impresora, None, buffer)`; `GetDeviceCaps` con `PHYSICALWIDTH(110)`, `PHYSICALHEIGHT(111)`, `PHYSICALOFFSETX(112)`, `PHYSICALOFFSETY(113)`, `HORZRES(8)`, `VERTRES(10)`, `LOGPIXELSX(88)`, `LOGPIXELSY(90)` → mm; `DeleteDC`.
- `imprimir`: DC igual que arriba con `con_copias(devmode, 1)`; `win32ui.CreateDCFromHandle(hdc)`; `StartDoc(nombre_documento)`; por página `StartPage`, `PIL.ImageWin.Dib(img).draw(hdc, (0, 0, HORZRES, VERTRES))`, `EndPage`; `EndDoc`. Cualquier excepción → `AbortDoc` y `ErrorImpresora(str(e))`.
- `version_driver`: `win32print.GetPrinter(h, 2)["DriverName"]` + `GetPrinterDriver(h, None, 2)["Version"]` → `"<nombre> v<versión>"`.

- [ ] **Step 1:** Prueba (solo Windows): `test_devmode_predeterminado_tiene_tamano_correcto`: `len(raw) == dmSize + dmDriverExtra` leídos del mismo raw.
- [ ] **Step 2:** Implementar `ControladorWindows`.
- [ ] **Step 3:** Escribir `scripts/spike_devmode.py`: (a) abre preferencias de `"EPSON L355 Series"`, (b) guarda bytes en `spike_perfil.bin`, (c) en una segunda ejecución con `--imprimir` lee el archivo, imprime una imagen de prueba (degradado de colores 4x6 a `DPI_IMPRESION`) e imprime en consola `leer_campos` e `info_papel`.
- [ ] **Step 4: Verificación manual de Luis en su PC** (bloqueante para Task 7): en la ventana elegir *Epson Premium Glossy*, calidad alta y 4x6 sin bordes; cerrar; reiniciar la PC; correr `python scripts/spike_devmode.py --imprimir`. Esperado: sale en glossy con calidad alta y sin bordes, y la ventana de preferencias, abierta otra vez con ese devmode, muestra lo elegido. Si falla, parar y reportar antes de seguir.
- [ ] **Step 5:** Commit `feat: backend de impresión para Windows y spike`.

---

### Task 4: Cobertura de tinta y precio

**Files:**
- Create: `trabajos/cobertura.py`, `tarifas/precio.py`
- Test: `tests/trabajos/test_cobertura.py`, `tests/tarifas/test_precio.py`

**Interfaces:**
- Consumes: modelos de Task 1.
- Produces:
  - `@dataclass(frozen=True) Cobertura: c: float, m: float, y: float, k: float` (0–1)
  - `medir_cobertura(img: Image.Image, monocromo: bool) -> Cobertura`
  - `@dataclass(frozen=True) Tarifas: costo_cm2: dict[str, Decimal], costo_hoja: dict[tuple[str, str], tuple[Decimal, Decimal]], margen: Decimal, redondeo: Decimal`; `cargar_tarifas() -> Tarifas`
  - `@dataclass(frozen=True) PrecioPagina: papel: Decimal, tinta: Decimal, costo: Decimal, precio: Decimal`
  - `precio_pagina(cob: Cobertura, area_cm2: Decimal, tipo_papel: str, tamano: str, factor_calidad: Decimal, t: Tarifas) -> PrecioPagina` (lanza `KeyError` con mensaje si falta `CostoHoja`)

Conversión RGB→CMYK (fija; sin ICC en esta fase — decisión del plan: el spec admite la conversión simple como respaldo y la calibración absorbe la diferencia):

```
K = 1 - max(R,G,B); si K == 1: C=M=Y=0; si no: C=(1-R-K)/(1-K), M=(1-G-K)/(1-K), Y=(1-B-K)/(1-K)
monocromo: K = 1 - luminancia(L de Pillow)/255, C=M=Y=0
```

Fórmula de precio (exacta del spec): `tinta = Σ cob_canal × area_cm2 × costo_cm2[canal] × factor_calidad`; `costo = papel + tinta`; `precio = max(precio_minimo, costo × (1 + margen))` redondeado **hacia arriba** al múltiplo de `redondeo`.

- [ ] **Step 1: Pruebas que fallan**

```python
def test_blanco(): assert medir_cobertura(Image.new("RGB", (10, 10), "white"), False) == Cobertura(0, 0, 0, 0)
def test_negro(): assert medir_cobertura(Image.new("RGB", (10, 10), "black"), False) == Cobertura(0, 0, 0, 1)
def test_cian(): assert medir_cobertura(Image.new("RGB", (10, 10), (0, 255, 255)), False) == Cobertura(1, 0, 0, 0)
def test_mitad_negra():
    img = Image.new("RGB", (10, 10), "white"); img.paste((0, 0, 0), (0, 0, 5, 10))
    assert medir_cobertura(img, False).k == pytest.approx(0.5)
def test_monocromo_rojo_va_a_k():
    cob = medir_cobertura(Image.new("RGB", (4, 4), (255, 0, 0)), True)
    assert cob.c == cob.m == cob.y == 0 and cob.k == pytest.approx(1 - 76 / 255, abs=0.01)
def test_rgba_transparente_es_blanco():
    assert medir_cobertura(Image.new("RGBA", (4, 4), (0, 0, 0, 0)), False).k == 0

T = Tarifas(costo_cm2={"C": D("0.01"), "M": D("0.01"), "Y": D("0.01"), "K": D("0.02")},
            costo_hoja={("Glossy", "4x6"): (D("10"), D("25"))}, margen=D("0.5"), redondeo=D("5"))
def test_precio():
    p = precio_pagina(Cobertura(0.5, 0.5, 0.5, 0.1), D("154.84"), "Glossy", "4x6", D("1.3"), T)
    # tinta = (0.5*0.01*3 + 0.1*0.02) * 154.84 * 1.3 = 0.017 * 154.84 * 1.3 = 3.421964
    assert p.tinta == pytest.approx(D("3.421964"), abs=D("0.000001"))
    assert p.precio == D("25")          # 13.42 * 1.5 = 20.13 < mínimo 25
def test_precio_redondea_hacia_arriba():
    p = precio_pagina(Cobertura(1, 1, 1, 1), D("154.84"), "Glossy", "4x6", D("1"), T)
    assert p.precio % D("5") == 0 and p.precio >= p.costo * D("1.5")
def test_falta_costo_hoja():
    with pytest.raises(KeyError, match="Bond.*Carta"): precio_pagina(Cobertura(0,0,0,0), D("1"), "Bond", "Carta", D("1"), T)
```

- [ ] **Step 2:** Run → FAIL. **Step 3:** Implementar (cobertura con `numpy` no está en el stack: usar `Image.split()` + `ImageStat`/aritmética de bandas de Pillow; RGBA se compone sobre blanco). **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: medición de cobertura y cálculo de precio`.

---

### Task 5: Normalización de archivos

**Files:**
- Create: `trabajos/conversion.py`
- Test: `tests/trabajos/test_conversion.py` (+ `tests/fixtures/`: `una.pdf` 1 página, `cuatro.pdf`, `protegido.pdf`, `roto.pdf`, `foto.jpg`)

**Interfaces:**
- Produces:
  - `class ArchivoNoValido(Exception)` (mensaje en español para el usuario)
  - `@dataclass Documento: ruta: Path, tipo: Literal["pdf", "imagen"], paginas: int`
  - `normalizar(ruta: Path, destino: Path) -> Documento`
  - `convertir_word_a_pdf(ruta: Path, destino: Path) -> Path`: intenta `docx2pdf.convert` (si importable y hay Word); si no, `soffice --headless --convert-to pdf --outdir destino ruta` (busca `soffice` en PATH y en `C:\Program Files\LibreOffice\program\`); si ninguno → `ArchivoNoValido("No se pudo convertir el Word: instala Microsoft Office o LibreOffice")`.

- [ ] **Step 1: Pruebas que fallan**

```python
def test_pdf_cuenta_paginas(tmp_path): assert normalizar(FIX / "cuatro.pdf", tmp_path) == Documento(FIX / "cuatro.pdf", "pdf", 4)
def test_foto(tmp_path): assert normalizar(FIX / "foto.jpg", tmp_path).tipo == "imagen"
@pytest.mark.parametrize("nombre,msg", [("protegido.pdf", "contraseña"), ("roto.pdf", "dañado"), ("x.txt", "no soportado")])
def test_invalidos(tmp_path, nombre, msg):
    with pytest.raises(ArchivoNoValido, match=msg): normalizar(FIX / nombre, tmp_path)
def test_word_usa_convertidor(tmp_path, monkeypatch):
    monkeypatch.setattr(conversion, "convertir_word_a_pdf", lambda r, d: FIX / "una.pdf")
    assert normalizar(FIX / "doc.docx", tmp_path).paginas == 1
```

- [ ] **Step 2:** Run → FAIL. **Step 3:** Implementar con PyMuPDF (`doc.needs_pass`, `fitz.FileDataError`) y `Image.open(...).verify()`. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: normalización de fotos, PDF y Word`.

---

### Task 6: Rasterizado al área imprimible

**Files:**
- Create: `trabajos/raster.py`
- Test: `tests/trabajos/test_raster.py`

**Interfaces:**
- Consumes: `Documento` (Task 5), `InfoPapel` (Task 2)
- Produces:
  - `Escala = Literal["ajustar", "real", "llenar"]`
  - `rasterizar(doc: Documento, papel: InfoPapel, escala: Escala, dpi: int, paginas: list[int]) -> Iterator[Image.Image]` — `paginas` 1-based; cada imagen RGB blanca de `round(imprimible_ancho_mm / 25.4 * dpi) × round(imprimible_alto_mm / 25.4 * dpi)` con el contenido centrado.

Reglas: fotos con `ImageOps.exif_transpose`; si la orientación del contenido (horizontal/vertical) no coincide con la del área imprimible, rotar 90° antes de escalar (en `ajustar` y `llenar`); `ajustar` = cabe completo sin deformar; `llenar` = cubre todo y recorta lo que sobra centrado; `real` = foto a su DPI EXIF (300 si no tiene), PDF a 72 pt/pulgada, recortado si no cabe. PDF se renderiza con `page.get_pixmap(dpi=...)` a la resolución que da el tamaño final.

- [ ] **Step 1: Pruebas que fallan**

```python
PAPEL_4x6 = InfoPapel(101.6, 152.4, 0, 0, 101.6, 152.4)
def test_tamano_lienzo():
    img = next(rasterizar(doc_foto(400, 600), PAPEL_4x6, "ajustar", 100, [1]))
    assert img.size == (400, 600)
def test_exif_rotada_sale_derecha(tmp_path):
    # foto 600x400 con EXIF Orientation=6 → contenido real vertical 400x600; marca roja arriba en el contenido real
    img = next(rasterizar(foto_exif_6(tmp_path), PAPEL_4x6, "ajustar", 100, [1]))
    assert img.getpixel((200, 5))[0] > 200 and img.getpixel((200, 595))[0] < 50
def test_horizontal_en_perfil_vertical_se_rota():
    img = next(rasterizar(doc_foto(600, 400, "black"), PAPEL_4x6, "ajustar", 100, [1]))
    assert img.getpixel((200, 300)) == (0, 0, 0) and img.getpixel((200, 5)) == (0, 0, 0)  # ocupa la hoja
def test_ajustar_no_deforma():
    img = next(rasterizar(doc_foto(100, 100, "black"), PAPEL_4x6, "ajustar", 100, [1]))
    assert img.getpixel((200, 10)) == (255, 255, 255)  # bandas blancas arriba/abajo
def test_llenar_cubre_todo():
    img = next(rasterizar(doc_foto(100, 100, "black"), PAPEL_4x6, "llenar", 100, [1]))
    assert ImageStat.Stat(img.convert("L")).mean[0] == 0
def test_pdf_paginas_seleccionadas():
    assert len(list(rasterizar(doc_pdf("cuatro.pdf"), PAPEL_CARTA, "ajustar", 50, [2, 4]))) == 2
```

- [ ] **Step 2:** Run → FAIL. **Step 3:** Implementar. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: rasterizado con escalado y rotación`.

---

### Task 7: Perfiles de impresión

**Files:**
- Create: `perfiles/models.py`, `perfiles/forms.py`, `perfiles/servicios.py`, `perfiles/views.py`, `perfiles/urls.py`, `perfiles/templates/perfiles/{lista,form}.html`
- Test: `tests/perfiles/test_servicios.py`, `tests/perfiles/test_views.py`

**Interfaces:**
- Consumes: `obtener_controlador`, `leer_campos`, `reconocer`, `TipoPapel`.
- Produces:
  - `PerfilImpresion`: `nombre` (unique), `impresora`, `devmode: BinaryField`, `version_driver`, `tamano: CharField`, `ancho_mm`, `alto_mm`, `imprimible_x_mm`, `imprimible_y_mm`, `imprimible_ancho_mm`, `imprimible_alto_mm` (FloatField), `color: bool`, `calidad: int`, `orientacion: int`, `tipo_papel: FK TipoPapel PROTECT`, `factor_calidad: Decimal default 1.00`, `predeterminado: bool`, `creado`, `actualizado`
  - `PerfilImpresion.info_papel() -> InfoPapel`; `PerfilImpresion.area_cm2() -> Decimal` (hoja completa); `PerfilImpresion.requiere_revision() -> bool` (versión del driver distinta a la actual)
  - `servicios.aplicar_devmode(perfil, devmode: bytes) -> None`: guarda devmode, versión y todos los campos derivados (de `leer_campos` + `info_papel` + `reconocer`)
  - `servicios.configurar_en_driver(perfil) -> bool` (False si canceló)
  - `servicios.duplicar(perfil, nombre: str) -> PerfilImpresion`
  - `servicios.marcar_predeterminado(perfil) -> None` (desmarca los demás)
  - URLs (`perfiles:`): `lista`, `nuevo`, `editar <pk>`, `preferencias <pk>` (POST), `duplicar <pk>` (POST), `eliminar <pk>` (POST), `predeterminado <pk>` (POST)

Flujo: "Nuevo" crea el perfil con `devmode_predeterminado` de la impresora elegida y lleva a "Editar"; en "Editar", el botón **"Abrir preferencias de Epson"** hace POST a `preferencias` (la petición espera a que se cierre la ventana); tras guardar se muestran tamaño, color, calidad leídos. Si `tamano == "Personalizado"` se muestra aviso: "Agrega este tamaño en Tarifas para poder cobrarlo". Lista con insignia "Revisar" si `requiere_revision()`.

- [ ] **Step 1: Pruebas que fallan** (backend falso)

```python
def test_nuevo_perfil_toma_devmode_predeterminado(client, db, controlador_falso):
    r = client.post(reverse("perfiles:nuevo"), {"nombre": "Foto glossy", "impresora": "EPSON L355 Series", "tipo_papel": glossy.pk, "factor_calidad": "1.3"})
    p = PerfilImpresion.objects.get(nombre="Foto glossy")
    assert bytes(p.devmode) == controlador_falso.devmode_predeterminado("EPSON L355 Series") and r.status_code == 302
def test_preferencias_guarda_cambios(client, perfil, controlador_falso):
    client.post(reverse("perfiles:preferencias", args=[perfil.pk])); perfil.refresh_from_db()
    assert perfil.calidad == 600
def test_preferencias_cancelado_no_cambia(client, perfil, controlador_falso):
    controlador_falso.cancelar = True; antes = bytes(perfil.devmode)
    client.post(reverse("perfiles:preferencias", args=[perfil.pk])); perfil.refresh_from_db()
    assert bytes(perfil.devmode) == antes
def test_un_solo_predeterminado(perfil, otro_perfil):
    marcar_predeterminado(perfil); marcar_predeterminado(otro_perfil); perfil.refresh_from_db()
    assert not perfil.predeterminado and PerfilImpresion.objects.filter(predeterminado=True).count() == 1
def test_duplicar_copia_devmode(perfil):
    assert bytes(duplicar(perfil, "Copia").devmode) == bytes(perfil.devmode)
def test_requiere_revision(perfil, controlador_falso):
    perfil.version_driver = "viejo"; assert perfil.requiere_revision()
```

- [ ] **Step 2:** Run → FAIL. **Step 3:** Implementar. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: perfiles de impresión con preferencias nativas`.

---

### Task 8: Rangos de páginas y estimación

**Files:**
- Create: `trabajos/rangos.py`, `trabajos/models.py`, `trabajos/servicios.py` (parte de estimación)
- Test: `tests/trabajos/test_rangos.py`, `tests/trabajos/test_estimacion.py`

**Interfaces:**
- Consumes: `Documento`, `rasterizar`, `medir_cobertura`, `cargar_tarifas`, `precio_pagina`, `PerfilImpresion`.
- Produces:
  - `parsear_rango(texto: str, total: int) -> list[int]` — vacío = todas; acepta `"1,3,5-7"` con espacios; lanza `ValueError` con mensaje en español
  - `Trabajo`: `archivo: FileField(upload_to="trabajos/%Y/%m/")`, `nombre_original`, `perfil: FK PerfilImpresion SET_NULL null`, `perfil_nombre` (copia), `escala`, `paginas: JSONField (list[int])`, `copias: int`, `coberturas: JSONField (list[dict c,m,y,k])`, `precio_unitario_por_pagina: JSONField (list[str])`, `total: Decimal`, `estado: choices "estimado","impreso","error"`, `mensaje_error`, `creado`
  - `@dataclass DetallePagina: numero: int, cobertura: Cobertura, precio: PrecioPagina, miniatura: Image.Image`
  - `@dataclass Estimacion: detalles: list[DetallePagina], copias: int, total: Decimal`
  - `estimar(doc: Documento, perfil: PerfilImpresion, paginas: list[int], copias: int, escala: Escala) -> Estimacion` — rasteriza a `DPI_MEDICION`, mide con `monocromo = not perfil.color`, `total = Σ precio × copias`; miniatura = la misma imagen reducida a 300 px de alto.

- [ ] **Step 1: Pruebas que fallan**

```python
@pytest.mark.parametrize("t,esp", [("", [1,2,3,4]), ("2", [2]), ("1, 3-4", [1,3,4]), ("4,1", [1,4]), ("2-2", [2])])
def test_rango_ok(t, esp): assert parsear_rango(t, 4) == esp
@pytest.mark.parametrize("t", ["0", "5", "3-1", "a", "1-", "-2"])
def test_rango_invalido(t):
    with pytest.raises(ValueError): parsear_rango(t, 4)

def test_estimar_suma_por_copias(db, perfil_glossy_4x6, doc_foto_negra):
    e = estimar(doc_foto_negra, perfil_glossy_4x6, [1], 3, "ajustar")
    assert e.total == e.detalles[0].precio.precio * 3
def test_estimar_perfil_bn_no_usa_color(db, perfil_bn_carta, doc_foto_cian):
    c = estimar(doc_foto_cian, perfil_bn_carta, [1], 1, "ajustar").detalles[0].cobertura
    assert c.c == c.m == c.y == 0 and c.k > 0
```

- [ ] **Step 2:** Run → FAIL. **Step 3:** Implementar. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: rangos de páginas y estimación de precio`.

---

### Task 9: Pantalla Imprimir

**Files:**
- Modify: `trabajos/servicios.py` (añadir `imprimir_trabajo`)
- Create: `trabajos/views.py`, `trabajos/urls.py`, `trabajos/forms.py`, `trabajos/templates/trabajos/{imprimir,_estimacion}.html`
- Test: `tests/trabajos/test_views_imprimir.py`

**Interfaces:**
- Consumes: Tasks 5–8, `obtener_controlador`.
- Produces:
  - `imprimir_trabajo(trabajo: Trabajo) -> Trabajo` — normaliza, rasteriza a `DPI_IMPRESION` cada página × copias, llama `controlador.imprimir(perfil.impresora, perfil.devmode, paginas, nombre_original)`; éxito → `estado="impreso"`; `ErrorImpresora` → `estado="error"`, `mensaje_error`
  - URLs (`trabajos:`): `imprimir` (GET pantalla; POST subida crea `Trabajo` `estimado` y redirige a `?trabajo=<pk>`), `estimacion <pk>` (POST htmx: perfil, copias, páginas, escala → recalcula, guarda y devuelve `_estimacion.html`), `confirmar <pk>` (POST → `imprimir_trabajo`), página principal `/` = `trabajos:imprimir`

Pantalla: zona de arrastrar/soltar; al cargar: miniaturas, selector de perfil (preseleccionado el predeterminado), copias (1–99), páginas (texto), escala (Ajustar / Tamaño real / Llenar); el desglose (papel, tinta, precio por página, total en RD$) se refresca con `hx-trigger="change"`; botón **Imprimir — RD$ <total>**. Errores (`ArchivoNoValido`, `ValueError` de rango, `KeyError` de tarifa) se muestran en el formulario.

- [ ] **Step 1: Pruebas que fallan**

```python
def test_subir_pdf_y_estimar(client, db, perfil_glossy_4x6):
    r = client.post(reverse("trabajos:imprimir"), {"archivo": SimpleUploadedFile("a.pdf", (FIX / "una.pdf").read_bytes())})
    t = Trabajo.objects.get(); r = client.post(reverse("trabajos:estimacion", args=[t.pk]), {"perfil": perfil_glossy_4x6.pk, "copias": 2, "paginas": "", "escala": "ajustar"})
    assert "RD$" in r.content.decode() and Trabajo.objects.get().total > 0
def test_archivo_roto_muestra_error(client, db):
    r = client.post(reverse("trabajos:imprimir"), {"archivo": SimpleUploadedFile("r.pdf", b"basura")})
    assert r.status_code == 200 and "dañado" in r.content.decode()
def test_rango_invalido_muestra_error(client, trabajo_cuatro_paginas, perfil_glossy_4x6):
    r = client.post(reverse("trabajos:estimacion", args=[trabajo_cuatro_paginas.pk]), {"perfil": perfil_glossy_4x6.pk, "copias": 1, "paginas": "9", "escala": "ajustar"})
    assert r.status_code == 200 and "página" in r.content.decode().lower()
def test_imprimir_envia_paginas_por_copias(client, trabajo_estimado_2_copias, controlador_falso):
    client.post(reverse("trabajos:confirmar", args=[trabajo_estimado_2_copias.pk]))
    assert len(controlador_falso.impresos[0][2]) == 2 and Trabajo.objects.get().estado == "impreso"
def test_impresora_falla_queda_error(client, trabajo_estimado_2_copias, controlador_falso):
    controlador_falso.fallar = True; client.post(reverse("trabajos:confirmar", args=[trabajo_estimado_2_copias.pk]))
    t = Trabajo.objects.get(); assert t.estado == "error" and "desconectada" in t.mensaje_error
```

- [ ] **Step 2:** Run → FAIL. **Step 3:** Implementar. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: pantalla de impresión con precio en vivo`.

---

### Task 10: Historial y calibración

**Files:**
- Create: `trabajos/templates/trabajos/historial.html`, `tarifas/calibracion.py`, `tarifas/views.py`, `tarifas/urls.py`, `tarifas/templates/tarifas/calibracion.html`; modelo `RecargaTinta` en `tarifas/models.py` + migración
- Modify: `trabajos/views.py`, `trabajos/urls.py` (vista `historial`)
- Test: `tests/trabajos/test_historial.py`, `tests/tarifas/test_calibracion.py`

**Interfaces:**
- Produces:
  - `trabajos:historial` — últimos 200 trabajos: fecha, archivo, perfil, páginas × copias, total, estado (errores en rojo con mensaje)
  - `RecargaTinta(canal, fecha: DateTimeField, precio_botella: Decimal)`
  - `cm2_impresos_desde(canal: str, desde: datetime) -> Decimal` = Σ sobre trabajos `impreso` creados después de `desde` de `cobertura_canal × area_cm2 × factor_calidad × copias` (usa área y factor guardados en el trabajo: añadir `area_cm2` y `factor_calidad` a `Trabajo` en esta task)
  - `sugerir_costo_cm2(canal: str) -> Decimal | None` = `precio_botella_de_la_recarga_anterior / cm2_impresos_entre(anterior, ultima)`; `None` si hay menos de 2 recargas o 0 cm²
  - `tarifas:calibracion` — por canal: registrar recarga, ver costo actual vs sugerido, botón "Aplicar"

- [ ] **Step 1: Pruebas que fallan**

```python
def test_sugerencia(db, trabajos_impresos_k_1000cm2):  # recargas K el día 1 (RD$600) y el día 10; entre ambas 1000 cm² equivalentes
    assert sugerir_costo_cm2("K") == Decimal("0.6")
def test_sin_recargas(db): assert sugerir_costo_cm2("C") is None
def test_historial_muestra_errores(client, trabajo_con_error):
    assert "desconectada" in client.get(reverse("trabajos:historial")).content.decode()
```

- [ ] **Step 2:** Run → FAIL. **Step 3:** Implementar. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: historial y calibración de tinta`.

---

### Task 11: Instalación en la PC con Windows

**Files:**
- Create: `scripts/iniciar.bat`, `docs/instalacion.md`, `config/servir.py`

**Interfaces:**
- Produces: `python -m config.servir` → `migrate --noinput`, `collectstatic --noinput`, `waitress.serve(application, host="127.0.0.1", port=8000)`.

- [ ] **Step 1:** `iniciar.bat`: activa `.venv` y corre `python -m config.servir`; con `start "" http://127.0.0.1:8000` tras 3 s.
- [ ] **Step 2:** `docs/instalacion.md` (español, paso a paso): instalar Python 3.12, `py -m venv .venv`, `pip install -r requirements-windows.txt`, `python manage.py createsuperuser`, crear tarea en el **Programador de tareas**: "Al iniciar sesión", usuario actual, "Ejecutar solo cuando el usuario haya iniciado sesión" (no como servicio, para que se vea la ventana de Epson), acción `iniciar.bat`; acceso directo al navegador; LibreOffice si no hay Office; cómo llenar las tarifas en el admin.
- [ ] **Step 3: Verificación:** en Linux, `IMPRESORA_BACKEND=falso python -m config.servir` y `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/` → `200`. `pytest` completo → todo PASS.
- [ ] **Step 4: Verificación manual de Luis en su PC:** reiniciar Windows → el sistema abre solo; crear perfil "Foto glossy 4x6", imprimir una foto de celular, comprobar que sale derecha, en glossy y que el precio aparece en el historial.
- [ ] **Step 5:** Commit `chore: arranque e instrucciones de instalación`.
