from django.db import migrations


def asignar(apps, schema_editor):
    Impresora = apps.get_model("impresora", "Impresora")
    epson, _ = Impresora.objects.get_or_create(
        nombre_windows="EPSON L355 Series", defaults={"predeterminada": True}
    )
    for modelo in ["CostoHoja", "CostoTinta", "RecargaTinta"]:
        apps.get_model("tarifas", modelo).objects.filter(impresora__isnull=True).update(impresora=epson)


class Migration(migrations.Migration):
    dependencies = [("tarifas", "0004_alter_costotinta_options_and_more"), ("impresora", "0002_epson_inicial")]
    operations = [migrations.RunPython(asignar, migrations.RunPython.noop)]
