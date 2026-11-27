from pathlib import Path

import pytest

from trabajos import conversion
from trabajos.conversion import ArchivoNoValido, Documento, normalizar

FIX = Path(__file__).resolve().parent.parent / "fixtures"


def test_pdf_cuenta_paginas(tmp_path):
    assert normalizar(FIX / "cuatro.pdf", tmp_path) == Documento(FIX / "cuatro.pdf", "pdf", 4)


def test_foto(tmp_path):
    d = normalizar(FIX / "foto.jpg", tmp_path)
    assert d.tipo == "imagen" and d.paginas == 1


@pytest.mark.parametrize(
    "nombre,msg",
    [("protegido.pdf", "contraseña"), ("roto.pdf", "dañado"), ("x.txt", "no soportado")],
)
def test_invalidos(tmp_path, nombre, msg):
    with pytest.raises(ArchivoNoValido, match=msg):
        normalizar(FIX / nombre, tmp_path)


def test_imagen_rota(tmp_path):
    falsa = tmp_path / "falsa.jpg"
    falsa.write_bytes(b"no es una imagen")
    with pytest.raises(ArchivoNoValido, match="dañada"):
        normalizar(falsa, tmp_path)


def test_word_usa_convertidor(tmp_path, monkeypatch):
    monkeypatch.setattr(conversion, "convertir_word_a_pdf", lambda r, d: FIX / "una.pdf")
    d = normalizar(FIX / "doc.docx", tmp_path)
    assert d.tipo == "pdf" and d.paginas == 1


def test_word_sin_convertidores(tmp_path, monkeypatch):
    monkeypatch.setattr(conversion, "_word_disponible", lambda: False)
    monkeypatch.setattr(conversion, "_buscar_soffice", lambda: None)
    with pytest.raises(ArchivoNoValido, match="Office o LibreOffice"):
        conversion.convertir_word_a_pdf(FIX / "doc.docx", tmp_path)
