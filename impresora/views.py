from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Impresora
from .servicios import marcar_predeterminada, sincronizar_impresoras


def lista(request):
    return render(request, "impresora/lista.html", {"impresoras": Impresora.objects.all()})


@require_POST
def guardar(request, pk):
    imp = get_object_or_404(Impresora, pk=pk)
    imp.alias = request.POST.get("alias", "").strip()[:80]
    if not imp.virtual:
        imp.controlada = request.POST.get("controlada") == "on"
    imp.save()
    messages.info(request, f"Impresora «{imp}» guardada.")
    return redirect("impresora:lista")


@require_POST
def predeterminada(request, pk):
    imp = get_object_or_404(Impresora, pk=pk, virtual=False)
    marcar_predeterminada(imp)
    return redirect("impresora:lista")


@require_POST
def buscar(request):
    nuevas = sincronizar_impresoras()
    messages.info(
        request,
        f"Nuevas: {', '.join(i.nombre_windows for i in nuevas)}" if nuevas else "No hay impresoras nuevas.",
    )
    return redirect("impresora:lista")
