from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from impresora.base import ErrorImpresora
from impresora.papeles import PERSONALIZADO

from . import servicios
from .forms import EditarPerfilForm, NuevoPerfilForm
from .models import PerfilImpresion


def lista(request):
    perfiles = list(
        PerfilImpresion.objects.select_related("tipo_papel", "impresora").order_by(
            "impresora__nombre_windows", "-predeterminado", "nombre"
        )
    )
    for p in perfiles:
        p.revisar = p.requiere_revision()
    return render(request, "perfiles/lista.html", {"perfiles": perfiles})


def nuevo(request):
    form = NuevoPerfilForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            perfil = servicios.crear_perfil(
                d["nombre"], d["impresora"], d["tipo_papel"], d["factor_calidad"]
            )
            perfil.uso_sugerido = d.get("uso_sugerido", "")
            perfil.save(update_fields=["uso_sugerido"])
        except ErrorImpresora as e:
            form.add_error(None, str(e))
        else:
            messages.info(request, "Perfil creado. Ahora configúralo en las preferencias de Epson.")
            return redirect("perfiles:editar", perfil.pk)
    return render(request, "perfiles/form.html", {"form": form, "perfil": None})


def editar(request, pk):
    perfil = get_object_or_404(PerfilImpresion, pk=pk)
    form = EditarPerfilForm(request.POST or None, instance=perfil)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.info(request, "Perfil guardado.")
        return redirect("perfiles:lista")
    return render(
        request,
        "perfiles/form.html",
        {"form": form, "perfil": perfil, "personalizado": perfil.tamano == PERSONALIZADO},
    )


@require_POST
def preferencias(request, pk):
    perfil = get_object_or_404(PerfilImpresion, pk=pk)
    try:
        if servicios.configurar_en_driver(perfil):
            messages.info(request, "Preferencias de la impresora guardadas en el perfil.")
        else:
            messages.info(request, "Cancelado: el perfil no cambió.")
    except ErrorImpresora as e:
        messages.error(request, str(e))
    return redirect("perfiles:editar", perfil.pk)


@require_POST
def duplicar(request, pk):
    perfil = get_object_or_404(PerfilImpresion, pk=pk)
    copia = servicios.duplicar(perfil, servicios.nombre_libre(f"Copia de {perfil.nombre}"))
    return redirect("perfiles:editar", copia.pk)


@require_POST
def eliminar(request, pk):
    get_object_or_404(PerfilImpresion, pk=pk).delete()
    messages.info(request, "Perfil eliminado.")
    return redirect("perfiles:lista")


@require_POST
def predeterminado(request, pk):
    servicios.marcar_predeterminado(get_object_or_404(PerfilImpresion, pk=pk))
    return redirect("perfiles:lista")
