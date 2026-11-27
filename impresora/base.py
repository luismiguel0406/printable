"""Tipos compartidos y la interfaz que todo backend de impresora implementa."""

from dataclasses import dataclass
from typing import Iterable, Protocol

from PIL import Image


@dataclass(frozen=True)
class InfoPapel:
    ancho_mm: float
    alto_mm: float
    imprimible_x_mm: float
    imprimible_y_mm: float
    imprimible_ancho_mm: float
    imprimible_alto_mm: float


@dataclass(frozen=True)
class CamposDevmode:
    tamano_codigo: int
    ancho_decimas_mm: int
    alto_decimas_mm: int
    orientacion: int
    calidad: int
    color: bool
    copias: int
    version_driver: int


@dataclass(frozen=True)
class TrabajoCola:
    id: int
    documento: str
    usuario: str


class ErrorImpresora(Exception):
    """Falla al hablar con la impresora o su driver. El mensaje es para el usuario."""


class ControladorImpresora(Protocol):
    def listar_impresoras(self) -> list[str]: ...

    def devmode_predeterminado(self, impresora: str) -> bytes: ...

    def abrir_preferencias(self, impresora: str, devmode: bytes) -> bytes | None: ...

    def info_papel(self, impresora: str, devmode: bytes) -> InfoPapel: ...

    def version_driver(self, impresora: str) -> str: ...

    def estado(self, impresora: str) -> str | None: ...  # motivo si no puede imprimir

    def listar_trabajos(self, impresora: str) -> list[TrabajoCola]: ...

    def cancelar_trabajo(self, impresora: str, id: int) -> None: ...

    def imprimir(
        self,
        impresora: str,
        devmode: bytes,
        paginas: Iterable[Image.Image],
        nombre_documento: str,
    ) -> None: ...


def envolver_errores(funcion):
    """Convierte cualquier excepción del sistema en ErrorImpresora (mensaje para el usuario)."""
    import functools

    @functools.wraps(funcion)
    def envuelta(*args, **kwargs):
        try:
            return funcion(*args, **kwargs)
        except ErrorImpresora:
            raise
        except Exception as e:
            raise ErrorImpresora(f"Error de la impresora: {e}") from e

    return envuelta
