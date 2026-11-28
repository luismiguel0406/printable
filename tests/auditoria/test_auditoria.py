from datetime import timedelta

import pytest
from django.utils import timezone

from auditoria import servicios
from auditoria.eventos import EventoImpresion, parsear
from auditoria.models import ImpresionFuera, PeriodoSinVigilancia
from impresora.models import Impresora

pytestmark = pytest.mark.django_db


def evento(id_registro=1, documento="Factura.docx", impresora="EPSON L355 Series", paginas=2):
    return EventoImpresion(id_registro, timezone.now(), documento, "Caja", impresora, paginas)


def test_primer_latido_no_crea_periodo():
    assert servicios.latir(timezone.now()) is None
    assert PeriodoSinVigilancia.objects.count() == 0


def test_hueco_mayor_a_2_min_crea_periodo():
    t0 = timezone.now()
    servicios.latir(t0)
    p = servicios.latir(t0 + timedelta(minutes=10))
    assert p is not None and p.inicio == t0 and p.fin == t0 + timedelta(minutes=10)


def test_hueco_corto_no_crea_periodo():
    t0 = timezone.now()
    servicios.latir(t0)
    assert servicios.latir(t0 + timedelta(seconds=90)) is None


def test_registrar_ignora_trabajos_del_sistema():
    assert servicios.registrar_eventos([evento(documento="Printable#5 foto.jpg")]) == []


def test_registrar_ignora_impresoras_virtuales():
    Impresora.objects.create(nombre_windows="Mi PDF", virtual=True)
    eventos = [evento(1, impresora="Printable"), evento(2, impresora="Microsoft Print to PDF"), evento(3, impresora="Mi PDF")]
    assert servicios.registrar_eventos(eventos) == []


def test_registrar_no_duplica():
    servicios.registrar_eventos([evento(7)])
    servicios.registrar_eventos([evento(7)])
    assert ImpresionFuera.objects.count() == 1
    f = ImpresionFuera.objects.get()
    assert (f.documento, f.usuario, f.impresora, f.paginas) == ("Factura.docx", "Caja", "EPSON L355 Series", 2)


def test_pendientes_cuenta_no_revisados():
    servicios.registrar_eventos([evento(1), evento(2)])
    t0 = timezone.now()
    servicios.latir(t0)
    servicios.latir(t0 + timedelta(minutes=5))
    ImpresionFuera.objects.filter(id_registro=1).update(revisado=True)
    assert servicios.pendientes() == 2


XML = """<Eventos><Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event"><System>
<Provider Name="Microsoft-Windows-PrintService"/><EventID>307</EventID>
<TimeCreated SystemTime="2026-11-27T22:15:03.1234567Z"/><EventRecordID>812</EventRecordID></System>
<UserData><DocumentPrinted xmlns="http://manifests.microsoft.com/win/2005/08/windows/printing/spooler/core/events">
<Param1>12</Param1><Param2>Factura.docx</Param2><Param3>Caja</Param3><Param4>\\\\PC</Param4>
<Param5>EPSON L355 Series</Param5><Param6>USB001</Param6><Param7>12345</Param7><Param8>3</Param8>
</DocumentPrinted></UserData></Event></Eventos>"""


def test_parsear_evento_307():
    [e] = parsear(XML)
    assert (e.id_registro, e.documento, e.usuario, e.impresora, e.paginas) == (812, "Factura.docx", "Caja", "EPSON L355 Series", 3)
    assert timezone.is_aware(e.fecha) and e.fecha.year == 2026 and e.fecha.hour == 22


def test_parsear_vacio():
    assert parsear("<Eventos></Eventos>") == []


def test_pc_apagada_no_cuenta_como_hueco():
    t0 = timezone.now()
    servicios.latir(t0)
    # La PC se apagó de noche y arrancó 8 h después; el vigilante late 40 s tras arrancar.
    arranque = t0 + timedelta(hours=8)
    assert servicios.latir(arranque + timedelta(seconds=40), arranque=arranque) is None


def test_vigilante_detenido_con_pc_encendida_si_cuenta():
    t0 = timezone.now()
    servicios.latir(t0)
    arranque = t0 - timedelta(days=1)  # la PC lleva encendida desde ayer
    p = servicios.latir(t0 + timedelta(minutes=20), arranque=arranque)
    assert p is not None and p.inicio == t0
