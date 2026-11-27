from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .calibracion import sugerir_costo_cm2
from .models import CANALES, CostoTinta, RecargaTinta


def calibracion(request):
    filas = []
    for canal, nombre in CANALES:
        tinta = CostoTinta.objects.filter(canal=canal).first()
        filas.append({
            "canal": canal,
            "nombre": nombre,
            "actual": tinta.costo_cm2 if tinta else None,
            "sugerido": sugerir_costo_cm2(canal),
            "ultima": RecargaTinta.objects.filter(canal=canal).first(),
        })
    return render(request, "tarifas/calibracion.html", {"filas": filas, "canales": CANALES})


@require_POST
def recarga(request):
    canal = request.POST.get("canal")
    try:
        precio = Decimal(request.POST.get("precio_botella", ""))
    except InvalidOperation:
        precio = Decimal(-1)
    if canal not in dict(CANALES) or precio <= 0:
        messages.error(request, "Indica el color y el precio de la botella.")
    else:
        RecargaTinta.objects.create(canal=canal, fecha=timezone.now(), precio_botella=precio)
        messages.info(request, "Recarga registrada.")
    return redirect("tarifas:calibracion")


@require_POST
def aplicar(request, canal):
    tinta = get_object_or_404(CostoTinta, canal=canal)
    sugerido = sugerir_costo_cm2(canal)
    if sugerido is None:
        messages.error(request, "Todavía no hay datos suficientes para este color.")
    else:
        tinta.costo_cm2 = sugerido
        tinta.save(update_fields=["costo_cm2"])
        messages.info(request, f"Costo de {tinta.get_canal_display()} actualizado.")
    return redirect("tarifas:calibracion")
