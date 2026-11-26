"""Convierte cada página del documento en la imagen exacta que se imprimirá."""

from typing import Iterator, Literal

import pymupdf
from PIL import Image, ImageOps

from impresora.base import InfoPapel

from .cobertura import _a_rgb
from .conversion import Documento

Escala = Literal["ajustar", "real", "llenar"]
DPI_FOTO_POR_DEFECTO = 300
DPI_FOTO_MINIMO = 150  # los celulares graban 72 ppp sin significado real
MM_POR_PULGADA = 25.4


def _lienzo(papel: InfoPapel, dpi: int) -> tuple[int, int]:
    return (
        max(1, round(papel.imprimible_ancho_mm / MM_POR_PULGADA * dpi)),
        max(1, round(papel.imprimible_alto_mm / MM_POR_PULGADA * dpi)),
    )


def _factor(ancho_px: float, alto_px: float, w: int, h: int, escala: Escala) -> float:
    if escala == "real":
        return 1.0
    fx, fy = w / ancho_px, h / alto_px
    return min(fx, fy) if escala == "ajustar" else max(fx, fy)


def _debe_rotar(ancho: float, alto: float, w: int, h: int, escala: Escala) -> bool:
    if escala == "real" or ancho == alto or w == h:
        return False
    return (ancho > alto) != (w > h)


def _componer(contenido: Image.Image, w: int, h: int) -> Image.Image:
    lienzo = Image.new("RGB", (w, h), "white")
    lienzo.paste(contenido, ((w - contenido.width) // 2, (h - contenido.height) // 2))
    return lienzo


def _pagina_imagen(doc: Documento, w: int, h: int, escala: Escala, dpi: int) -> Image.Image:
    with Image.open(doc.ruta) as original:
        dpi_foto = float(original.info.get("dpi", (0,))[0] or 0)
        if dpi_foto < DPI_FOTO_MINIMO:
            dpi_foto = DPI_FOTO_POR_DEFECTO
        img = _a_rgb(ImageOps.exif_transpose(original))
    # tamaño natural en píxeles del lienzo
    ancho, alto = img.width / dpi_foto * dpi, img.height / dpi_foto * dpi
    if _debe_rotar(ancho, alto, w, h, escala):
        img = img.rotate(90, expand=True)
        ancho, alto = alto, ancho
    f = _factor(ancho, alto, w, h, escala)
    dw, dh = ancho * f, alto * f  # tamaño final del contenido en px del lienzo
    vis_w, vis_h = min(dw, w), min(dh, h)
    if vis_w < dw or vis_h < dh:
        # Recortar primero en píxeles de origen: nunca se crea una imagen mayor que el lienzo.
        cx, cy = img.width / 2, img.height / 2
        mw, mh = img.width * vis_w / dw / 2, img.height * vis_h / dh / 2
        img = img.crop((round(cx - mw), round(cy - mh), round(cx + mw), round(cy + mh)))
    destino = (max(1, round(vis_w)), max(1, round(vis_h)))
    if destino != img.size:
        img = img.resize(destino, Image.Resampling.LANCZOS)
    return _componer(img, w, h)


def _pagina_pdf(pdf, numero: int, w: int, h: int, escala: Escala, dpi: int) -> Image.Image:
    pagina = pdf[numero - 1]
    ancho, alto = pagina.rect.width / 72 * dpi, pagina.rect.height / 72 * dpi
    rotar = _debe_rotar(ancho, alto, w, h, escala)
    if rotar:
        ancho, alto = alto, ancho
    f = _factor(ancho, alto, w, h, escala)
    zoom = dpi * f / 72
    # Parte visible (centrada) del contenido, en coordenadas de la página sin rotar.
    fx, fy = min(1.0, w / (ancho * f)), min(1.0, h / (alto * f))
    if rotar:
        fx, fy = fy, fx
    r = pagina.rect
    mx, my = r.width * (1 - fx) / 2, r.height * (1 - fy) / 2
    recorte = pymupdf.Rect(r.x0 + mx, r.y0 + my, r.x1 - mx, r.y1 - my)
    pix = pagina.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=recorte, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    if rotar:
        img = img.rotate(90, expand=True)
    return _componer(img, w, h)


def rasterizar(
    doc: Documento, papel: InfoPapel, escala: Escala, dpi: int, paginas: list[int]
) -> Iterator[Image.Image]:
    w, h = _lienzo(papel, dpi)
    if doc.tipo == "imagen":
        for _ in paginas:
            yield _pagina_imagen(doc, w, h, escala, dpi)
        return
    with pymupdf.open(doc.ruta) as pdf:
        for numero in paginas:
            yield _pagina_pdf(pdf, numero, w, h, escala, dpi)
