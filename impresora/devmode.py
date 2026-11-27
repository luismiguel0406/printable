"""Lectura y ajuste de los campos públicos de un DEVMODEW guardado como bytes crudos.

Solo usa `struct`, así que funciona y se prueba en cualquier sistema operativo.
La parte privada del driver (después de dmSize) nunca se modifica.
"""

import struct

from .base import CamposDevmode

TAMANO_MINIMO = 220  # sizeof(DEVMODEW) público

_OFF_DRIVER_VERSION = 66
_OFF_ORIENTACION = 76
_OFF_PAPEL = 78  # dmPaperSize, dmPaperLength, dmPaperWidth
_OFF_COPIAS = 86
_OFF_CALIDAD = 90  # dmPrintQuality, dmColor

DMCOLOR_COLOR = 2


def _validar(raw: bytes) -> None:
    if len(raw) < TAMANO_MINIMO:
        raise ValueError(f"DEVMODE inválido: {len(raw)} bytes (mínimo {TAMANO_MINIMO})")


def leer_campos(raw: bytes) -> CamposDevmode:
    _validar(raw)
    (version,) = struct.unpack_from("<H", raw, _OFF_DRIVER_VERSION)
    (orientacion,) = struct.unpack_from("<h", raw, _OFF_ORIENTACION)
    papel, largo, ancho = struct.unpack_from("<hhh", raw, _OFF_PAPEL)
    (copias,) = struct.unpack_from("<h", raw, _OFF_COPIAS)
    calidad, color = struct.unpack_from("<hh", raw, _OFF_CALIDAD)
    return CamposDevmode(
        tamano_codigo=papel,
        ancho_decimas_mm=ancho,
        alto_decimas_mm=largo,
        orientacion=orientacion,
        calidad=calidad,
        color=color == DMCOLOR_COLOR,
        copias=copias,
        version_driver=version,
    )


def con_copias(raw: bytes, copias: int) -> bytes:
    _validar(raw)
    buf = bytearray(raw)
    struct.pack_into("<h", buf, _OFF_COPIAS, copias)
    return bytes(buf)
