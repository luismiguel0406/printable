"""Clasifica cada página como B/N o color."""

import pymupdf
from PIL import Image, ImageChops, ImageMath, ImageOps

from .cobertura import _a_rgb
from .conversion import Documento

DPI_CLASIFICACION = 50
UMBRAL_SATURACION = 40  # max(R,G,B) - min(R,G,B)
UMBRAL_RELATIVO = 0.25  # (max - min) / max: el papel amarillento queda por debajo
PROPORCION_MINIMA = 0.005  # 0.5 % de los píxeles


def es_color(img: Image.Image) -> bool:
    r, g, b = _a_rgb(img).split()
    maximo = ImageChops.lighter(ImageChops.lighter(r, g), b)
    saturacion = ImageChops.subtract(maximo, ImageChops.darker(ImageChops.darker(r, g), b))
    # Píxel con color: diferencia absoluta alta Y relativa al brillo alta.
    absoluta = saturacion.point(lambda v: 255 if v > UMBRAL_SATURACION else 0)
    relativa = ImageMath.lambda_eval(
        lambda a: a["convert"](
            (a["float"](a["s"]) > a["float"](a["mx"]) * UMBRAL_RELATIVO) * 255, "L"
        ),
        s=saturacion, mx=maximo,
    )
    saturados = ImageChops.multiply(absoluta, relativa).histogram()[255]
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
