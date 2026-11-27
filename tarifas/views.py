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
    from .models import TamanoPapel, TipoPapel

    return render(request, "tarifas/editar.html", {
        "impresoras": impresoras, "impresora": impresora,
        "tipos": TipoPapel.objects.all(), "tamanos": TamanoPapel.objects.all(),
        "hojas": hojas, "tintas": tintas, "copias": copias, "general": general,
    })


# --- Tipos de papel y tamaños ------------------------------------------------
def _volver_tarifas(request):
    from django.utils.http import url_has_allowed_host_and_scheme

    siguiente = request.POST.get("siguiente") or ""
    if not url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()}):
        siguiente = reverse("tarifas:editar")
    return redirect(siguiente)


@solo_dueno
@require_POST
def tipo_agregar(request):
    from .models import TipoPapel
    from .servicios import asegurar_combinaciones

    nombre = request.POST.get("nombre", "").strip()[:50]
    if not nombre:
        messages.error(request, "Escribe el nombre del tipo de papel.")
    elif TipoPapel.objects.filter(nombre__iexact=nombre).exists():
        messages.error(request, f"El tipo de papel «{nombre}» ya existe.")
    else:
        TipoPapel.objects.create(nombre=nombre)
        asegurar_combinaciones()
        messages.info(request, f"Tipo de papel «{nombre}» agregado. Pon sus costos en la tabla Papel.")
    return _volver_tarifas(request)


@solo_dueno
@require_POST
def tipo_quitar(request, pk):
    from perfiles.models import PerfilImpresion

    from .models import CostoHoja, TipoPapel

    tipo = get_object_or_404(TipoPapel, pk=pk)
    perfil = PerfilImpresion.objects.filter(tipo_papel=tipo).first()
    if perfil:
        messages.error(request, f"No se puede quitar «{tipo}»: lo usa el perfil «{perfil}».")
    else:
        CostoHoja.objects.filter(tipo_papel=tipo).delete()
        tipo.delete()
        messages.info(request, f"Tipo de papel «{tipo}» quitado.")
    return _volver_tarifas(request)


@solo_dueno
@require_POST
def tamano_agregar(request):
    from decimal import InvalidOperation

    from .models import TamanoPapel
    from .servicios import asegurar_combinaciones

    nombre = request.POST.get("nombre", "").strip()[:30]
    try:
        ancho, alto = float(request.POST.get("ancho_mm", "")), float(request.POST.get("alto_mm", ""))
    except (ValueError, InvalidOperation):
        ancho = alto = 0
    if not nombre:
        messages.error(request, "Escribe el nombre del tamaño.")
    elif ancho <= 0 or alto <= 0:
        messages.error(request, "El ancho y el alto deben ser mayores que 0 (en milímetros).")
    elif TamanoPapel.objects.filter(nombre__iexact=nombre).exists():
        messages.error(request, f"El tamaño «{nombre}» ya existe.")
    else:
        TamanoPapel.objects.create(nombre=nombre, ancho_mm=ancho, alto_mm=alto)
        asegurar_combinaciones()
        messages.info(request, f"Tamaño «{nombre}» agregado. Pon sus costos en la tabla Papel.")
    return _volver_tarifas(request)


@solo_dueno
@require_POST
def tamano_quitar(request, pk):
    from perfiles.models import PerfilImpresion

    from .models import CostoHoja, TamanoPapel

    tam = get_object_or_404(TamanoPapel, pk=pk)
    perfil = PerfilImpresion.objects.filter(tamano=tam.nombre).first()
    if perfil:
        messages.error(request, f"No se puede quitar «{tam}»: lo usa el perfil «{perfil}».")
    else:
        CostoHoja.objects.filter(tamano=tam.nombre).delete()
        tam.delete()
        messages.info(request, f"Tamaño «{tam}» quitado.")
    return _volver_tarifas(request)
