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
    tarifas = cargar_tarifas(perfil.impresora)
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


def crear_trabajo_desde(ruta: "Path", nombre: str, origen: str):
    """Crea un Trabajo con un archivo que ya está dentro de MEDIA_ROOT.

    Normaliza, cuenta páginas y clasifica B/N o color. Lanza ArchivoNoValido.
    """
    from pathlib import Path

    from .color import paginas_con_color
    from .conversion import normalizar
    from .models import Trabajo

    ruta = Path(ruta)
    doc = normalizar(ruta, ruta.parent / f"{ruta.stem}_pdf")
    try:
        colores = paginas_con_color(doc)
    except Exception:  # la clasificación es una ayuda: no debe impedir imprimir
        colores = []
    trabajo = Trabajo(
        nombre_original=nombre[:255], origen=origen, ruta_normalizada=str(doc.ruta),
        tipo_documento=doc.tipo, total_paginas=doc.paginas, paginas_color=colores,
    )
    trabajo.archivo.name = str(ruta.relative_to(Path(settings.MEDIA_ROOT))).replace("\\", "/")
    trabajo.save()
    return trabajo


ALTO_MINIATURA_SELECTOR = 160


def miniaturas_paginas(trabajo) -> list[str]:
    """URLs de una miniatura por página (se generan una vez y quedan en media/miniaturas/<id>/)."""
    from pathlib import Path

    import pymupdf

    carpeta = Path(settings.MEDIA_ROOT) / "miniaturas" / str(trabajo.pk)
    carpeta.mkdir(parents=True, exist_ok=True)
    urls = []
    doc = documento_de(trabajo)
    pdf = pymupdf.open(doc.ruta) if doc.tipo == "pdf" else None
    try:
        for n in range(1, trabajo.total_paginas + 1):
            archivo = carpeta / f"{n}.png"
            if not archivo.exists():
                if pdf is not None:
                    pagina = pdf[n - 1]
                    zoom = ALTO_MINIATURA_SELECTOR / pagina.rect.height
                    pagina.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False).save(archivo)
                else:
                    from PIL import ImageOps

                    with Image.open(doc.ruta) as img:
                        img = ImageOps.exif_transpose(img).convert("RGB")
                        img.thumbnail((ALTO_MINIATURA_SELECTOR * 2, ALTO_MINIATURA_SELECTOR))
                        img.save(archivo)
            urls.append(f"{settings.MEDIA_URL}miniaturas/{trabajo.pk}/{n}.png")
    finally:
        if pdf is not None:
            pdf.close()
    return urls


def tarifas_en_cero(perfil: PerfilImpresion) -> bool:
    """Sin costo de tinta ni de hoja: el precio saldría RD$ 0."""
    t = cargar_tarifas(perfil.impresora)
    costo, minimo = t.costo_hoja.get((perfil.tipo_papel.nombre, perfil.tamano), (0, 0))
    return not any(t.costo_cm2.values()) and not costo and not minimo


def documento_de(trabajo) -> Documento:
    from pathlib import Path

    return Documento(Path(trabajo.ruta_normalizada), trabajo.tipo_documento, trabajo.total_paginas)


def guardar_estimacion(trabajo, est: Estimacion, perfil: PerfilImpresion, paginas, escala) -> None:
    trabajo.perfil = perfil
    trabajo.perfil_nombre = perfil.nombre
    trabajo.impresora = perfil.impresora
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
    # El vigilante solo deja pasar trabajos enviados hace poco (ver vigilancia.es_del_sistema).
    from django.utils import timezone

    trabajo.enviado_en = timezone.now()
    trabajo.save(update_fields=["enviado_en"])

    def paginas():
        for _ in range(trabajo.copias):
            yield from rasterizar(
                doc, perfil.info_papel(), trabajo.escala, settings.DPI_IMPRESION, trabajo.paginas
            )

    try:
        obtener_controlador().imprimir(
            perfil.impresora.nombre_windows, bytes(perfil.devmode), paginas(),
            f"Printable#{trabajo.pk} {trabajo.nombre_original}",
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
