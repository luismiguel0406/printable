"""Clasifica cada página como B/N o color."""

import pymupdf
from PIL import Image, ImageChops, ImageOps

from .cobertura import _a_rgb
from .conversion import Documento

DPI_CLASIFICACION = 50
UMBRAL_SATURACION = 40  # max(R,G,B) - min(R,G,B)
PROPORCION_MINIMA = 0.005  # 0.5 % de los píxeles


def es_color(img: Image.Image) -> bool:
    r, g, b = _a_rgb(img).split()
    saturacion = ImageChops.subtract(
        ImageChops.lighter(ImageChops.lighter(r, g), b),
        ImageChops.darker(ImageChops.darker(r, g), b),
    )
    hist = saturacion.histogram()
    saturados = sum(hist[UMBRAL_SATURACION + 1:])
    return saturados > PROPORCION_MINIMA * img.width * img.height


def paginas_con_color(doc: Documento) -> list[bool]:
    if doc.tipo == "imagen":
        with Image.open(doc.ruta) as img:
            img = ImageOps.exif_transpose(img)
            img.thumbnail((600, 600))
            return [es_color(img)]
    resultado = []
    with pymupdf.open(doc.ruta) as pdf:
        for pagina in pdf:
            pix = pagina.get_pixmap(dpi=DPI_CLASIFICACION, alpha=False)
            resultado.append(es_color(Image.frombytes("RGB", (pix.width, pix.height), pix.samples)))
    return resultado
