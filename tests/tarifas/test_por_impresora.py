from datetime import datetime, timezone
from decimal import Decimal

import pytest
from django.db import IntegrityError
from PIL import Image

from impresora.models import Impresora
from impresora.servicios import sincronizar_impresoras
from tarifas.calibracion import sugerir_costo_cm2
from tarifas.models import CostoHoja, CostoTinta, RecargaTinta
from tarifas.precio import cargar_tarifas
from trabajos.conversion import Documento
from trabajos.servicios import estimar


def test_tarifas_separadas_por_impresora(epson, hp):
    CostoTinta.objects.filter(impresora=hp, canal="K").update(costo_cm2=Decimal("0.5"))
    assert cargar_tarifas(epson).costo_cm2["K"] != cargar_tarifas(hp).costo_cm2["K"]


def test_impresora_nueva_recibe_tarifas_en_cero(db, controlador_falso):
    controlador_falso.impresoras = ["EPSON L355 Series", "HP DeskJet 2700", "Printable"]
    sincronizar_impresoras()
    hp = Impresora.objects.get(nombre_windows="HP DeskJet 2700")
    assert CostoTinta.objects.filter(impresora=hp).count() == 4
    assert all(t.costo_cm2 == 0 for t in CostoTinta.objects.filter(impresora=hp))
    assert CostoHoja.objects.filter(impresora=hp).count() == CostoHoja.objects.filter(
        impresora__nombre_windows="EPSON L355 Series"
    ).count()
    assert not CostoTinta.objects.filter(impresora__nombre_windows="Printable").exists()


def test_crear_tarifas_es_idempotente(hp):
    from tarifas.servicios import crear_tarifas_para

    crear_tarifas_para(hp)
    assert CostoTinta.objects.filter(impresora=hp).count() == 4


def test_uso_sugerido_unico_por_impresora(crear_perfil, hp):
    crear_perfil("Color 1", uso="color")
    crear_perfil("HP color", impresora=hp, uso="color")
    crear_perfil("Sin uso 1")
    crear_perfil("Sin uso 2")
    with pytest.raises(IntegrityError):
        crear_perfil("Color 2", uso="color")


def test_calibracion_por_impresora(epson, hp):
    d = lambda n: datetime(2026, 11, n, tzinfo=timezone.utc)  # noqa: E731
    RecargaTinta.objects.create(impresora=hp, canal="K", fecha=d(1), precio_botella=Decimal("900"))
    RecargaTinta.objects.create(impresora=hp, canal="K", fecha=d(9), precio_botella=Decimal("900"))
    assert sugerir_costo_cm2(epson, "K") is None


def test_estimar_usa_tarifas_de_la_impresora_del_perfil(crear_perfil, hp, tmp_path):
    ruta = tmp_path / "n.png"
    Image.new("RGB", (300, 300), "black").save(ruta)
    doc = Documento(ruta, "imagen", 1)
    CostoHoja.objects.filter(impresora=hp, tipo_papel__nombre="Bond", tamano="Carta").update(
        costo=Decimal("40"), precio_minimo=Decimal("0")
    )
    epson_total = estimar(doc, crear_perfil("E"), [1], 1, "ajustar").total
    hp_total = estimar(doc, crear_perfil("H", impresora=hp), [1], 1, "ajustar").total
    assert hp_total > epson_total
