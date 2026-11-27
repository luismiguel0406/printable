"""Lo cobrado hoy, por origen. Las consolas se sumarán aquí cuando existan."""

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone


@dataclass
class Resumen:
    impresiones: Decimal
    copias: Decimal
    papeleria: Decimal

    @property
    def total(self) -> Decimal:
        return self.impresiones + self.copias + self.papeleria


def inicio_de_hoy():
    return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)


def resumen_del_dia() -> Resumen:
    from papeleria.models import Venta

    from .models import Trabajo, VentaCopia

    hoy = inicio_de_hoy()
    suma = lambda qs, campo="total": qs.aggregate(t=Sum(campo))["t"] or Decimal("0")  # noqa: E731
    return Resumen(
        impresiones=suma(Trabajo.objects.filter(estado="impreso", enviado_en__gte=hoy)),
        copias=suma(VentaCopia.objects.filter(anulada=False, fecha__gte=hoy)),
        papeleria=suma(Venta.objects.filter(anulada=False, fecha__gte=hoy)),
    )
