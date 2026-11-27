from decimal import Decimal

from perfiles.models import PerfilImpresion
from perfiles.servicios import duplicar, marcar_predeterminado


def test_aplicar_devmode_deriva_campos(perfil_glossy_4x6):
    p = perfil_glossy_4x6
    assert p.tamano == "4x6"
    assert p.color is True
    assert p.calidad == 360
    assert p.version_driver == "EPSON L355 Series v3.0"
    assert p.area_cm2() == Decimal("154.84")
    info = p.info_papel()
    assert info.imprimible_ancho_mm == 101.6 - 6


def test_tamano_personalizado(crear_perfil):
    assert crear_perfil("Raro", ancho_mm=100, alto_mm=100).tamano == "Personalizado"


def test_un_solo_predeterminado(perfil, otro_perfil):
    marcar_predeterminado(perfil)
    marcar_predeterminado(otro_perfil)
    perfil.refresh_from_db()
    assert not perfil.predeterminado
    assert PerfilImpresion.objects.filter(predeterminado=True).count() == 1


def test_duplicar_copia_devmode(perfil):
    copia = duplicar(perfil, "Copia")
    assert bytes(copia.devmode) == bytes(perfil.devmode)
    assert copia.pk != perfil.pk and not copia.predeterminado


def test_requiere_revision(perfil, controlador_falso):
    assert not perfil.requiere_revision()
    perfil.version_driver = "viejo"
    assert perfil.requiere_revision()


def test_requiere_revision_si_impresora_no_existe(perfil):
    perfil.impresora.nombre_windows = "Otra"
    assert perfil.requiere_revision()
