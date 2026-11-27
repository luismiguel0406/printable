import base64
import io
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from impresora.models import Impresora
from perfiles.models import PerfilImpresion
from perfiles.sugerencia import sugerir

from . import servicios
from .conversion import ArchivoNoValido
from .forms import OpcionesForm, SubirForm
from .models import Bloqueo, Trabajo
from .rangos import parsear_rango


def _data_uri(img) -> str:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _guardar_subida(archivo) -> Trabajo:
    ext = Path(archivo.name).suffix.lower()
    if ext not in settings.EXTENSIONES_PERMITIDAS:
        raise ArchivoNoValido(f"Tipo de archivo no soportado: {ext or 'sin extensión'}")
    if archivo.size > settings.TAMANO_MAXIMO_ARCHIVO:
        raise ArchivoNoValido("El archivo es demasiado grande (máximo 50 MB)")
    temporal = Trabajo()
    temporal.archivo.save(archivo.name, archivo, save=False)
    try:
        return servicios.crear_trabajo_desde(Path(temporal.archivo.path), archivo.name, "subido")
    except ArchivoNoValido:
        temporal.archivo.delete(save=False)
        raise


def imprimir(request):
    subir = SubirForm()
    if request.method == "POST":
        subir = SubirForm(request.POST, request.FILES)
        if subir.is_valid():
            try:
                trabajo = _guardar_subida(subir.cleaned_data["archivo"])
            except ArchivoNoValido as e:
                subir.add_error("archivo", str(e))
            else:
                return redirect(f"{reverse('trabajos:imprimir')}?trabajo={trabajo.pk}")
    trabajo = None
    opciones = None
    if request.GET.get("trabajo", "").isdigit():
        trabajo = Trabajo.objects.filter(pk=request.GET["trabajo"]).first()
    sugerencia = None
    if trabajo and trabajo.estado != "impreso":
        impresora = trabajo.impresora if trabajo.impresora and trabajo.impresora.activa else None
        paginas = trabajo.paginas or list(range(1, trabajo.total_paginas + 1))
        sugerencia = sugerir(trabajo.paginas_color, paginas, impresora)
        manual = trabajo.perfil is not None and trabajo.perfil.impresora_id == getattr(
            sugerencia.impresora, "pk", None
        )
        opciones = OpcionesForm(
            impresora=sugerencia.impresora,
            initial={
                "impresora": sugerencia.impresora,
                "perfil": trabajo.perfil if manual else sugerencia.perfil,
                "perfil_manual": "1" if manual else "0",
                "copias": trabajo.copias,
                "escala": trabajo.escala,
            },
        )
    return render(
        request,
        "trabajos/imprimir.html",
        {
            "subir": subir,
            "trabajo": trabajo,
            "opciones": opciones,
            "sugerencia": sugerencia,
            "hay_perfiles": PerfilImpresion.objects.exists(),
            "hay_impresoras": Impresora.disponibles().exists(),
        },
    )


@require_POST
def estimacion(request, pk):
    trabajo = get_object_or_404(Trabajo, pk=pk)
    form = OpcionesForm(request.POST)
    ctx = {"trabajo": trabajo, "error": None, "est": None, "perfiles": None}
    if trabajo.estado == "impreso":
        ctx["error"] = "Este trabajo ya se imprimió. Sube el archivo otra vez para reimprimir."
        return render(request, "trabajos/_estimacion.html", ctx)
    if not form.is_valid():
        ctx["error"] = " ".join(e for errs in form.errors.values() for e in errs)
        return render(request, "trabajos/_estimacion.html", ctx)
    d = form.cleaned_data
    impresora, perfil = d["impresora"], d["perfil"]
    ctx["perfiles"] = PerfilImpresion.objects.filter(impresora=impresora)
    try:
        paginas = parsear_rango(d["paginas"], trabajo.total_paginas)
    except ValueError as e:
        ctx["error"] = str(e)
        return render(request, "trabajos/_estimacion.html", ctx)
    sugerencia = sugerir(trabajo.paginas_color, paginas, impresora)
    ctx["motivo"] = sugerencia.motivo
    if d["perfil_manual"] == "1" and perfil is not None:
        if perfil.impresora_id != impresora.pk:
            ctx["error"] = "El perfil no es de esta impresora. Elige uno de la lista."
            return render(request, "trabajos/_estimacion.html", ctx)
        ctx["manual"] = True
    else:
        perfil = sugerencia.perfil
    ctx["perfil"] = perfil
    if perfil is None:
        ctx["error"] = f"{impresora} no tiene perfiles. Crea uno en Perfiles."
        return render(request, "trabajos/_estimacion.html", ctx)
    try:
        est = servicios.estimar(
            servicios.documento_de(trabajo), perfil, paginas, d["copias"], d["escala"]
        )
    except ValueError as e:
        ctx["error"] = str(e)
    except KeyError as e:
        ctx["error"] = e.args[0]
    except Exception:  # archivo ilegible, sin memoria, etc.
        ctx["error"] = "No se pudo leer el archivo. Vuelve a subirlo."
    else:
        servicios.guardar_estimacion(trabajo, est, perfil, paginas, d["escala"])
        ctx["est"] = est
        colores = trabajo.paginas_color
        ctx["miniaturas"] = [
            (det, _data_uri(det.miniatura),
             colores[det.numero - 1] if det.numero <= len(colores) else None)
            for det in est.detalles
        ]
    return render(request, "trabajos/_estimacion.html", ctx)


@require_POST
def confirmar(request, pk):
    trabajo = get_object_or_404(Trabajo, pk=pk)
    url = f"{reverse('trabajos:imprimir')}?trabajo={trabajo.pk}"
    if trabajo.estado == "impreso":
        messages.info(request, "Este trabajo ya se imprimió. Sube el archivo otra vez para reimprimir.")
        return redirect(url)
    if not trabajo.paginas or trabajo.perfil_id is None:
        messages.error(request, "Primero calcula el precio con un perfil.")
        return redirect(url)
    if request.POST.get("huella") != trabajo.huella():
        messages.error(request, "Las opciones o el precio cambiaron. Revisa el precio antes de imprimir.")
        return redirect(url)
    try:
        resultado = servicios.imprimir_trabajo(trabajo)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect(url)
    if resultado.estado == "impreso":
        messages.info(request, f"Enviado a la impresora: {trabajo.nombre_original} — RD$ {trabajo.total}")
        return redirect("trabajos:imprimir")
    messages.error(request, f"No se pudo imprimir: {resultado.mensaje_error}")
    return redirect(url)


def historial(request):
    return render(
        request,
        "trabajos/historial.html",
        {"trabajos": Trabajo.objects.all()[:200], "bloqueos": Bloqueo.objects.all()[:100]},
    )


def bandeja(request):
    from django.utils import timezone

    desde = timezone.now() - timezone.timedelta(days=1)
    recibidos = Trabajo.objects.filter(origen="capturado", estado="estimado", creado__gte=desde)
    return render(
        request,
        "trabajos/_bandeja.html",
        {"recibidos": recibidos[:20], "bloqueos": Bloqueo.objects.filter(visto=False)[:10]},
    )


@require_POST
def quitar(request, pk):
    Trabajo.objects.filter(pk=pk, estado="estimado").update(estado="descartado")
    return bandeja(request)


@require_POST
def bloqueo_visto(request, pk):
    Bloqueo.objects.filter(pk=pk).update(visto=True)
    return bandeja(request)
