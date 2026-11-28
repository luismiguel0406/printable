"""Auditor: latido del vigilante y lectura periódica del registro de impresión de Windows."""

import logging
import subprocess
from datetime import datetime, timedelta, timezone as tz
from typing import Callable

from django.utils import timezone

from . import servicios
from .eventos import parsear
from .models import Latido

log = logging.getLogger(__name__)

INTERVALO_EVENTOS = timedelta(seconds=60)
MARGEN = timedelta(seconds=10)  # Windows puede anotar un evento con unos segundos de retraso
REGISTRO = "Microsoft-Windows-PrintService/Operational"


def comando_wevtutil(desde: datetime) -> list[str]:
    instante = desde.astimezone(tz.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    consulta = f"*[System[(EventID=307) and TimeCreated[@SystemTime>='{instante}']]]"
    return ["wevtutil", "qe", REGISTRO, f"/q:{consulta}", "/f:xml"]


def arranque_windows() -> datetime | None:
    """Momento en que encendió la PC (GetTickCount64); None fuera de Windows."""
    try:
        import ctypes

        ms = ctypes.windll.kernel32.GetTickCount64
        ms.restype = ctypes.c_ulonglong
        return timezone.now() - timedelta(milliseconds=ms())
    except Exception:
        return None


def leer_windows(desde: datetime) -> str:
    r = subprocess.run(comando_wevtutil(desde), capture_output=True, text=True, timeout=60,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode != 0:
        raise OSError(r.stderr.strip() or f"wevtutil terminó con código {r.returncode}")
    return f"<Eventos>{r.stdout}</Eventos>"


class Auditor:
    def __init__(self, lector: Callable[[datetime], str], reloj: Callable[[], datetime] = timezone.now,
                 arranque: Callable[[], datetime | None] = arranque_windows):
        self.lector, self.reloj, self.arranque = lector, reloj, arranque
        self._ultima_lectura: datetime | None = None

    def _leer(self, desde: datetime, ahora: datetime) -> None:
        self._ultima_lectura = ahora
        try:
            nuevas = servicios.registrar_eventos(parsear(self.lector(desde)))
        except Exception:
            log.exception("No se pudo leer el registro de impresión de Windows")
            return
        for f in nuevas:
            log.warning("Impresión fuera del sistema: %s en %s (%s pág.) por %s", f.documento, f.impresora, f.paginas, f.usuario)
        Latido.objects.filter(pk=1).update(eventos_hasta=ahora - MARGEN)

    def arrancar(self) -> None:
        ahora = self.reloj()
        hasta = Latido.obtener().eventos_hasta
        periodo = servicios.latir(ahora, self.arranque())
        if periodo:
            log.warning("El vigilante estuvo apagado de %s a %s", periodo.inicio, periodo.fin)
        candidatos = [d for d in (hasta, periodo.inicio if periodo else None) if d is not None]
        self._leer(min(candidatos) if candidatos else ahora - timedelta(days=1), ahora)

    def ciclo(self) -> None:
        ahora = self.reloj()
        servicios.latir(ahora, self.arranque())
        if self._ultima_lectura is None or ahora - self._ultima_lectura >= INTERVALO_EVENTOS:
            desde = Latido.obtener().eventos_hasta or ahora - timedelta(days=1)
            self._leer(desde, ahora)
