"""Detección de las impresoras instaladas en Windows."""

from django.conf import settings
from django.db import transaction

from . import obtener_controlador
from .base import ErrorImpresora
from .models import Impresora


def es_virtual(nombre: str) -> bool:
    n = nombre.lower()
    return any(v.lower() in n for v in settings.IMPRESORAS_VIRTUALES)


def sincronizar_impresoras() -> list[Impresora]:
    try:
        nombres = set(obtener_controlador().listar_impresoras())
    except ErrorImpresora:
        return []
    creadas = []
    for nombre in sorted(nombres):
        imp, nueva = Impresora.objects.get_or_create(
            nombre_windows=nombre,
            defaults={"virtual": es_virtual(nombre), "controlada": not es_virtual(nombre)},
        )
        if nueva:
            creadas.append(imp)
            _al_crear(imp)
    Impresora.objects.filter(nombre_windows__in=nombres, activa=False).update(activa=True)
    Impresora.objects.exclude(nombre_windows__in=nombres).update(activa=False)
    _actualizar_estado(obtener_controlador())
    return creadas


def _actualizar_estado(ctrl) -> None:
    for imp in Impresora.objects.filter(activa=True, virtual=False):
        try:
            motivo = ctrl.estado(imp.nombre_windows)
        except ErrorImpresora as e:
            motivo = str(e)
        motivo = (motivo or "")[:120]
        if imp.en_linea != (not motivo) or imp.motivo_no_disponible != motivo:
            imp.en_linea = not motivo
            imp.motivo_no_disponible = motivo
            imp.save(update_fields=["en_linea", "motivo_no_disponible"])


def _al_crear(imp: Impresora) -> None:
    """Una impresora real nueva recibe sus tarifas en cero para que Luis las llene."""
    if not imp.virtual:
        from tarifas.servicios import crear_tarifas_para

        crear_tarifas_para(imp)


@transaction.atomic
def marcar_predeterminada(imp: Impresora) -> None:
    Impresora.objects.exclude(pk=imp.pk).update(predeterminada=False)
    imp.predeterminada = True
    imp.save(update_fields=["predeterminada"])
