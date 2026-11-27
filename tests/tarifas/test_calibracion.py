from datetime import datetime, timezone
from decimal import Decimal

import pytest
from django.urls import reverse

from tarifas.calibracion import cm2_impresos_entre, sugerir_costo_cm2
from tarifas.models import CostoTinta, RecargaTinta
from trabajos.models import Trabajo


def epson():
    from impresora.models import Impresora

    return Impresora.objects.get(nombre_windows="EPSON L355 Series")


def dia(n):
    return datetime(2026, 11, n, 12, tzinfo=timezone.utc)


def trabajo(creado, k, area="1000", factor="1.00", copias=2, estado="impreso"):
    t = Trabajo.objects.create(
        impresora=epson(), nombre_original="x.pdf", coberturas=[{"c": 0, "m": 0, "y": 0, "k": k}],
        area_cm2=Decimal(area), factor_calidad=Decimal(factor), copias=copias, estado=estado,
    )
    Trabajo.objects.filter(pk=t.pk).update(creado=creado)


@pytest.fixture
def trabajos_impresos_k_1000cm2(db):
    RecargaTinta.objects.create(impresora=epson(), canal="K", fecha=dia(1), precio_botella=Decimal("600"))
    RecargaTinta.objects.create(impresora=epson(), canal="K", fecha=dia(10), precio_botella=Decimal("650"))
    trabajo(dia(5), 0.5)  # 0.5 × 1000 × 1 × 2 = 1000 cm²
    trabajo(dia(6), 0.9, estado="error")  # no cuenta
    trabajo(dia(12), 0.9)  # después de la última recarga: no cuenta


def test_cm2_entre(trabajos_impresos_k_1000cm2):
    assert cm2_impresos_entre(epson(), "K", dia(1), dia(10)) == Decimal("1000")


def test_sugerencia(trabajos_impresos_k_1000cm2):
    assert sugerir_costo_cm2(epson(), "K") == Decimal("0.6")


def test_sin_recargas(db):
    assert sugerir_costo_cm2(epson(), "C") is None


def test_sin_consumo(db):
    RecargaTinta.objects.create(impresora=epson(), canal="M", fecha=dia(1), precio_botella=Decimal("600"))
    RecargaTinta.objects.create(impresora=epson(), canal="M", fecha=dia(2), precio_botella=Decimal("600"))
    assert sugerir_costo_cm2(epson(), "M") is None


def test_vista_registrar_y_aplicar(client, trabajos_impresos_k_1000cm2):
    r = client.get(reverse("tarifas:calibracion"))
    assert "0.6" in r.content.decode()
    client.post(reverse("tarifas:aplicar", args=[epson().pk, "K"]))
    assert CostoTinta.objects.get(impresora=epson(), canal="K").costo_cm2 == Decimal("0.6")
    client.post(reverse("tarifas:recarga"), {"impresora": epson().pk, "canal": "C", "precio_botella": "620"})
    assert RecargaTinta.objects.filter(canal="C").count() == 1
