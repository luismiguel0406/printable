import pytest
from PIL import Image

from impresora import obtener_controlador
from impresora.base import ErrorImpresora
from impresora.devmode import leer_campos
from impresora.falso import ControladorFalso

IMPRESORA = "EPSON L355 Series"


def test_obtener_controlador_falso_es_singleton(controlador_falso):
    assert isinstance(controlador_falso, ControladorFalso)
    assert obtener_controlador() is controlador_falso


def test_lista_impresoras(controlador_falso):
    assert controlador_falso.listar_impresoras() == [IMPRESORA]


def test_preferencias_cambia_calidad(controlador_falso):
    raw = controlador_falso.devmode_predeterminado(IMPRESORA)
    nuevo = controlador_falso.abrir_preferencias(IMPRESORA, raw)
    assert leer_campos(nuevo).calidad == 600


def test_preferencias_cancelar(controlador_falso):
    controlador_falso.cancelar = True
    raw = controlador_falso.devmode_predeterminado(IMPRESORA)
    assert controlador_falso.abrir_preferencias(IMPRESORA, raw) is None


def test_info_papel_segun_devmode(controlador_falso):
    raw = controlador_falso.devmode_predeterminado(IMPRESORA)
    info = controlador_falso.info_papel(IMPRESORA, raw)
    assert (info.ancho_mm, info.alto_mm) == pytest.approx((215.9, 279.4))
    assert info.imprimible_ancho_mm < info.ancho_mm


def test_falso_imprimir_guarda(controlador_falso):
    img = Image.new("RGB", (10, 10), "white")
    controlador_falso.imprimir(IMPRESORA, b"x" * 260, iter([img, img]), "doc")
    assert controlador_falso.impresos[0][0] == IMPRESORA
    assert len(controlador_falso.impresos[0][2]) == 2


def test_falso_imprimir_y_fallar(controlador_falso):
    controlador_falso.fallar = True
    with pytest.raises(ErrorImpresora):
        controlador_falso.imprimir(IMPRESORA, b"x" * 260, [], "doc")


def test_impresora_desconocida(controlador_falso):
    with pytest.raises(ErrorImpresora):
        controlador_falso.devmode_predeterminado("Otra")
