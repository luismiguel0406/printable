import pytest

from impresora.base import ErrorImpresora
from impresora.models import Impresora
from impresora.servicios import es_virtual, marcar_predeterminada, sincronizar_impresoras


def test_epson_inicial(db):
    e = Impresora.objects.get(nombre_windows="EPSON L355 Series")
    assert e.predeterminada and e.controlada and not e.virtual
    assert Impresora.predeterminada_o_primera() == e


def test_crea_nuevas_y_marca_virtuales(db, controlador_falso):
    controlador_falso.impresoras = ["EPSON L355 Series", "HP DeskJet 2700", "Printable", "Microsoft Print to PDF"]
    creadas = sincronizar_impresoras()
    assert {i.nombre_windows for i in creadas} == {"HP DeskJet 2700", "Printable", "Microsoft Print to PDF"}
    p = Impresora.objects.get(nombre_windows="Printable")
    assert p.virtual and not p.controlada
    assert Impresora.objects.get(nombre_windows="HP DeskJet 2700").controlada


def test_desinstalada_queda_inactiva_y_vuelve(db, controlador_falso):
    controlador_falso.impresoras = ["EPSON L355 Series", "HP DeskJet 2700"]
    sincronizar_impresoras()
    controlador_falso.impresoras = ["EPSON L355 Series"]
    sincronizar_impresoras()
    assert not Impresora.objects.get(nombre_windows="HP DeskJet 2700").activa
    assert list(Impresora.disponibles().values_list("nombre_windows", flat=True)) == ["EPSON L355 Series"]
    controlador_falso.impresoras = ["EPSON L355 Series", "HP DeskJet 2700"]
    sincronizar_impresoras()
    assert Impresora.objects.get(nombre_windows="HP DeskJet 2700").activa


def test_error_del_controlador_no_toca_nada(db, controlador_falso, monkeypatch):
    def falla():
        raise ErrorImpresora("x")

    monkeypatch.setattr(controlador_falso, "listar_impresoras", falla)
    assert sincronizar_impresoras() == []
    assert Impresora.objects.get(nombre_windows="EPSON L355 Series").activa


def test_una_sola_predeterminada(db):
    hp = Impresora.objects.create(nombre_windows="HP DeskJet 2700")
    marcar_predeterminada(hp)
    assert list(Impresora.objects.filter(predeterminada=True)) == [hp]


@pytest.mark.parametrize("n,v", [("Printable", True), ("Microsoft Print to PDF", True), ("OneNote (Desktop)", True), ("HP DeskJet 2700", False)])
def test_es_virtual(n, v):
    assert es_virtual(n) is v


def test_str_usa_alias(db):
    assert str(Impresora(nombre_windows="HP X", alias="HP emergencia")) == "HP emergencia"
    assert str(Impresora(nombre_windows="HP X")) == "HP X"
