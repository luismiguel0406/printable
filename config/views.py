from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from tarifas.models import Configuracion


def _opciones(campo: str) -> dict:
    return dict(Configuracion._meta.get_field(campo).choices)


@require_POST
def tema(request):
    """Cambia el color (tema) y/o el modo claro u oscuro."""
    cambios = {c: request.POST[c] for c in ("tema", "modo") if request.POST.get(c)}
    if not cambios or any(v not in _opciones(c) for c, v in cambios.items()):
        return HttpResponseBadRequest("Tema o modo desconocido")
    conf = Configuracion.obtener()
    for campo, valor in cambios.items():
        setattr(conf, campo, valor)
    conf.save(update_fields=list(cambios))
    siguiente = request.POST.get("siguiente", "/")
    if not url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()}):
        siguiente = "/"
    return redirect(siguiente)
