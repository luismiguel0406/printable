"""Lanzador de Printable instalado: servidor en segundo plano + ícono junto al reloj.

Uso: pythonw.exe lanzador.py [--abrir]
  --abrir  abre el navegador al arrancar (acceso directo del escritorio).
Si el sistema ya está corriendo, solo abre el navegador.
"""

import logging
import os
import sys
import threading
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from config import servir  # noqa: E402

log = logging.getLogger("printable.lanzador")


def preparar_entorno() -> None:
    os.environ.setdefault("PRINTABLE_DATOS", str(Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Printable"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def _mensaje_error(texto: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, texto, "Printable", 0x10)
    except Exception:
        print(texto, file=sys.stderr)


def _icono():
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for (x, y), color in zip([(6, 6), (34, 6), (6, 34), (34, 34)],
                             ["#4fc3dc", "#e0629f", "#e6c35c", "#e4e8ee"]):
        d.ellipse([x, y, x + 24, y + 24], fill=color)
    return img


def iniciar(abrir: bool) -> None:
    try:
        servir.preparar()
    except Exception as e:
        logging.getLogger("printable").exception("No se pudo arrancar")
        _mensaje_error(f"Printable no pudo arrancar:\n\n{e}\n\nRevisa el archivo de registro en la carpeta de datos.")
        raise
    hilo = threading.Thread(target=servir.servir, name="servidor", daemon=True)
    hilo.start()
    if abrir:
        threading.Timer(1.5, webbrowser.open, args=[servir.URL]).start()

    try:
        import pystray

        menu = pystray.Menu(
            pystray.MenuItem("Abrir Printable", lambda: webbrowser.open(servir.URL), default=True),
            pystray.MenuItem("Salir", lambda icono: icono.stop()),
        )
        pystray.Icon("printable", _icono(), "Printable", menu).run()
    except Exception:
        # Sin escritorio (p. ej. un servicio o una sesión remota): el sistema sigue funcionando.
        logging.getLogger("printable").exception("No se pudo mostrar el ícono; el servidor sigue activo")
        hilo.join()


def main(argv: list[str]) -> int:
    preparar_entorno()
    abrir = "--abrir" in argv
    if servir.servidor_activo():
        webbrowser.open(servir.URL)
        return 0
    iniciar(abrir)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
