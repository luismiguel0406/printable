from django.db import migrations


def asignar(apps, schema_editor):
    """Los trabajos de v1 eran de la Epson: así la calibración los sigue contando."""
    Impresora = apps.get_model("impresora", "Impresora")
    Trabajo = apps.get_model("trabajos", "Trabajo")
    principal = Impresora.objects.filter(predeterminada=True).first()
    for t in Trabajo.objects.filter(impresora__isnull=True).select_related("perfil"):
        t.impresora_id = t.perfil.impresora_id if t.perfil_id else getattr(principal, "pk", None)
        t.save(update_fields=["impresora"])


class Migration(migrations.Migration):
    dependencies = [
        ("trabajos", "0005_trabajo_enviado_en_alter_trabajo_estado"),
        ("perfiles", "0004_impresora_fk"),
        ("impresora", "0002_epson_inicial"),
    ]
    operations = [migrations.RunPython(asignar, migrations.RunPython.noop)]
