from tarifas.models import Configuracion


def tema(request):
    try:
        conf = Configuracion.obtener()
        actual, modo = conf.tema, conf.modo
    except Exception:  # base sin migrar
        actual, modo = "cian", "oscuro"
    return {"tema": actual, "modo": modo, "temas": Configuracion._meta.get_field("tema").choices}
