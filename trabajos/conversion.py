"""Normaliza los archivos del cliente a PDF o imagen."""

import importlib.util
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pymupdf
from PIL import Image

EXT_IMAGEN = {".jpg", ".jpeg", ".png"}
EXT_PDF = {".pdf"}
EXT_WORD = {".doc", ".docx"}
SOFFICE_WINDOWS = [
    Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
    Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
]


class ArchivoNoValido(Exception):
    """El archivo no se puede usar. El mensaje es para el usuario."""


@dataclass
class Documento:
    ruta: Path
    tipo: Literal["pdf", "imagen"]
    paginas: int


RAIZ = Path(__file__).resolve().parent.parent
TIEMPO_MAXIMO = 180  # segundos


def _word_disponible() -> bool:
    return sys.platform == "win32" and importlib.util.find_spec("win32com") is not None


def _convertir_con_word(ruta: Path, salida: Path) -> bool:
    """Word por COM en un proceso aparte: aísla COM del servidor y se corta si se cuelga."""
    try:
        subprocess.run(
            [sys.executable, "-m", "trabajos.word_a_pdf", str(ruta.resolve()), str(salida.resolve())],
            cwd=RAIZ, check=True, capture_output=True, timeout=TIEMPO_MAXIMO,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return salida.exists()


def _buscar_soffice() -> str | None:
    encontrado = shutil.which("soffice")
    if encontrado:
        return encontrado
    for ruta in SOFFICE_WINDOWS:
        if ruta.exists():
            return str(ruta)
    return None


def convertir_word_a_pdf(ruta: Path, destino: Path) -> Path:
    destino.mkdir(parents=True, exist_ok=True)
    salida = destino / (ruta.stem + ".pdf")
    if _word_disponible() and _convertir_con_word(ruta, salida):
        return salida
    soffice = _buscar_soffice()
    if soffice:
        try:
            subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(destino), str(ruta)],
                check=True, capture_output=True, timeout=TIEMPO_MAXIMO,
            )
        except (subprocess.SubprocessError, OSError) as e:
            raise ArchivoNoValido("No se pudo convertir el Word: el archivo parece estar dañado") from e
        if salida.exists():
            return salida
    raise ArchivoNoValido("No se pudo convertir el Word: instala Microsoft Office o LibreOffice")


def _abrir_pdf(ruta: Path) -> Documento:
    try:
        with pymupdf.open(ruta) as doc:
            if doc.needs_pass:
                raise ArchivoNoValido("El PDF está protegido con contraseña")
            if doc.page_count == 0:
                raise ArchivoNoValido("El PDF no tiene páginas")
            return Documento(ruta, "pdf", doc.page_count)
    except ArchivoNoValido:
        raise
    except Exception as e:
        raise ArchivoNoValido("El PDF está dañado o no se puede leer") from e


def normalizar(ruta: Path, destino: Path) -> Documento:
    ext = ruta.suffix.lower()
    if ext in EXT_PDF:
        return _abrir_pdf(ruta)
    if ext in EXT_IMAGEN:
        try:
            with Image.open(ruta) as img:
                img.verify()
            with Image.open(ruta) as img:  # verify() no decodifica: hay que cargarla
                img.load()
        except Image.DecompressionBombError as e:
            raise ArchivoNoValido("La imagen es demasiado grande para imprimirla") from e
        except Exception as e:
            raise ArchivoNoValido("La imagen está dañada o no se puede leer") from e
        return Documento(ruta, "imagen", 1)
    if ext in EXT_WORD:
        return _abrir_pdf(convertir_word_a_pdf(ruta, destino))
    raise ArchivoNoValido(f"Tipo de archivo no soportado: {ext or 'sin extensión'}")
