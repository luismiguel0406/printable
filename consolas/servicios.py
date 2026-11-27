from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Alquiler, Consola

BLOQUE = 30
MAXIMO = 720  # 12 horas


def minutos_validos(valor) -> int | None:
    try:
        minutos = int(valor)
    except (TypeError, ValueError):
        return None
    return minutos if 0 < minutos <= MAXIMO and minutos % BLOQUE == 0 else None


def precio_por_minutos(consola: Consola, minutos: int) -> Decimal:
    horas, resto = divmod(minutos, 60)
    return consola.precio_hora * horas + (consola.precio_media_hora if resto else Decimal("0"))


def iniciar(consola: Consola, minutos: int, usuario=None) -> Alquiler | None:
    """None si la consola ya está ocupada."""
    ahora = timezone.now()
    try:
        with transaction.atomic():
            return Alquiler.objects.create(
                consola=consola, inicio=ahora, fin=ahora + timedelta(minutes=minutos), minutos=minutos,
                total=precio_por_minutos(consola, minutos),
                usuario=usuario if usuario is not None and usuario.is_authenticated else None,
            )
    except IntegrityError:
        return None


def extender(alquiler: Alquiler, minutos: int) -> None:
    """Suma tiempo y cobro. Si ya venció, el tiempo nuevo cuenta desde ahora."""
    ahora = timezone.now()
    alquiler.fin = max(alquiler.fin, ahora) + timedelta(minutes=minutos)
    alquiler.minutos += minutos
    alquiler.total = precio_por_minutos(alquiler.consola, alquiler.minutos)
    alquiler.save(update_fields=["fin", "minutos", "total"])


def terminar(alquiler: Alquiler, estado: str = "terminado") -> None:
    alquiler.estado = estado
    alquiler.terminado_en = timezone.now()
    alquiler.save(update_fields=["estado", "terminado_en"])
