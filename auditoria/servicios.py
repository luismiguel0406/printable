from datetime import datetime, timedelta

from django.db import IntegrityError, transaction

from impresora.models import Impresora

from .eventos import EventoImpresion
from .models import ImpresionFuera, Latido, PeriodoSinVigilancia

HUECO = timedelta(minutes=2)
PREFIJO_SISTEMA = "Printable#"
VIRTUALES = ["printable", "microsoft print to pdf", "microsoft xps document writer", "onenote", "fax", "clawpdf"]


def latir(ahora: datetime) -> PeriodoSinVigilancia | None:
    """Anota que el vigilante está vivo; si llevaba más de 2 min sin latir, registra el hueco."""
    latido = Latido.obtener()
    periodo = None
    if latido.ultimo is not None and ahora - latido.ultimo > HUECO:
        periodo = PeriodoSinVigilancia.objects.create(inicio=latido.ultimo, fin=ahora)
    latido.ultimo = ahora
    latido.save(update_fields=["ultimo"])
    return periodo


def _es_virtual(nombre: str) -> bool:
    n = nombre.lower()
    return any(v in n for v in VIRTUALES) or Impresora.objects.filter(nombre_windows=nombre, virtual=True).exists()


def registrar_eventos(eventos: list[EventoImpresion]) -> list[ImpresionFuera]:
    nuevas = []
    for e in eventos:
        if e.documento.startswith(PREFIJO_SISTEMA) or _es_virtual(e.impresora):
            continue
        if ImpresionFuera.objects.filter(id_registro=e.id_registro).exists():
            continue
        try:
            with transaction.atomic():
                nuevas.append(ImpresionFuera.objects.create(
                    id_registro=e.id_registro, fecha=e.fecha, impresora=e.impresora[:200],
                    documento=e.documento[:500], usuario=e.usuario[:200], paginas=e.paginas,
                ))
        except IntegrityError:
            continue
    return nuevas


def pendientes() -> int:
    return (PeriodoSinVigilancia.objects.filter(revisado=False).count()
            + ImpresionFuera.objects.filter(revisado=False).count())
