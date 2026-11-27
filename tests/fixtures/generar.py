"""Regenera los archivos de prueba: python tests/fixtures/generar.py"""
from pathlib import Path

import pymupdf
from PIL import Image

AQUI = Path(__file__).parent


def pdf(nombre, paginas, cifrado=False):
    doc = pymupdf.open()
    for i in range(paginas):
        p = doc.new_page(width=612, height=792)  # Carta
        p.insert_text((72, 72), f"Pagina {i + 1}", fontsize=24)
        p.draw_rect(pymupdf.Rect(72, 100, 300, 300), color=(0, 0, 0), fill=(0, 0, 0))
    kw = {}
    if cifrado:
        kw = dict(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="clave", owner_pw="clave")
    doc.save(AQUI / nombre, **kw)


pdf("una.pdf", 1)
pdf("cuatro.pdf", 4)
pdf("protegido.pdf", 1, cifrado=True)
(AQUI / "roto.pdf").write_bytes(b"%PDF-1.4\nbasura que no es un pdf")
Image.new("RGB", (60, 40), (200, 30, 30)).save(AQUI / "foto.jpg")
(AQUI / "doc.docx").write_bytes(b"PK\x03\x04 no es un docx real")
(AQUI / "x.txt").write_text("hola")
