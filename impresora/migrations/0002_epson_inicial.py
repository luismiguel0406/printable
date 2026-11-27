from django.db import migrations


def crear(apps, schema_editor):
    apps.get_model("impresora", "Impresora").objects.get_or_create(
        nombre_windows="EPSON L355 Series", defaults={"predeterminada": True}
    )


class Migration(migrations.Migration):
    dependencies = [("impresora", "0001_initial")]
    operations = [migrations.RunPython(crear, migrations.RunPython.noop)]
