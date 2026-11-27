from decimal import Decimal

import pytest
from django.db import IntegrityError

from tarifas.models import Configuracion, CostoHoja, CostoTinta, TipoPapel


def test_configuracion_obtener_es_singleton(db):
    a = Configuracion.obtener()
    b = Configuracion.obtener()
    assert a.pk == b.pk
    assert Configuracion.objects.count() == 1


def test_costo_hoja_unico_por_papel_y_tamano(db):
    bond = TipoPapel.objects.get(nombre="Bond")
    with pytest.raises(IntegrityError):
        CostoHoja.objects.create(tipo_papel=bond, tamano="Carta", costo=1, precio_minimo=1)


def test_datos_iniciales(db):
    nombres = set(TipoPapel.objects.values_list("nombre", flat=True))
    assert nombres >= {"Bond", "Glossy", "Mate", "Cartulina"}
    assert CostoTinta.objects.count() == 4
    k = CostoTinta.objects.get(canal="K")
    esperado = (
        k.precio_botella / (Decimal(k.rendimiento_paginas) * Decimal("603.22") * Decimal("0.05"))
    ).quantize(Decimal("0.00000001"))
    assert k.costo_cm2 == esperado


def test_configuracion_valores_iniciales(db):
    c = Configuracion.obtener()
    assert c.margen == Decimal("0.50")
    assert c.redondeo == Decimal("1.00")
    assert c.moneda == "RD$"
