from tarifas.models import Configuracion


def tema(request):
    try:
        actual = Configuracion.obtener().tema
    except Exception:  # base sin migrar
        actual = "cian"
    return {"tema": actual, "temas": Configuracion._meta.get_field("tema").choices}
