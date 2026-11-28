from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from config.permisos import solo_dueno

from .models import ImpresionFuera, PeriodoSinVigilancia


@require_POST
@solo_dueno
def revisar(request):
    PeriodoSinVigilancia.objects.filter(revisado=False).update(revisado=True)
    ImpresionFuera.objects.filter(revisado=False).update(revisado=True)
    return redirect("/historial/#fuera")
