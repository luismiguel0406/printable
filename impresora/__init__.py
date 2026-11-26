"""Acceso a la impresora. Único paquete que toca APIs de Windows."""


def obtener_controlador():
    from django.conf import settings

    if settings.IMPRESORA_BACKEND == "windows":
        from .windows import instancia
    else:
        from .falso import instancia
    return instancia()
