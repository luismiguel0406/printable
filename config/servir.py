"""Arranca el sistema en http://127.0.0.1:8000 (uso: python -m config.servir)."""

import os
import socket

PUERTO = 8000
URL = f"http://127.0.0.1:{PUERTO}/"


def servidor_activo(puerto: int = PUERTO) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", puerto), timeout=0.5):
            return True
    except OSError:
        return False


def preparar(colas: bool = True) -> None:
    """Django listo, base migrada, impresoras detectadas y vigilante en marcha.

    colas=False: las colas las vigila el proceso SYSTEM (vigilante_servicio.py).
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()
    from django.conf import settings
    from django.core.management import call_command

    call_command("migrate", interactive=False, verbosity=0)
    if not os.environ.get("PRINTABLE_DATOS"):  # instalado: los estáticos vienen recolectados
        call_command("collectstatic", interactive=False, verbosity=0)

    from impresora.servicios import sincronizar_impresoras
    from trabajos.vigilancia import Vigilante

    sincronizar_impresoras()
    Vigilante(settings.CARPETA_ENTRADA).iniciar(colas=colas)


def servir() -> None:
    from django.core.wsgi import get_wsgi_application
    from waitress import serve

    serve(get_wsgi_application(), host="127.0.0.1", port=PUERTO, threads=4)


def main() -> None:
    preparar()
    from django.conf import settings

    print(f"Vigilando la carpeta {settings.CARPETA_ENTRADA} y las colas de impresión")
    print(f"Sistema de impresión en {URL}  (Ctrl+C para detener)")
    servir()


if __name__ == "__main__":
    main()
