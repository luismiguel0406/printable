from collections import Counter

from django.db import migrations

NOMBRE_POR_DEFECTO = "EPSON L355 Series"


def nombre_de_la_epson(apps) -> str:
    """En una base v1 la Epson puede llamarse distinto (p. ej. "EPSON L355 Series (Copiar 1)")."""
    nombres = Counter(apps.get_model("perfiles", "PerfilImpresion").objects.values_list("impresora", flat=True))
    con_l355 = [n for n, _ in nombres.most_common() if "l355" in n.lower()]
    if con_l355:
        return con_l355[0]
    if nombres:
        return nombres.most_common(1)[0][0]
    return NOMBRE_POR_DEFECTO


def crear(apps, schema_editor):
    Impresora = apps.get_model("impresora", "Impresora")
    if not Impresora.objects.filter(predeterminada=True).exists():
        imp, _ = Impresora.objects.get_or_create(nombre_windows=nombre_de_la_epson(apps))
        imp.predeterminada = True
        imp.save()


class Migration(migrations.Migration):
    dependencies = [("impresora", "0001_initial"), ("perfiles", "0001_initial")]
    operations = [migrations.RunPython(crear, migrations.RunPython.noop)]
