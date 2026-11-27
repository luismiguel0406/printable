from pathlib import Path

import pytest
from PIL import Image, ImageStat

from impresora.base import InfoPapel
from trabajos.conversion import Documento
from trabajos.raster import rasterizar

FIX = Path(__file__).resolve().parent.parent / "fixtures"
PAPEL_4x6 = InfoPapel(101.6, 152.4, 0, 0, 101.6, 152.4)
PAPEL_CARTA = InfoPapel(215.9, 279.4, 3, 3, 209.9, 273.4)


@pytest.fixture
def doc_foto(tmp_path):
    def crear(w, h, color="black", dpi=None):
        ruta = tmp_path / f"f_{w}x{h}_{color}.png"
        kw = {"dpi": (dpi, dpi)} if dpi else {}
        Image.new("RGB", (w, h), color).save(ruta, **kw)
        return Documento(ruta, "imagen", 1)

    return crear


def doc_pdf(nombre):
    return Documento(FIX / nombre, "pdf", 4 if nombre == "cuatro.pdf" else 1)


def foto_exif_6(tmp_path):
    real = Image.new("RGB", (400, 600), "white")
    real.paste((255, 0, 0), (0, 0, 400, 60))  # franja roja arriba
    almacenada = real.rotate(90, expand=True)  # 600x400 en disco
    exif = Image.Exif()
    exif[0x0112] = 6
    ruta = tmp_path / "exif6.jpg"
    almacenada.save(ruta, exif=exif, quality=95)
    return Documento(ruta, "imagen", 1)


def test_tamano_lienzo(doc_foto):
    img = next(rasterizar(doc_foto(400, 600), PAPEL_4x6, "ajustar", 100, [1]))
    assert img.size == (400, 600)
    assert img.mode == "RGB"


def test_exif_rotada_sale_derecha(tmp_path):
    img = next(rasterizar(foto_exif_6(tmp_path), PAPEL_4x6, "ajustar", 100, [1]))
    assert img.getpixel((200, 5))[0] > 200 and img.getpixel((200, 5))[1] < 60
    assert img.getpixel((200, 595))[1] > 200  # abajo blanco, no rojo


def test_horizontal_en_perfil_vertical_se_rota(doc_foto):
    img = next(rasterizar(doc_foto(600, 400), PAPEL_4x6, "ajustar", 100, [1]))
    assert img.getpixel((200, 300)) == (0, 0, 0)
    assert img.getpixel((200, 5)) == (0, 0, 0)


def test_ajustar_no_deforma(doc_foto):
    img = next(rasterizar(doc_foto(100, 100), PAPEL_4x6, "ajustar", 100, [1]))
    assert img.getpixel((200, 10)) == (255, 255, 255)
    assert img.getpixel((200, 300)) == (0, 0, 0)


def test_llenar_cubre_todo(doc_foto):
    img = next(rasterizar(doc_foto(100, 100), PAPEL_4x6, "llenar", 100, [1]))
    assert ImageStat.Stat(img.convert("L")).mean[0] == 0


def test_real_usa_dpi_de_la_foto(doc_foto):
    # 200x200 px a 200 ppp = 1 pulgada = 100 px en lienzo de 100 ppp
    img = next(rasterizar(doc_foto(200, 200, dpi=200), PAPEL_4x6, "real", 100, [1]))
    negros = sum(1 for x in range(400) if img.getpixel((x, 300)) == (0, 0, 0))
    assert negros == 100


def test_pdf_paginas_seleccionadas():
    assert len(list(rasterizar(doc_pdf("cuatro.pdf"), PAPEL_CARTA, "ajustar", 50, [2, 4]))) == 2


def test_pdf_tamano_y_contenido():
    img = next(rasterizar(doc_pdf("una.pdf"), PAPEL_CARTA, "ajustar", 50, [1]))
    assert img.size == (round(209.9 / 25.4 * 50), round(273.4 / 25.4 * 50))
    assert ImageStat.Stat(img.convert("L")).mean[0] < 250  # tiene el rectángulo negro
