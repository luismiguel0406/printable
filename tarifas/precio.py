"""Cálculo del precio de una página a partir de su cobertura de tinta."""

from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal

from trabajos.cobertura import Cobertura

_CENTAVO = Decimal("0.01")


@dataclass(frozen=True)
class Tarifas:
    costo_cm2: dict[str, Decimal]
    costo_hoja: dict[tuple[str, str], tuple[Decimal, Decimal]]  # (costo, precio_minimo)
    margen: Decimal
    redondeo: Decimal


@dataclass(frozen=True)
class PrecioPagina:
    papel: Decimal
    tinta: Decimal
    costo: Decimal
    precio: Decimal


def cargar_tarifas() -> Tarifas:
    from .models import Configuracion, CostoHoja, CostoTinta

    conf = Configuracion.obtener()
    return Tarifas(
        costo_cm2={t.canal: t.costo_cm2 for t in CostoTinta.objects.all()},
        costo_hoja={
            (h.tipo_papel.nombre, h.tamano): (h.costo, h.precio_minimo)
            for h in CostoHoja.objects.select_related("tipo_papel")
        },
        margen=conf.margen,
        redondeo=conf.redondeo,
    )


def _redondear_arriba(valor: Decimal, multiplo: Decimal) -> Decimal:
    if multiplo <= 0:
        return valor.quantize(_CENTAVO, rounding=ROUND_CEILING)
    return (valor / multiplo).to_integral_value(rounding=ROUND_CEILING) * multiplo


def precio_pagina(
    cob: Cobertura,
    area_cm2: Decimal,
    tipo_papel: str,
    tamano: str,
    factor_calidad: Decimal,
    t: Tarifas,
) -> PrecioPagina:
    try:
        papel, minimo = t.costo_hoja[(tipo_papel, tamano)]
    except KeyError:
        raise KeyError(
            f"No hay tarifa para papel {tipo_papel} en tamaño {tamano}. Agrégala en Tarifas."
        ) from None
    cobertura = {"C": cob.c, "M": cob.m, "Y": cob.y, "K": cob.k}
    tinta = sum(
        (Decimal(str(cobertura[canal])) * t.costo_cm2.get(canal, Decimal(0)) for canal in "CMYK"),
        Decimal(0),
    ) * area_cm2 * factor_calidad
    costo = papel + tinta
    precio = max(minimo, _redondear_arriba(costo * (1 + t.margen), t.redondeo))
    return PrecioPagina(papel=papel, tinta=tinta, costo=costo, precio=precio)
