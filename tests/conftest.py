import pytest


@pytest.fixture
def controlador_falso(settings):
    settings.IMPRESORA_BACKEND = "falso"
    from impresora import falso

    falso.reiniciar()
    yield falso.instancia()
    falso.reiniciar()


import struct
from decimal import Decimal


def devmode_falso(ancho_mm=215.9, alto_mm=279.4, color=True, codigo=1):
    """DEVMODE del backend falso con otro tamaño de papel / color."""
    from impresora.falso import _devmode_carta

    buf = bytearray(_devmode_carta())
    struct.pack_into("<hhh", buf, 78, codigo, round(alto_mm * 10), round(ancho_mm * 10))
    struct.pack_into("<h", buf, 92, 2 if color else 1)
    return bytes(buf)


@pytest.fixture
def crear_perfil(db, controlador_falso):
    from perfiles.servicios import aplicar_devmode
    from perfiles.models import PerfilImpresion
    from tarifas.models import TipoPapel

    def crear(nombre="Perfil", papel="Bond", ancho_mm=215.9, alto_mm=279.4, color=True, factor="1.00",
              impresora=None, uso=""):
        from impresora.models import Impresora

        p = PerfilImpresion(
            nombre=nombre,
            impresora=impresora or Impresora.objects.get(nombre_windows="EPSON L355 Series"),
            uso_sugerido=uso,
            tipo_papel=TipoPapel.objects.get(nombre=papel),
            factor_calidad=Decimal(factor),
        )
        aplicar_devmode(p, devmode_falso(ancho_mm, alto_mm, color))
        return p

    return crear


@pytest.fixture
def perfil(crear_perfil):
    return crear_perfil("Documento")


@pytest.fixture
def otro_perfil(crear_perfil):
    return crear_perfil("Otro")


@pytest.fixture
def perfil_glossy_4x6(crear_perfil):
    """Hoja 4x6 sin bordes (el falso deja 3 mm de margen; aquí da igual)."""
    return crear_perfil("Foto glossy 4x6", "Glossy", 101.6, 152.4, True, "1.30")


@pytest.fixture
def perfil_bn_carta(crear_perfil):
    return crear_perfil("B/N Carta", "Bond", 215.9, 279.4, False)


@pytest.fixture
def epson(db):
    from impresora.models import Impresora

    return Impresora.objects.get(nombre_windows="EPSON L355 Series")


@pytest.fixture
def hp(db, controlador_falso):
    from impresora.models import Impresora
    from tarifas.servicios import crear_tarifas_para

    controlador_falso.impresoras.append("HP DeskJet 2700")
    imp = Impresora.objects.create(nombre_windows="HP DeskJet 2700", alias="HP emergencia")
    crear_tarifas_para(imp)
    return imp


@pytest.fixture
def perfil_hp(crear_perfil, hp):
    return crear_perfil("HP Carta", "Bond", impresora=hp)
