from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from trabajos.models import Trabajo

FIX = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture(autouse=True)
def media_temporal(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def bn(crear_perfil):
    return crear_perfil("B/N Carta", uso="bn", color=False)


@pytest.fixture
def color(crear_perfil):
    return crear_perfil("Color Carta", uso="color")


def subir(client, nombre):
    client.post(reverse("trabajos:imprimir"), {"archivo": SimpleUploadedFile(nombre, (FIX / nombre).read_bytes())})
    return Trabajo.objects.latest("pk")


def estimar(client, t, impresora, perfil=None, manual="0", paginas=""):
    return client.post(reverse("trabajos:estimacion", args=[t.pk]), {
        "impresora": impresora.pk, "perfil": perfil.pk if perfil else "", "perfil_manual": manual,
        "copias": 1, "paginas": paginas, "escala": "ajustar"}).content.decode()


def test_subida_clasifica_paginas(client, db):
    assert subir(client, "mixto.pdf").paginas_color == [False, True]


def test_documento_bn_sugiere_perfil_bn(client, bn, color, epson):
    t = subir(client, "una.pdf")
    html = client.get(f"/?trabajo={t.pk}").content.decode()
    assert "Sugerido: B/N" in html
    html = estimar(client, t, epson)
    assert "Sugerido: B/N" in html and f'value="{bn.pk}" selected' in html
    t.refresh_from_db()
    assert t.perfil == bn and t.impresora == epson


def test_rango_cambia_sugerencia(client, bn, color, epson):
    t = subir(client, "mixto.pdf")
    assert f'value="{color.pk}" selected' in estimar(client, t, epson)
    assert f'value="{bn.pk}" selected' in estimar(client, t, epson, paginas="1")


def test_eleccion_manual_se_respeta(client, bn, color, epson):
    t = subir(client, "una.pdf")
    html = estimar(client, t, epson, perfil=color, manual="1")
    assert f'value="{color.pk}" selected' in html
    t.refresh_from_db()
    assert t.perfil == color


def test_cambiar_impresora_filtra_perfiles(client, bn, color, perfil_hp, hp):
    t = subir(client, "una.pdf")
    html = estimar(client, t, hp)
    assert perfil_hp.nombre in html and bn.nombre not in html and color.nombre not in html


def test_perfil_de_otra_impresora_rechazado(client, bn, perfil_hp, epson):
    t = subir(client, "una.pdf")
    assert "El perfil no es de esta impresora" in estimar(client, t, epson, perfil=perfil_hp, manual="1")


def test_impresora_desconectada_no_se_ofrece(client, bn, hp, perfil_hp):
    hp.activa = False
    hp.save()
    t = subir(client, "una.pdf")
    r = client.get(f"/?trabajo={t.pk}")
    assert r.status_code == 200 and "HP emergencia" not in r.content.decode()
    assert "válid" in estimar(client, t, hp)


def test_miniaturas_marcan_color(client, bn, color, epson):
    t = subir(client, "mixto.pdf")
    html = estimar(client, t, epson)
    assert html.count(">Color<") == 1 and html.count(">B/N<") == 1


def test_pantalla_impresoras(client, epson, hp, admin_user):
    client.force_login(admin_user)
    r = client.get(reverse("impresora:lista"))
    assert "HP emergencia" in r.content.decode() and "EPSON L355 Series" in r.content.decode()
    client.post(reverse("impresora:guardar", args=[hp.pk]), {"alias": "HP de emergencia", "controlada": "on"})
    client.post(reverse("impresora:predeterminada", args=[hp.pk]))
    hp.refresh_from_db()
    epson.refresh_from_db()
    assert hp.alias == "HP de emergencia" and hp.predeterminada and not epson.predeterminada


def test_buscar_impresoras(client, epson, controlador_falso):
    controlador_falso.impresoras.append("Canon G3110")
    client.post(reverse("impresora:buscar"))
    assert "Canon G3110" in client.get(reverse("impresora:lista")).content.decode()
