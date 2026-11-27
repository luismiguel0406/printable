import pytest

from perfiles.sugerencia import Sugerencia, sugerir


@pytest.fixture
def bn(crear_perfil):
    return crear_perfil("B/N", uso="bn", color=False)


@pytest.fixture
def color(crear_perfil):
    return crear_perfil("Color", uso="color")


def test_sugiere_bn(bn, color):
    s = sugerir([False, False], [1, 2])
    assert s.perfil == bn and s.motivo == "Sugerido: B/N — ninguna página tiene color"


def test_sugiere_color_por_pagina_seleccionada(bn, color):
    s = sugerir([False, True, False, False, True], [1, 2, 3, 4, 5])
    assert s.perfil == color and s.motivo == "Sugerido: Color — páginas 2 y 5"
    assert sugerir([False, True], [1]).perfil == bn


def test_una_imagen_con_color(bn, color):
    assert sugerir([True], [1]).motivo == "Sugerido: Color — la imagen tiene color"


def test_una_pagina_con_color(bn, color):
    assert sugerir([True, False], [1, 2]).motivo == "Sugerido: Color — página 1"


def test_respeta_impresora_elegida(bn, color, perfil_hp, hp):
    s = sugerir([True], [1], hp)
    assert s.impresora == hp and s.perfil == perfil_hp


def test_sin_perfil_de_ese_uso_usa_predeterminado(crear_perfil):
    from perfiles.servicios import marcar_predeterminado

    crear_perfil("A")
    marcar_predeterminado(crear_perfil("B"))
    s = sugerir([False], [1])
    assert s.perfil.nombre == "B"
    assert s.motivo.endswith("(no hay perfil «para B/N» en esta impresora)")


def test_sin_impresoras(db):
    from impresora.models import Impresora

    Impresora.objects.update(activa=False)
    assert sugerir([True], [1]) == Sugerencia(None, None, "No hay impresoras disponibles")


def test_impresora_sin_perfiles(db, hp):
    s = sugerir([True], [1], hp)
    assert s.impresora == hp and s.perfil is None and "no tiene perfiles" in s.motivo
