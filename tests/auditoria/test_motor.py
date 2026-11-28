from datetime import datetime, timedelta, timezone as tz

import pytest
from django.utils import timezone

from auditoria.models import ImpresionFuera, Latido
from auditoria.motor import Auditor, comando_wevtutil

from .test_auditoria import XML

pytestmark = pytest.mark.django_db


class Reloj:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


class Lector:
    def __init__(self, xml="<Eventos></Eventos>", fallar=False):
        self.desdes, self.xml, self.fallar = [], xml, fallar

    def __call__(self, desde):
        self.desdes.append(desde)
        if self.fallar:
            raise OSError("wevtutil no disponible")
        return self.xml


def test_arrancar_tras_hueco_lee_desde_inicio_del_hueco():
    t0 = timezone.now()
    Latido.objects.create(pk=1, ultimo=t0, eventos_hasta=t0 + timedelta(seconds=30))
    lector = Lector(XML)
    Auditor(lector, Reloj(t0 + timedelta(hours=1))).arrancar()
    assert lector.desdes == [t0]
    assert ImpresionFuera.objects.count() == 1


def test_arrancar_sin_historia_lee_ultimo_dia():
    ahora = timezone.now()
    lector = Lector()
    Auditor(lector, Reloj(ahora)).arrancar()
    assert lector.desdes == [ahora - timedelta(days=1)]


def test_ciclo_lee_eventos_cada_60s():
    t = timezone.now()
    reloj, lector = Reloj(t), Lector()
    a = Auditor(lector, reloj)
    a.arrancar()
    reloj.t = t + timedelta(seconds=30); a.ciclo()
    assert len(lector.desdes) == 1
    reloj.t = t + timedelta(seconds=61); a.ciclo()
    assert len(lector.desdes) == 2
    assert Latido.obtener().ultimo == t + timedelta(seconds=61)


def test_lector_que_falla_no_rompe():
    t = timezone.now()
    reloj = Reloj(t)
    a = Auditor(Lector(fallar=True), reloj)
    a.arrancar()
    reloj.t = t + timedelta(seconds=61)
    a.ciclo()
    assert Latido.obtener().ultimo == reloj.t


def test_comando_wevtutil_formato():
    cmd = comando_wevtutil(datetime(2026, 11, 27, 18, 0, 5, tzinfo=tz(timedelta(hours=-4))))
    texto = " ".join(cmd)
    assert cmd[:3] == ["wevtutil", "qe", "Microsoft-Windows-PrintService/Operational"]
    assert "EventID=307" in texto and "2026-11-27T22:00:05.000Z" in texto and "/f:xml" in cmd


def test_auditor_pasa_el_arranque_de_windows():
    t0 = timezone.now()
    Latido.objects.create(pk=1, ultimo=t0)
    arranque = t0 + timedelta(hours=8)
    Auditor(Lector(), Reloj(arranque + timedelta(seconds=30)), arranque=lambda: arranque).arrancar()
    from auditoria.models import PeriodoSinVigilancia
    assert PeriodoSinVigilancia.objects.count() == 0
