from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from config.permisos import solo_dueno
from impresora.models import Impresora

from . import forms as tarifas_forms

from .calibracion import sugerir_costo_cm2
from .models import CANALES, CostoTinta, RecargaTinta


def _volver(impresora):
    return redirect(f"{reverse('tarifas:calibracion')}?impresora={impresora.pk}")


def calibracion(request):
    impresoras = list(Impresora.objects.filter(virtual=False))
    impresora = None
    if request.GET.get("impresora", "").isdigit():
        impresora = Impresora.objects.filter(pk=request.GET["impresora"], virtual=False).first()
    impresora = impresora or Impresora.predeterminada_o_primera()
    filas = []
    for canal, nombre in CANALES if impresora else []:
        tinta = CostoTinta.objects.filter(impresora=impresora, canal=canal).first()
        filas.append({
            "canal": canal,
            "nombre": nombre,
            "actual": tinta.costo_cm2 if tinta else None,
            "sugerido": sugerir_costo_cm2(impresora, canal),
            "ultima": RecargaTinta.objects.filter(impresora=impresora, canal=canal).first(),
        })
    return render(
        request,
        "tarifas/calibracion.html",
        {"filas": filas, "canales": CANALES, "impresora": impresora, "impresoras": impresoras},
    )


@solo_dueno
@require_POST
def recarga(request):
    impresora = get_object_or_404(Impresora, pk=request.POST.get("impresora") or 0, virtual=False)
    canal = request.POST.get("canal")
    try:
        precio = Decimal(request.POST.get("precio_botella", ""))
    except InvalidOperation:
        precio = Decimal(-1)
    if canal not in dict(CANALES) or precio <= 0:
        messages.error(request, "Indica el color y el precio de la botella.")
    else:
        RecargaTinta.objects.create(
            impresora=impresora, canal=canal, fecha=timezone.now(), precio_botella=precio
        )
        messages.info(request, "Recarga registrada.")
    return _volver(impresora)


@solo_dueno
@require_POST
def aplicar(request, impresora, canal):
    imp = get_object_or_404(Impresora, pk=impresora)
    tinta = get_object_or_404(CostoTinta, impresora=imp, canal=canal)
    sugerido = sugerir_costo_cm2(imp, canal)
    if sugerido is None:
        messages.error(request, "Todavía no hay datos suficientes para este color.")
    else:
        tinta.costo_cm2 = sugerido
        tinta.save(update_fields=["costo_cm2"])
        messages.info(request, f"Costo de {tinta.get_canal_display()} actualizado en {imp}.")
    return _volver(imp)


@solo_dueno
def editar(request):
    impresoras = Impresora.objects.filter(virtual=False)
    elegida = request.GET.get("impresora", "")
    impresora = (impresoras.filter(pk=elegida).first() if elegida.isdigit() else None) or Impresora.predeterminada_o_primera()
    if impresora is None:
        return render(request, "tarifas/editar.html", {"impresoras": impresoras, "impresora": None})
    formularios = tarifas_forms.formularios_de(impresora, request.POST if request.method == "POST" else None)
    if request.method == "POST":
        if all(f.is_valid() for f in formularios):
            tarifas_forms.guardar(impresora, formularios)
            messages.info(request, f"Tarifas de {impresora} guardadas.")
            return redirect(f"{reverse('tarifas:editar')}?impresora={impresora.pk}")
        messages.error(request, "Revisa los valores marcados: no se guardó nada.")
    hojas, tintas, copias, general = formularios
    return render(request, "tarifas/editar.html", {
        "impresoras": impresoras, "impresora": impresora,
        "hojas": hojas, "tintas": tintas, "copias": copias, "general": general,
    })
