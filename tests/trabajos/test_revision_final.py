"""Pruebas de los hallazgos de la revisión final."""
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from impresora.base import InfoPapel
from trabajos import conversion, raster
from trabajos.conversion import ArchivoNoValido, Documento, normalizar
from trabajos.models import Trabajo
from trabajos.raster import rasterizar

FIX = Path(__file__).resolve().parent.parent / "fixtures"
PAPEL_4x6 = InfoPapel(101.6, 152.4, 0, 0, 101.6, 152.4)


@pytest.fixture(autouse=True)
def media_temporal(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


def subir(client, nombre, contenido):
    return client.post(reverse("trabajos:imprimir"), {"archivo": SimpleUploadedFile(nombre, contenido)})


def estimar(client, t, perfil, copias=1, paginas=""):
    return client.post(reverse("trabajos:estimacion", args=[t.pk]),
                       {"perfil": perfil.pk, "copias": copias, "paginas": paginas, "escala": "ajustar"})


def confirmar(client, t):
    t.refresh_from_db()
    return client.post(reverse("trabajos:confirmar", args=[t.pk]), {"huella": t.huella()})


@pytest.fixture
def trabajo(client, db, perfil_glossy_4x6):
    subir(client, "una.pdf", (FIX / "una.pdf").read_bytes())
    t = Trabajo.objects.get()
    estimar(client, t, perfil_glossy_4x6)
    t.refresh_from_db()
    return t


# Hallazgo 1
def test_reestimar_impreso_no_lo_revierte(client, trabajo, perfil_glossy_4x6, controlador_falso):
    confirmar(client, trabajo)
    r = estimar(client, trabajo, perfil_glossy_4x6)
    trabajo.refresh_from_db()
    assert trabajo.estado == "impreso" and "ya se imprimió" in r.content.decode()
    confirmar(client, trabajo)
    assert len(controlador_falso.impresos) == 1


def test_pantalla_de_impreso_no_muestra_opciones(client, trabajo, controlador_falso):
    confirmar(client, trabajo)
    html = client.get(f"{reverse('trabajos:imprimir')}?trabajo={trabajo.pk}").content.decode()
    assert 'id="opciones"' not in html


# Hallazgo 2
def test_error_queda_en_historial_tras_reestimar(client, trabajo, perfil_glossy_4x6, controlador_falso):
    controlador_falso.fallar = True
    confirmar(client, trabajo)
    estimar(client, trabajo, perfil_glossy_4x6)
    html = client.get(reverse("trabajos:historial")).content.decode()
    assert "desconectada" in html
    assert Trabajo.objects.filter(estado="error").count() == 1


# Hallazgos 3 y 4
def test_jpeg_truncado_se_rechaza(tmp_path):
    ruta = tmp_path / "t.jpg"
    Image.new("RGB", (400, 400), "red").save(ruta, quality=95)
    datos = ruta.read_bytes()
    ruta.write_bytes(datos[: len(datos) // 2])
    with pytest.raises(ArchivoNoValido, match="dañada"):
        normalizar(ruta, tmp_path)


def test_imagen_gigante_se_rechaza(tmp_path, monkeypatch):
    ruta = tmp_path / "g.png"
    Image.new("RGB", (300, 300), "white").save(ruta)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    with pytest.raises(ArchivoNoValido, match="demasiado grande"):
        normalizar(ruta, tmp_path)


def test_estimacion_con_archivo_ilegible_muestra_error(client, trabajo, perfil_glossy_4x6):
    Path(trabajo.ruta_normalizada).write_bytes(b"ya no es un pdf")
    r = estimar(client, trabajo, perfil_glossy_4x6)
    assert r.status_code == 200 and "No se pudo leer el archivo" in r.content.decode()


# Hallazgo 5
def test_dpi_bajo_de_celular_se_trata_como_300(tmp_path):
    ruta = tmp_path / "cel.jpg"
    Image.new("RGB", (300, 300), "black").save(ruta, dpi=(72, 72))
    img = next(rasterizar(Documento(ruta, "imagen", 1), PAPEL_4x6, "real", 100, [1]))
    negros = sum(1 for x in range(400) if img.getpixel((x, 300)) == (0, 0, 0))
    assert negros == 100  # 300 px a 300 ppp = 1 pulgada


def test_llenar_no_crea_imagenes_mayores_que_el_lienzo(tmp_path, monkeypatch):
    ruta = tmp_path / "tira.png"
    Image.new("RGB", (4000, 40), "black").save(ruta)
    tamanos = []
    original = Image.Image.resize

    def espia(self, size, *a, **k):
        tamanos.append(size)
        return original(self, size, *a, **k)

    monkeypatch.setattr(Image.Image, "resize", espia)
    img = next(rasterizar(Documento(ruta, "imagen", 1), PAPEL_4x6, "llenar", 100, [1]))
    assert img.getpixel((200, 300)) == (0, 0, 0)
    assert all(w <= 400 and h <= 600 for w, h in tamanos)


def test_pdf_llenar_usa_recorte(monkeypatch):
    img = next(rasterizar(Documento(FIX / "una.pdf", "pdf", 1), InfoPapel(300, 20, 0, 0, 300, 20), "llenar", 50, [1]))
    assert img.size == (round(300 / 25.4 * 50), round(20 / 25.4 * 50))


# Hallazgo 6
def test_word_usa_microsoft_word_en_subproceso(tmp_path, monkeypatch):
    llamadas = []

    def falso_run(cmd, **kw):
        llamadas.append(cmd)
        Path(cmd[-1]).write_bytes((FIX / "una.pdf").read_bytes())

    monkeypatch.setattr(conversion, "_word_disponible", lambda: True)
    monkeypatch.setattr(conversion.subprocess, "run", falso_run)
    salida = conversion.convertir_word_a_pdf(FIX / "doc.docx", tmp_path)
    assert salida.exists() and "trabajos.word_a_pdf" in llamadas[0]


# Hallazgo 9
def test_confirmar_con_huella_vieja_no_imprime(client, trabajo, perfil_glossy_4x6, controlador_falso):
    huella_vieja = trabajo.huella()
    estimar(client, trabajo, perfil_glossy_4x6, copias=3)
    client.post(reverse("trabajos:confirmar", args=[trabajo.pk]), {"huella": huella_vieja})
    assert controlador_falso.impresos == []
