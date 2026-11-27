from decimal import Decimal

from django.db import migrations


def asignar(apps, schema_editor):
    Impresora = apps.get_model("impresora", "Impresora")
    CostoHoja = apps.get_model("tarifas", "CostoHoja")
    CostoTinta = apps.get_model("tarifas", "CostoTinta")
    principal = Impresora.objects.filter(predeterminada=True).first()
    if principal is None:
        principal, _ = Impresora.objects.get_or_create(
            nombre_windows="EPSON L355 Series", defaults={"predeterminada": True}
        )
    # Las tarifas, recargas y costos de v1 eran de la Epson (la predeterminada).
    for modelo in ["CostoHoja", "CostoTinta", "RecargaTinta"]:
        apps.get_model("tarifas", modelo).objects.filter(impresora__isnull=True).update(impresora=principal)
    # Otras impresoras reales de v1 (p. ej. una HP con perfiles) reciben tarifas en cero.
    for imp in Impresora.objects.filter(virtual=False).exclude(pk=principal.pk):
        for canal in "CMYK":
            CostoTinta.objects.get_or_create(
                impresora=imp, canal=canal,
                defaults={"costo_cm2": Decimal(0), "precio_botella": Decimal(0), "rendimiento_paginas": 0},
            )
        for h in CostoHoja.objects.filter(impresora=principal):
            CostoHoja.objects.get_or_create(
                impresora=imp, tipo_papel=h.tipo_papel, tamano=h.tamano,
                defaults={"costo": Decimal(0), "precio_minimo": Decimal(0)},
            )


class Migration(migrations.Migration):
    dependencies = [
        ("tarifas", "0004_alter_costotinta_options_and_more"),
        ("impresora", "0002_epson_inicial"),
        ("perfiles", "0003_asignar_impresora"),
    ]
    operations = [migrations.RunPython(asignar, migrations.RunPython.noop)]
