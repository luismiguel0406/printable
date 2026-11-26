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
