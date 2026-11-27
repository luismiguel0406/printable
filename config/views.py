from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from tarifas.models import Configuracion


@require_POST
def tema(request):
    valor = request.POST.get("tema", "")
    if valor not in dict(Configuracion._meta.get_field("tema").choices):
        return HttpResponseBadRequest("Tema desconocido")
    conf = Configuracion.obtener()
    conf.tema = valor
    conf.save(update_fields=["tema"])
    siguiente = request.POST.get("siguiente", "/")
    if not url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()}):
        siguiente = "/"
    return redirect(siguiente)
