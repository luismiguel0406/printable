from django.db import migrations

VIRTUALES = ["printable", "microsoft print to pdf", "microsoft xps document writer", "onenote", "fax"]


def asignar(apps, schema_editor):
    Impresora = apps.get_model("impresora", "Impresora")
    for p in apps.get_model("perfiles", "PerfilImpresion").objects.all():
        virtual = any(v in p.impresora.lower() for v in VIRTUALES)
        p.impresora_ref, _ = Impresora.objects.get_or_create(
            nombre_windows=p.impresora, defaults={"virtual": virtual, "controlada": not virtual}
        )
        p.save(update_fields=["impresora_ref"])


class Migration(migrations.Migration):
    dependencies = [("perfiles", "0002_perfilimpresion_impresora_ref_and_more"), ("impresora", "0002_epson_inicial")]
    operations = [migrations.RunPython(asignar, migrations.RunPython.noop)]
