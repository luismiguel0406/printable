from decimal import Decimal

import pytest
from django.urls import reverse

from impresora.papeles import reconocer
from tarifas.models import CostoHoja, TamanoPapel, TipoPapel


def test_papeles_iniciales(db, epson):
    assert set(TipoPapel.objects.values_list("nombre", flat=True)) == {"Bond", "Glossy", "Glossy adhesivo"}
    assert set(TamanoPapel.objects.values_list("nombre", flat=True)) >= {"Carta", "Legal", "A4", "4x6", "5x7"}
    assert CostoHoja.objects.filter(impresora=epson).count() == TipoPapel.objects.count() * TamanoPapel.objects.count()


def test_legal_se_reconoce(db):
    assert reconocer(215.9, 355.6) == "Legal"


def test_agregar_tipo_crea_tarifas_en_todas_las_impresoras(client, epson, hp):
    client.post(reverse("tarifas:tipo_agregar"), {"nombre": "Opalina"})
    for imp in (epson, hp):
        assert CostoHoja.objects.filter(impresora=imp, tipo_papel__nombre="Opalina").count() == TamanoPapel.objects.count()


def test_tipo_repetido_avisa(client, epson):
    r = client.post(reverse("tarifas:tipo_agregar"), {"nombre": "glossy"}, follow=True)
    assert "ya existe" in r.content.decode() and TipoPapel.objects.filter(nombre__iexact="glossy").count() == 1


def test_quitar_tipo_sin_uso(client, epson):
    t = TipoPapel.objects.create(nombre="Opalina")
    client.post(reverse("tarifas:tipo_quitar", args=[t.pk]))
    assert not TipoPapel.objects.filter(nombre="Opalina").exists()
    assert not CostoHoja.objects.filter(tipo_papel__nombre="Opalina").exists()


def test_no_quita_tipo_usado_por_un_perfil(client, perfil):
    r = client.post(reverse("tarifas:tipo_quitar", args=[perfil.tipo_papel_id]), follow=True)
    assert "lo usa el perfil" in r.content.decode()
    assert TipoPapel.objects.filter(pk=perfil.tipo_papel_id).exists()


def test_agregar_tamano(client, epson):
    client.post(reverse("tarifas:tamano_agregar"), {"nombre": "Media carta", "ancho_mm": "139.7", "alto_mm": "215.9"})
    assert CostoHoja.objects.filter(impresora=epson, tamano="Media carta").count() == TipoPapel.objects.count()
    assert reconocer(139.7, 215.9) == "Media carta"


def test_tamano_invalido(client, epson):
    r = client.post(reverse("tarifas:tamano_agregar"), {"nombre": "X", "ancho_mm": "0", "alto_mm": "10"}, follow=True)
    assert not TamanoPapel.objects.filter(nombre="X").exists() and "mayor" in r.content.decode()


def test_no_quita_tamano_usado_por_un_perfil(client, perfil):
    tam = TamanoPapel.objects.get(nombre=perfil.tamano)
    r = client.post(reverse("tarifas:tamano_quitar", args=[tam.pk]), follow=True)
    assert "lo usa el perfil" in r.content.decode() and TamanoPapel.objects.filter(pk=tam.pk).exists()


def test_quitar_tamano_sin_uso(client, epson):
    tam = TamanoPapel.objects.get(nombre="5x7")
    client.post(reverse("tarifas:tamano_quitar", args=[tam.pk]))
    assert not CostoHoja.objects.filter(tamano="5x7").exists()


def test_empleado_no_cambia_papeles(cliente_empleado, epson):
    assert cliente_empleado.post(reverse("tarifas:tipo_agregar"), {"nombre": "X"}).status_code == 403
    assert cliente_empleado.post(reverse("tarifas:tamano_agregar"), {"nombre": "X", "ancho_mm": 1, "alto_mm": 1}).status_code == 403


def test_seccion_en_pantalla_tarifas(client, epson):
    html = client.get(reverse("tarifas:editar")).content.decode()
    assert "Tipos de papel" in html and "Glossy adhesivo" in html and "Legal" in html
