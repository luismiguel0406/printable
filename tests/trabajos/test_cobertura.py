import pytest
from PIL import Image

from trabajos.cobertura import Cobertura, medir_cobertura


def test_blanco():
    assert medir_cobertura(Image.new("RGB", (10, 10), "white"), False) == Cobertura(0, 0, 0, 0)


def test_negro():
    assert medir_cobertura(Image.new("RGB", (10, 10), "black"), False) == Cobertura(0, 0, 0, 1)


def test_cian():
    assert medir_cobertura(Image.new("RGB", (10, 10), (0, 255, 255)), False) == Cobertura(1, 0, 0, 0)


def test_mitad_negra():
    img = Image.new("RGB", (10, 10), "white")
    img.paste((0, 0, 0), (0, 0, 5, 10))
    assert medir_cobertura(img, False).k == pytest.approx(0.5)


def test_gris_medio_es_k():
    c = medir_cobertura(Image.new("RGB", (4, 4), (128, 128, 128)), False)
    assert c.c == c.m == c.y == pytest.approx(0, abs=0.001)
    assert c.k == pytest.approx(1 - 128 / 255, abs=0.01)


def test_monocromo_rojo_va_a_k():
    cob = medir_cobertura(Image.new("RGB", (4, 4), (255, 0, 0)), True)
    assert cob.c == cob.m == cob.y == 0
    assert cob.k == pytest.approx(1 - 76 / 255, abs=0.01)


def test_rgba_transparente_es_blanco():
    assert medir_cobertura(Image.new("RGBA", (4, 4), (0, 0, 0, 0)), False).k == 0


def test_modo_l_y_p():
    assert medir_cobertura(Image.new("L", (4, 4), 0), False).k == pytest.approx(1)
    assert medir_cobertura(Image.new("RGB", (4, 4), "white").convert("P"), False).k == 0
