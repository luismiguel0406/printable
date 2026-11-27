from pathlib import Path

from PIL import Image

from trabajos.color import es_color, paginas_con_color
from trabajos.conversion import Documento

FIX = Path(__file__).resolve().parent.parent / "fixtures"


def test_gris_es_bn():
    assert not es_color(Image.new("RGB", (50, 50), (128, 128, 128)))


def test_tinte_leve_es_bn():
    assert not es_color(Image.new("RGB", (50, 50), (240, 235, 228)))


def test_foto_escala_grises_es_bn():
    assert not es_color(Image.linear_gradient("L").convert("RGB"))


def test_logo_pequeno_es_color():
    img = Image.new("RGB", (100, 100), "white")
    img.paste((220, 20, 20), (0, 0, 10, 10))  # 1 %
    assert es_color(img)


def test_punto_rojo_minimo_no_cuenta():
    img = Image.new("RGB", (100, 100), "white")
    img.paste((220, 20, 20), (0, 0, 2, 2))  # 0.04 %
    assert not es_color(img)


def test_paginas_pdf():
    assert paginas_con_color(Documento(FIX / "mixto.pdf", "pdf", 2)) == [False, True]


def test_foto(tmp_path):
    ruta = tmp_path / "c.png"
    Image.new("RGB", (40, 40), (0, 120, 255)).save(ruta)
    assert paginas_con_color(Documento(ruta, "imagen", 1)) == [True]
