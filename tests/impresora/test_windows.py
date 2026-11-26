"""Pruebas del backend real. Solo corren en Windows con una impresora instalada."""

import struct
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="requiere Windows")


@pytest.fixture
def controlador():
    from impresora.windows import ControladorWindows

    c = ControladorWindows()
    if not c.listar_impresoras():
        pytest.skip("no hay impresoras instaladas")
    return c


def test_devmode_predeterminado_tiene_tamano_correcto(controlador):
    impresora = controlador.listar_impresoras()[0]
    raw = controlador.devmode_predeterminado(impresora)
    dm_size, dm_extra = struct.unpack_from("<HH", raw, 68)
    assert len(raw) == dm_size + dm_extra


def test_info_papel_es_coherente(controlador):
    impresora = controlador.listar_impresoras()[0]
    info = controlador.info_papel(impresora, controlador.devmode_predeterminado(impresora))
    assert 0 < info.imprimible_ancho_mm <= info.ancho_mm
    assert 0 < info.imprimible_alto_mm <= info.alto_mm
