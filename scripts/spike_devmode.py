"""Prueba en la PC: ¿un perfil guardado conserva las opciones propias de Epson?

Uso (en Windows, desde la carpeta del proyecto, con el entorno activado):
  1) python scripts/spike_devmode.py
       Abre las preferencias de la Epson. Elige Epson Premium Glossy, calidad alta,
       4x6 sin bordes y acepta. Se guarda en spike_perfil.bin.
  2) Reinicia la PC.
  3) python scripts/spike_devmode.py --imprimir
       Imprime una imagen de prueba con la configuración guardada.
  4) python scripts/spike_devmode.py --revisar
       Vuelve a abrir la ventana con lo guardado: debe mostrar lo que elegiste.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw  # noqa: E402

from impresora.devmode import leer_campos  # noqa: E402
from impresora.windows import ControladorWindows  # noqa: E402

ARCHIVO = Path("spike_perfil.bin")
DPI = 360


def imagen_prueba(ancho_mm: float, alto_mm: float) -> Image.Image:
    w, h = round(ancho_mm / 25.4 * DPI), round(alto_mm / 25.4 * DPI)
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    for x in range(w):
        t = x / max(w - 1, 1)
        d.line([(x, 0), (x, h // 2)], fill=(int(255 * (1 - t)), int(255 * t), 128))
    franja = w // 4
    for i, color in enumerate([(0, 255, 255), (255, 0, 255), (255, 255, 0), (0, 0, 0)]):
        d.rectangle([i * franja, h // 2, (i + 1) * franja, h], fill=color)
    return img


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--impresora", default="EPSON L355 Series")
    p.add_argument("--imprimir", action="store_true")
    p.add_argument("--revisar", action="store_true")
    a = p.parse_args()
    c = ControladorWindows()
    print("Impresoras:", c.listar_impresoras())

    if a.imprimir or a.revisar:
        raw = ARCHIVO.read_bytes()
        print("Campos:", leer_campos(raw))
        info = c.info_papel(a.impresora, raw)
        print("Papel:", info)
        if a.revisar:
            c.abrir_preferencias(a.impresora, raw)
        else:
            c.imprimir(a.impresora, raw, [imagen_prueba(info.imprimible_ancho_mm, info.imprimible_alto_mm)], "Spike perfil")
            print("Enviado a la impresora.")
        return

    raw = c.devmode_predeterminado(a.impresora)
    nuevo = c.abrir_preferencias(a.impresora, raw)
    if nuevo is None:
        print("Cancelado.")
        return
    ARCHIVO.write_bytes(nuevo)
    print(f"Guardado {len(nuevo)} bytes en {ARCHIVO}. Campos:", leer_campos(nuevo))
    print("Versión driver:", c.version_driver(a.impresora))


if __name__ == "__main__":
    main()
