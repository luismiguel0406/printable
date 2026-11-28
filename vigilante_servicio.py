"""Vigilante de Printable que corre como SYSTEM (tarea programada «Printable\\Vigilante»).

Cancela lo que se mande directo a una impresora real y deja el latido y la auditoría de lo que
Windows imprimió por fuera. Una cuenta estándar de Windows no puede detenerlo.
Uso: pythonw.exe vigilante_servicio.py
"""

import logging
import os
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

INTERVALO = 30  # segundos entre latidos
MUTEX = "Global\\PrintableVigilante"

log = logging.getLogger("printable.vigilante")


def preparar_entorno() -> None:
    os.environ.setdefault("PRINTABLE_DATOS", str(Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Printable"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.environ.setdefault("PRINTABLE_LOG", "vigilante.log")


def instancia_unica():
    """Devuelve el mutex si este es el único vigilante; None si ya hay otro corriendo."""
    import win32api
    import win32event
    import winerror

    mutex = win32event.CreateMutex(None, False, MUTEX)
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        return None
    return mutex


def main() -> int:
    preparar_entorno()
    mutex = instancia_unica()
    if mutex is None:
        return 0
    import django

    django.setup()
    from django.conf import settings
    from django.db import close_old_connections

    from auditoria.motor import Auditor, leer_windows
    from trabajos.vigilancia import Vigilante

    log.info("Vigilante iniciado (pid %s)", os.getpid())
    Vigilante(settings.CARPETA_ENTRADA).iniciar(colas=True, carpeta=False)
    auditor = Auditor(leer_windows)
    arrancado = False
    while True:
        close_old_connections()
        try:
            if not arrancado:
                auditor.arrancar()
                arrancado = True
            else:
                auditor.ciclo()
        except Exception:
            log.exception("Error en la auditoría")
        time.sleep(INTERVALO)


if __name__ == "__main__":
    sys.exit(main())
