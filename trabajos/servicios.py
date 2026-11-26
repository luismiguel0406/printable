"""Estimación de precio e impresión de trabajos."""

from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from PIL import Image

from perfiles.models import PerfilImpresion
from tarifas.precio import PrecioPagina, cargar_tarifas, precio_pagina

from .cobertura import Cobertura, medir_cobertura
from .conversion import Documento
from .raster import Escala, rasterizar

ALTO_MINIATURA = 300


@dataclass
class DetallePagina:
    numero: int
    cobertura: Cobertura
    precio: PrecioPagina
    miniatura: Image.Image


@dataclass
class Estimacion:
    detalles: list[DetallePagina]
    copias: int
    total: Decimal


def _miniatura(img: Image.Image) -> Image.Image:
    ancho = max(1, round(img.width * ALTO_MINIATURA / img.height))
    return img.resize((ancho, ALTO_MINIATURA), Image.Resampling.LANCZOS)


def estimar(
    doc: Documento, perfil: PerfilImpresion, paginas: list[int], copias: int, escala: Escala
) -> Estimacion:
    tarifas = cargar_tarifas()
    area = perfil.area_cm2()
    detalles = []
    imagenes = rasterizar(doc, perfil.info_papel(), escala, settings.DPI_MEDICION, paginas)
    for numero, img in zip(paginas, imagenes):
        cob = medir_cobertura(img, monocromo=not perfil.color)
        precio = precio_pagina(
            cob, area, perfil.tipo_papel.nombre, perfil.tamano, perfil.factor_calidad, tarifas
        )
        detalles.append(DetallePagina(numero, cob, precio, _miniatura(img)))
    total = sum((d.precio.precio for d in detalles), Decimal(0)) * copias
    return Estimacion(detalles, copias, total)


def documento_de(trabajo) -> Documento:
    from pathlib import Path

    return Documento(Path(trabajo.ruta_normalizada), trabajo.tipo_documento, trabajo.total_paginas)


def guardar_estimacion(trabajo, est: Estimacion, perfil: PerfilImpresion, paginas, escala) -> None:
    trabajo.perfil = perfil
    trabajo.perfil_nombre = perfil.nombre
    trabajo.escala = escala
    trabajo.paginas = paginas
    trabajo.copias = est.copias
    trabajo.coberturas = [d.cobertura.como_dict() for d in est.detalles]
    trabajo.precio_unitario_por_pagina = [str(d.precio.precio) for d in est.detalles]
    trabajo.area_cm2 = perfil.area_cm2()
    trabajo.factor_calidad = perfil.factor_calidad
    trabajo.total = est.total
    trabajo.estado = "estimado"
    trabajo.mensaje_error = ""
    trabajo.save()


def imprimir_trabajo(trabajo):
    from impresora import obtener_controlador
    from impresora.base import ErrorImpresora

    perfil = trabajo.perfil
    if perfil is None:
        raise ValueError("El perfil de este trabajo ya no existe. Elige otro y vuelve a calcular.")
    doc = documento_de(trabajo)

    def paginas():
        for _ in range(trabajo.copias):
            yield from rasterizar(
                doc, perfil.info_papel(), trabajo.escala, settings.DPI_IMPRESION, trabajo.paginas
            )

    try:
        obtener_controlador().imprimir(
            perfil.impresora, bytes(perfil.devmode), paginas(), trabajo.nombre_original
        )
    except ErrorImpresora as e:
        # El intento fallido queda como registro propio en el historial; el trabajo
        # original sigue disponible para reintentar.
        from .models import Trabajo

        fallido = Trabajo.objects.get(pk=trabajo.pk)
        fallido.pk = None
        fallido.estado = "error"
        fallido.mensaje_error = str(e)
        fallido.save()
        return fallido
    trabajo.estado = "impreso"
    trabajo.mensaje_error = ""
    trabajo.save()
    return trabajo
