"""Comprobaciones para la prueba de instalación en GitHub Actions (no se usa en la PC)."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.contrib.auth.models import User  # noqa: E402

from trabajos.models import Trabajo  # noqa: E402


def main(orden: str) -> int:
    if orden == "usuario":
        if not User.objects.filter(username="ci").exists():
            User.objects.create_superuser("ci", "", "clave-de-prueba-ci")
        return 0
    if orden == "capturados":
        n = Trabajo.objects.filter(origen="capturado").count()
        print(f"capturados={n}")
        return 0 if n > 0 else 1
    if orden == "latido":
        from django.utils import timezone

        from auditoria.models import Latido

        ultimo = Latido.obtener().ultimo
        print(f"latido={ultimo}")
        return 0 if ultimo and timezone.now() - ultimo < timezone.timedelta(minutes=2) else 1
    print("orden desconocida", orden)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
