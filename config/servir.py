"""Arranca el sistema en http://127.0.0.1:8000 (uso: python -m config.servir)."""

import os


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()
    from django.core.management import call_command
    from django.core.wsgi import get_wsgi_application
    from waitress import serve

    call_command("migrate", interactive=False, verbosity=0)
    call_command("collectstatic", interactive=False, verbosity=0)
    print("Sistema de impresión en http://127.0.0.1:8000  (Ctrl+C para detener)")
    serve(get_wsgi_application(), host="127.0.0.1", port=8000, threads=4)


if __name__ == "__main__":
    main()
