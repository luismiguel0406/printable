from decimal import Decimal

from .models import CANALES, CostoHoja, CostoTinta


def crear_tarifas_para(imp) -> None:
    """Tarifas en cero para una impresora nueva, copiando los papeles de la predeterminada."""
    from impresora.models import Impresora

    for canal, _ in CANALES:
        CostoTinta.objects.get_or_create(
            impresora=imp, canal=canal,
            defaults={"costo_cm2": Decimal(0), "precio_botella": Decimal(0), "rendimiento_paginas": 0},
        )
    base = Impresora.objects.filter(predeterminada=True).exclude(pk=imp.pk).first()
    hojas = CostoHoja.objects.filter(impresora=base) if base else []
    for h in hojas:
        CostoHoja.objects.get_or_create(
            impresora=imp, tipo_papel=h.tipo_papel, tamano=h.tamano,
            defaults={"costo": Decimal(0), "precio_minimo": Decimal(0)},
        )
