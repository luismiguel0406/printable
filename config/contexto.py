from tarifas.models import Configuracion


def tema(request):
    try:
        conf = Configuracion.obtener()
        actual, modo = conf.tema, conf.modo
    except Exception:  # base sin migrar
        actual, modo = "cian", "oscuro"
    return {"tema": actual, "modo": modo, "temas": Configuracion._meta.get_field("tema").choices}


def alertas(request):
    """Cantidad de alertas de auditoría sin revisar (banner rojo en todas las pantallas)."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    try:
        from auditoria.servicios import pendientes

        return {"alertas_pendientes": pendientes()}
    except Exception:  # base sin migrar
        return {}
