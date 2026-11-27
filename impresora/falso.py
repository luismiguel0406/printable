"""Backend falso: permite desarrollar y probar sin Windows ni impresora."""

import struct
from typing import Iterable

from PIL import Image

from .base import ErrorImpresora, InfoPapel, TrabajoCola
from .devmode import _OFF_CALIDAD, leer_campos

IMPRESORA = "EPSON L355 Series"
MARGEN_MM = 3.0


def _devmode_carta() -> bytes:
    buf = bytearray(260)
    buf[0:34] = IMPRESORA.encode("utf-16-le")
    struct.pack_into("<HHHH", buf, 64, 0x0401, 0x0400, 220, 40)
    struct.pack_into("<h", buf, 76, 1)  # vertical
    struct.pack_into("<hhh", buf, 78, 1, 2794, 2159)  # Carta
    struct.pack_into("<h", buf, 86, 1)
    struct.pack_into("<hh", buf, 90, 360, 2)  # 360 ppp, color
    buf[220:] = b"EPSON-PRIVADO".ljust(40, b"\x00")
    return bytes(buf)


class ControladorFalso:
    def __init__(self) -> None:
        self.cancelar = False
        self.fallar = False
        self.version = "EPSON L355 Series v3.0"
        self.impresos: list[tuple[str, bytes, list[Image.Image], str]] = []
        self.impresoras: list[str] = [IMPRESORA]
        self.colas: dict[str, list[TrabajoCola]] = {}
        self.cancelados: list[tuple[str, int]] = []
        self._siguiente_id = 1

    def _validar(self, impresora: str) -> None:
        if impresora not in self.impresoras:
            raise ErrorImpresora(f"No se encontró la impresora «{impresora}»")

    def listar_impresoras(self) -> list[str]:
        return list(self.impresoras)

    def devmode_predeterminado(self, impresora: str) -> bytes:
        self._validar(impresora)
        return _devmode_carta()

    def abrir_preferencias(self, impresora: str, devmode: bytes) -> bytes | None:
        self._validar(impresora)
        if self.cancelar:
            return None
        buf = bytearray(devmode)
        struct.pack_into("<h", buf, _OFF_CALIDAD, 600)
        return bytes(buf)

    def info_papel(self, impresora: str, devmode: bytes) -> InfoPapel:
        self._validar(impresora)
        c = leer_campos(devmode)
        ancho, alto = c.ancho_decimas_mm / 10, c.alto_decimas_mm / 10
        if c.orientacion == 2:
            ancho, alto = alto, ancho
        return InfoPapel(
            ancho, alto, MARGEN_MM, MARGEN_MM, ancho - 2 * MARGEN_MM, alto - 2 * MARGEN_MM
        )

    def version_driver(self, impresora: str) -> str:
        self._validar(impresora)
        return self.version

    def imprimir(
        self,
        impresora: str,
        devmode: bytes,
        paginas: Iterable[Image.Image],
        nombre_documento: str,
    ) -> None:
        if self.fallar:
            raise ErrorImpresora("Impresora desconectada")
        self._validar(impresora)
        self.impresos.append((impresora, devmode, list(paginas), nombre_documento))


    def encolar(self, impresora: str, documento: str, usuario: str = "cliente") -> int:
        trabajo = TrabajoCola(self._siguiente_id, documento, usuario)
        self._siguiente_id += 1
        self.colas.setdefault(impresora, []).append(trabajo)
        return trabajo.id

    def listar_trabajos(self, impresora: str) -> list[TrabajoCola]:
        self._validar(impresora)
        return list(self.colas.get(impresora, []))

    def cancelar_trabajo(self, impresora: str, id: int) -> None:
        self._validar(impresora)
        self.colas[impresora] = [t for t in self.colas.get(impresora, []) if t.id != id]
        self.cancelados.append((impresora, id))


_instancia: ControladorFalso | None = None


def instancia() -> ControladorFalso:
    global _instancia
    if _instancia is None:
        _instancia = ControladorFalso()
    return _instancia


def reiniciar() -> None:
    global _instancia
    _instancia = None
