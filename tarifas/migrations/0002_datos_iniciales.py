from decimal import Decimal

from django.db import migrations

# Valores iniciales: Luis los ajusta en el admin.
PRECIO_BOTELLA = Decimal("600.00")  # Epson 664, RD$ (estimado)
RENDIMIENTO = {"C": 6500, "M": 6500, "Y": 6500, "K": 4000}
AREA_CARTA_CM2 = Decimal("603.22")
COBERTURA_REFERENCIA = Decimal("0.05")

TIPOS = ["Bond", "Glossy", "Mate", "Cartulina"]
TAMANOS = ["Carta", "A4", "4x6", "5x7"]


def sembrar(apps, schema_editor):
    TipoPapel = apps.get_model("tarifas", "TipoPapel")
    CostoHoja = apps.get_model("tarifas", "CostoHoja")
    CostoTinta = apps.get_model("tarifas", "CostoTinta")
    Configuracion = apps.get_model("tarifas", "Configuracion")

    for nombre in TIPOS:
        tipo = TipoPapel.objects.create(nombre=nombre)
        for tamano in TAMANOS:
            CostoHoja.objects.create(
                tipo_papel=tipo, tamano=tamano, costo=Decimal("0"), precio_minimo=Decimal("0")
            )

    for canal, rendimiento in RENDIMIENTO.items():
        costo = (
            PRECIO_BOTELLA / (Decimal(rendimiento) * AREA_CARTA_CM2 * COBERTURA_REFERENCIA)
        ).quantize(Decimal("0.00000001"))
        CostoTinta.objects.create(
            canal=canal,
            costo_cm2=costo,
            precio_botella=PRECIO_BOTELLA,
            rendimiento_paginas=rendimiento,
        )

    Configuracion.objects.create(
        pk=1, margen=Decimal("0.50"), redondeo=Decimal("1.00"), moneda="RD$"
    )


def deshacer(apps, schema_editor):
    for modelo in ["CostoHoja", "CostoTinta", "TipoPapel", "Configuracion"]:
        apps.get_model("tarifas", modelo).objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("tarifas", "0001_initial")]
    operations = [migrations.RunPython(sembrar, deshacer)]
