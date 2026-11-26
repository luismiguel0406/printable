import base64
import io
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from perfiles.models import PerfilImpresion

from . import servicios
from .conversion import ArchivoNoValido, normalizar
from .forms import OpcionesForm, SubirForm
from .models import Trabajo
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
    trabajo = Trabajo(nombre_original=archivo.name[:255])
    trabajo.archivo.save(archivo.name, archivo, save=False)
    ruta = Path(trabajo.archivo.path)
    try:
        doc = normalizar(ruta, ruta.parent / f"{ruta.stem}_pdf")
    except ArchivoNoValido:
        trabajo.archivo.delete(save=False)
        raise
    trabajo.ruta_normalizada = str(doc.ruta)
    trabajo.tipo_documento = doc.tipo
    trabajo.total_paginas = doc.paginas
    trabajo.save()
    return trabajo


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
    if trabajo:
        predeterminado = PerfilImpresion.objects.filter(predeterminado=True).first()
        opciones = OpcionesForm(
            initial={
                "perfil": trabajo.perfil or predeterminado or PerfilImpresion.objects.first(),
                "copias": trabajo.copias,
                "escala": trabajo.escala,
            }
        )
    return render(
        request,
        "trabajos/imprimir.html",
        {
            "subir": subir,
            "trabajo": trabajo,
            "opciones": opciones,
            "hay_perfiles": PerfilImpresion.objects.exists(),
        },
    )


@require_POST
def estimacion(request, pk):
    trabajo = get_object_or_404(Trabajo, pk=pk)
    form = OpcionesForm(request.POST)
    ctx = {"trabajo": trabajo, "error": None, "est": None}
    if not form.is_valid():
        ctx["error"] = " ".join(e for errs in form.errors.values() for e in errs)
        return render(request, "trabajos/_estimacion.html", ctx)
    d = form.cleaned_data
    try:
        paginas = parsear_rango(d["paginas"], trabajo.total_paginas)
        est = servicios.estimar(
            servicios.documento_de(trabajo), d["perfil"], paginas, d["copias"], d["escala"]
        )
    except ValueError as e:
        ctx["error"] = str(e)
    except KeyError as e:
        ctx["error"] = e.args[0]
    else:
        servicios.guardar_estimacion(trabajo, est, d["perfil"], paginas, d["escala"])
        ctx["est"] = est
        ctx["miniaturas"] = [(det, _data_uri(det.miniatura)) for det in est.detalles]
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
    servicios.imprimir_trabajo(trabajo)
    if trabajo.estado == "impreso":
        messages.info(request, f"Enviado a la impresora: {trabajo.nombre_original} — RD$ {trabajo.total}")
        return redirect("trabajos:imprimir")
    messages.error(request, f"No se pudo imprimir: {trabajo.mensaje_error}")
    return redirect(url)


def historial(request):
    return render(request, "trabajos/historial.html", {"trabajos": Trabajo.objects.all()[:200]})
