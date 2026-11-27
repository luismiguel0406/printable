from decimal import Decimal

from django.db import migrations

TAMANOS = [("Carta", 215.9, 279.4), ("Legal", 215.9, 355.6), ("A4", 210, 297), ("4x6", 101.6, 152.4), ("5x7", 127, 177.8)]
TIPOS = ["Bond", "Glossy", "Glossy adhesivo"]
QUITAR = ["Mate", "Cartulina"]


def aplicar(apps, schema_editor):
    TamanoPapel = apps.get_model("tarifas", "TamanoPapel")
    TipoPapel = apps.get_model("tarifas", "TipoPapel")
    CostoHoja = apps.get_model("tarifas", "CostoHoja")
    Perfil = apps.get_model("perfiles", "PerfilImpresion")
    Impresora = apps.get_model("impresora", "Impresora")

    for nombre, w, h in TAMANOS:
        TamanoPapel.objects.get_or_create(nombre=nombre, defaults={"ancho_mm": w, "alto_mm": h})
    # Los perfiles con tamaño "Oficio" (nombre anterior) pasan a "Legal".
    Perfil.objects.filter(tamano="Oficio").update(tamano="Legal")
    CostoHoja.objects.filter(tamano="Oficio").update(tamano="Legal")

    for nombre in TIPOS:
        TipoPapel.objects.get_or_create(nombre=nombre)
    for nombre in QUITAR:  # solo si ningún perfil los usa
        tipo = TipoPapel.objects.filter(nombre=nombre).first()
        if tipo and not Perfil.objects.filter(tipo_papel=tipo).exists():
            CostoHoja.objects.filter(tipo_papel=tipo).delete()
            tipo.delete()

    tipos, tamanos = list(TipoPapel.objects.all()), list(TamanoPapel.objects.all())
    for imp in Impresora.objects.filter(virtual=False):
        existentes = set(CostoHoja.objects.filter(impresora=imp).values_list("tipo_papel_id", "tamano"))
        CostoHoja.objects.bulk_create([
            CostoHoja(impresora=imp, tipo_papel=t, tamano=z.nombre, costo=Decimal(0), precio_minimo=Decimal(0))
            for t in tipos for z in tamanos if (t.pk, z.nombre) not in existentes
        ])


class Migration(migrations.Migration):
    dependencies = [
        ("tarifas", "0010_tamanopapel"),
        ("perfiles", "0004_impresora_fk"),
        ("impresora", "0003_impresora_en_linea_impresora_motivo_no_disponible"),
    ]
    operations = [migrations.RunPython(aplicar, migrations.RunPython.noop)]
