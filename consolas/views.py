from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from config.permisos import solo_dueno

from . import servicios
from .models import Alquiler, Consola

OPCIONES = [(30, "30 min"), (60, "1 h"), (120, "2 h")]


class ConsolaForm(forms.ModelForm):
    precio_hora = forms.DecimalField(min_value=0, max_digits=8, decimal_places=2, label="Precio por hora (RD$)")
    precio_media_hora = forms.DecimalField(min_value=0, max_digits=8, decimal_places=2, label="Precio por media hora (RD$)")

    class Meta:
        model = Consola
        fields = ["nombre", "imagen", "precio_hora", "precio_media_hora"]


def _tarjetas():
    tarjetas = []
    for c in Consola.objects.filter(activa=True):
        tarjetas.append({
            "consola": c,
            "alquiler": c.alquiler_activo(),
            "opciones": [(m, texto, servicios.precio_por_minutos(c, m)) for m, texto in OPCIONES],
        })
    return tarjetas


def lista(request):
    return render(request, "consolas/lista.html", {"tarjetas": _tarjetas()})


def tarjetas(request):
    return render(request, "consolas/_tarjetas.html", {"tarjetas": _tarjetas()})


@require_POST
def iniciar(request, pk):
    consola = get_object_or_404(Consola, pk=pk, activa=True)
    minutos = servicios.minutos_validos(request.POST.get("minutos"))
    if minutos is None:
        messages.error(request, "Elige un tiempo en bloques de 30 minutos (máximo 12 horas).")
    elif servicios.iniciar(consola, minutos, request.user) is None:
        messages.error(request, f"{consola} ya está en uso.")
    else:
        messages.info(request, f"{consola}: {minutos} min, RD$ {servicios.precio_por_minutos(consola, minutos):,.2f}")
    return redirect("consolas:lista")


@require_POST
def extender(request, pk):
    alquiler = get_object_or_404(Alquiler, pk=pk, estado="activo")
    minutos = servicios.minutos_validos(request.POST.get("minutos"))
    if minutos is None:
        messages.error(request, "Elige un tiempo en bloques de 30 minutos.")
    else:
        antes = alquiler.total
        servicios.extender(alquiler, minutos)
        messages.info(request, f"{alquiler.consola}: +{minutos} min, cobra RD$ {alquiler.total - antes:,.2f} más")
    return redirect("consolas:lista")


@require_POST
def terminar(request, pk):
    alquiler = get_object_or_404(Alquiler, pk=pk, estado="activo")
    servicios.terminar(alquiler)
    messages.info(request, f"{alquiler.consola} quedó libre.")
    return redirect("consolas:lista")


@solo_dueno
@require_POST
def cancelar(request, pk):
    alquiler = get_object_or_404(Alquiler, pk=pk)
    servicios.terminar(alquiler, "cancelado")
    messages.info(request, f"Alquiler de {alquiler.consola} cancelado: no cuenta en la caja.")
    return redirect("consolas:lista")


@solo_dueno
def administrar(request):
    form = ConsolaForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.info(request, f"Consola «{form.instance}» agregada.")
        return redirect("consolas:administrar")
    return render(request, "consolas/administrar.html", {
        "form": form, "consolas": Consola.objects.all(),
        "formularios": [(c, ConsolaForm(instance=c, prefix=f"c{c.pk}")) for c in Consola.objects.all()],
    })


@solo_dueno
@require_POST
def editar(request, pk):
    consola = get_object_or_404(Consola, pk=pk)
    prefijo = f"c{pk}" if f"c{pk}-nombre" in request.POST else None
    form = ConsolaForm(request.POST, request.FILES, instance=consola, prefix=prefijo)
    if form.is_valid():
        form.save()
        messages.info(request, f"Consola «{consola}» guardada.")
    else:
        messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
    return redirect("consolas:administrar")


@solo_dueno
@require_POST
def activa(request, pk):
    consola = get_object_or_404(Consola, pk=pk)
    consola.activa = not consola.activa
    consola.save(update_fields=["activa"])
    return redirect("consolas:administrar")
