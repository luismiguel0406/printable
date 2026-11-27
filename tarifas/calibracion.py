"""Ajusta el costo de tinta por cm² según lo que realmente rinde cada botella."""

from datetime import datetime
from decimal import Decimal

from .models import RecargaTinta


def cm2_impresos_entre(impresora, canal: str, desde: datetime, hasta: datetime) -> Decimal:
    from trabajos.models import Trabajo

    clave = canal.lower()
    total = Decimal(0)
    trabajos = Trabajo.objects.filter(
        impresora=impresora, estado="impreso", creado__gt=desde, creado__lte=hasta
    )
    for t in trabajos.only("coberturas", "area_cm2", "factor_calidad", "copias"):
        cobertura = sum((Decimal(str(c.get(clave, 0))) for c in t.coberturas), Decimal(0))
        total += cobertura * t.area_cm2 * t.factor_calidad * t.copias
    return total


def sugerir_costo_cm2(impresora, canal: str) -> Decimal | None:
    recargas = list(
        RecargaTinta.objects.filter(impresora=impresora, canal=canal).order_by("-fecha")[:2]
    )
    if len(recargas) < 2:
        return None
    ultima, anterior = recargas
    cm2 = cm2_impresos_entre(impresora, canal, anterior.fecha, ultima.fecha)
    if cm2 <= 0:
        return None
    return (anterior.precio_botella / cm2).quantize(Decimal("0.00000001")).normalize()
