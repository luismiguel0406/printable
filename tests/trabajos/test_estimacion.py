import pytest
from PIL import Image

from trabajos.conversion import Documento
from trabajos.servicios import estimar


@pytest.fixture
def doc_foto(tmp_path):
    def crear(color):
        ruta = tmp_path / f"{color}.png"
        Image.new("RGB", (600, 400), color).save(ruta)
        return Documento(ruta, "imagen", 1)

    return crear


def test_estimar_suma_por_copias(perfil_glossy_4x6, doc_foto):
    e = estimar(doc_foto("black"), perfil_glossy_4x6, [1], 3, "ajustar")
    assert e.copias == 3
    assert e.total == e.detalles[0].precio.precio * 3
    assert e.detalles[0].numero == 1
    assert e.detalles[0].miniatura.height == 300


def test_estimar_perfil_bn_no_usa_color(perfil_bn_carta, doc_foto):
    c = estimar(doc_foto((0, 255, 255)), perfil_bn_carta, [1], 1, "ajustar").detalles[0].cobertura
    assert c.c == c.m == c.y == 0 and c.k > 0


def test_estimar_mas_tinta_cuesta_mas(perfil_glossy_4x6, doc_foto, db):
    from tarifas.models import Configuracion

    conf = Configuracion.obtener()
    conf.redondeo = 0
    conf.save()
    blanco = estimar(doc_foto("white"), perfil_glossy_4x6, [1], 1, "ajustar").total
    negro = estimar(doc_foto("black"), perfil_glossy_4x6, [1], 1, "ajustar").total
    assert negro > blanco
