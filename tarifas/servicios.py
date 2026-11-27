from decimal import Decimal

from .models import CANALES, CostoHoja, CostoTinta


def asegurar_combinaciones(impresora=None) -> None:
    """Cada impresora real tiene una fila de costo por cada tipo de papel × tamaño (en 0 si es nueva)."""
    from impresora.models import Impresora

    from .models import TamanoPapel, TipoPapel

    impresoras = [impresora] if impresora is not None else Impresora.objects.filter(virtual=False)
    tipos, tamanos = list(TipoPapel.objects.all()), list(TamanoPapel.objects.all())
    for imp in impresoras:
        existentes = set(CostoHoja.objects.filter(impresora=imp).values_list("tipo_papel_id", "tamano"))
        CostoHoja.objects.bulk_create([
            CostoHoja(impresora=imp, tipo_papel=t, tamano=z.nombre, costo=Decimal(0), precio_minimo=Decimal(0))
            for t in tipos for z in tamanos if (t.pk, z.nombre) not in existentes
        ])


def crear_tarifas_para(imp) -> None:
    """Tarifas en cero para una impresora nueva."""
    for canal, _ in CANALES:
        CostoTinta.objects.get_or_create(
            impresora=imp, canal=canal,
            defaults={"costo_cm2": Decimal(0), "precio_botella": Decimal(0), "rendimiento_paginas": 0},
        )
    asegurar_combinaciones(imp)
