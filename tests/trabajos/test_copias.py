from datetime import datetime, timezone as tz
from decimal import Decimal

import pytest
from django.urls import reverse

from tarifas.models import PrecioCopia
from trabajos.copias import cuadre, precio_copia
from trabajos.models import LecturaContador, Trabajo, VentaCopia


def dia(n, h=12):
    return datetime(2026, 11, n, h, tzinfo=tz.utc)


@pytest.fixture
def precios(epson):
    PrecioCopia.objects.update_or_create(impresora=epson, tipo="bn", defaults={"precio": Decimal("5")})
    PrecioCopia.objects.update_or_create(impresora=epson, tipo="color", defaults={"precio": Decimal("15")})


def test_registrar_copias(client, epson, precios):
    r = client.post(reverse("trabajos:copias"), {"impresora": epson.pk, "tipo": "color", "cantidad": 3})
    assert r.status_code == 302
    v = VentaCopia.objects.get()
    assert (v.cantidad, v.precio_unitario, v.total, v.impresora) == (3, Decimal("15"), Decimal("45"), epson)


@pytest.mark.parametrize("cantidad", ["0", "-2", "x", "1000"])
def test_cantidad_invalida(client, epson, precios, cantidad):
    r = client.post(reverse("trabajos:copias"), {"impresora": epson.pk, "tipo": "bn", "cantidad": cantidad})
    assert r.status_code == 200 and VentaCopia.objects.count() == 0


def test_pantalla_muestra_ventas_de_hoy_y_total(client, epson, precios):
    for tipo, n in [("bn", 10), ("color", 2)]:
        client.post(reverse("trabajos:copias"), {"impresora": epson.pk, "tipo": tipo, "cantidad": n})
    html = client.get(reverse("trabajos:copias")).content.decode()
    assert "RD$ 80.00" in html  # 10×5 + 2×15
    assert 'aria-label="Copias B/N' in html and 'aria-label="Copias a color' in html


def test_anular_venta(client, epson, precios):
    client.post(reverse("trabajos:copias"), {"impresora": epson.pk, "tipo": "bn", "cantidad": 4})
    v = VentaCopia.objects.get()
    client.post(reverse("trabajos:anular_copia", args=[v.pk]))
    v.refresh_from_db()
    assert v.anulada
    assert "RD$ 0.00" in client.get(reverse("trabajos:copias")).content.decode()


def test_precio_sin_configurar_avisa(client, epson):
    assert precio_copia(epson, "bn") == Decimal("0")
    assert "precio de las copias está en 0" in client.get(reverse("trabajos:copias")).content.decode()


def test_cuadre_detecta_paginas_sin_registrar(epson):
    LecturaContador.objects.create(impresora=epson, fecha=dia(1, 8), total_paginas=1000)
    t = Trabajo.objects.create(nombre_original="a", impresora=epson, estado="impreso", paginas=[1, 2, 3], copias=2)
    Trabajo.objects.filter(pk=t.pk).update(enviado_en=dia(1, 10))  # 6 páginas
    Trabajo.objects.create(nombre_original="b", impresora=epson, estado="error", paginas=[1], copias=1, enviado_en=dia(1, 11))
    v = VentaCopia.objects.create(impresora=epson, tipo="bn", cantidad=10, precio_unitario=5, total=50)
    VentaCopia.objects.filter(pk=v.pk).update(fecha=dia(1, 12))
    anulada = VentaCopia.objects.create(impresora=epson, tipo="bn", cantidad=50, precio_unitario=5, total=250, anulada=True)
    VentaCopia.objects.filter(pk=anulada.pk).update(fecha=dia(1, 12))
    LecturaContador.objects.create(impresora=epson, fecha=dia(1, 20), total_paginas=1020)
    [fila] = cuadre(epson)
    assert (fila.contadas, fila.sistema, fila.copias, fila.sin_registrar) == (20, 6, 10, 4)


def test_cuadre_por_impresora(epson, hp):
    LecturaContador.objects.create(impresora=hp, fecha=dia(1, 8), total_paginas=10)
    LecturaContador.objects.create(impresora=hp, fecha=dia(1, 20), total_paginas=15)
    assert cuadre(epson) == [] and cuadre(hp)[0].sin_registrar == 5


def test_lectura_menor_que_la_anterior_se_rechaza(client, epson):
    LecturaContador.objects.create(impresora=epson, fecha=dia(1), total_paginas=1000)
    r = client.post(reverse("trabajos:lectura"), {"impresora": epson.pk, "total_paginas": 900})
    assert r.status_code == 200 and "menor que la última" in r.content.decode()
    assert LecturaContador.objects.count() == 1


def test_registrar_lectura(client, epson):
    r = client.post(reverse("trabajos:lectura"), {"impresora": epson.pk, "total_paginas": 1234})
    assert r.status_code == 302 and LecturaContador.objects.get().total_paginas == 1234


def test_menu_tiene_copias(client, db):
    assert 'href="/copias/"' in client.get("/historial/").content.decode()
