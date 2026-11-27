"""Pasos de sistema del instalador. Se ejecuta con el Python incluido:

  python.exe instalador\\configurar.py datos       crea carpetas y prepara la base
  python.exe instalador\\configurar.py clawpdf     impresora Printable + autoguardado + predeterminada
  python.exe instalador\\configurar.py colas       «iniciar al terminar la cola» en impresoras reales
  python.exe instalador\\configurar.py verificar   muestra el estado en JSON (código 1 si falta algo)
"""

import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from instalador.clawpdf import NOMBRE_IMPRESORA, RAIZ_REGISTRO, valores_registro  # noqa: E402

VIRTUALES = ["printable", "microsoft print to pdf", "microsoft xps document writer", "onenote", "fax", "clawpdf"]
CLAWPDF_DIRS = [Path(r"C:\Program Files\clawPDF"), Path(r"C:\Program Files (x86)\clawPDF")]


def carpeta_datos() -> Path:
    return Path(os.environ.get("PRINTABLE_DATOS") or Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Printable")


def es_impresora_real(nombre: str) -> bool:
    n = nombre.lower()
    return not any(v in n for v in VIRTUALES)


def comando_colas(nombre: str) -> list[str]:
    return ["rundll32.exe", "printui.dll,PrintUIEntry", "/Xs", "/n", nombre, "attributes", "+queued"]


def _impresoras() -> list[str]:
    import win32print

    return [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]


def datos() -> None:
    d = carpeta_datos()
    for sub in ["", "media", "entrada", "entrada/rechazados", "logs"]:
        (d / sub).mkdir(parents=True, exist_ok=True)
    os.environ["PRINTABLE_DATOS"] = str(d)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()
    from django.core.management import call_command

    call_command("migrate", interactive=False, verbosity=0)
    print(f"Datos listos en {d}")


def _setuphelper() -> Path | None:
    for base in CLAWPDF_DIRS:
        if (base / "SetupHelper.exe").exists():
            return base / "SetupHelper.exe"
    return None


def clawpdf() -> None:
    import winreg

    if NOMBRE_IMPRESORA not in _impresoras():
        ayudante = _setuphelper()
        if ayudante is None:
            raise SystemExit("No se encontró clawPDF (SetupHelper.exe). ¿Se instaló?")
        subprocess.run([str(ayudante), "/Printer=Add", f"/Name={NOMBRE_IMPRESORA}"], check=True, timeout=120)

    for sub, valores in valores_registro(carpeta_datos() / "entrada").items():
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RAIZ_REGISTRO + "\\" + sub) as clave:
            for nombre, valor in valores.items():
                winreg.SetValueEx(clave, nombre, 0, winreg.REG_SZ, valor)

    # Impresora predeterminada (por usuario) y sin que Windows la cambie sola.
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows NT\CurrentVersion\Windows") as clave:
        winreg.SetValueEx(clave, "LegacyDefaultPrinterMode", 0, winreg.REG_DWORD, 1)
    import win32print

    win32print.SetDefaultPrinter(NOMBRE_IMPRESORA)
    print("clawPDF configurado")


def colas() -> None:
    for nombre in _impresoras():
        if es_impresora_real(nombre):
            r = subprocess.run(comando_colas(nombre), timeout=60)
            print(f"{nombre}: {'ok' if r.returncode == 0 else 'no se pudo'}")


def verificar() -> int:
    estado = {"datos": carpeta_datos().is_dir(), "impresora_printable": False, "autoguardado": False,
              "carpeta_autoguardado": None, "predeterminada": None}
    try:
        import win32print
        import winreg

        estado["impresora_printable"] = NOMBRE_IMPRESORA in _impresoras()
        estado["predeterminada"] = win32print.GetDefaultPrinter()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RAIZ_REGISTRO + r"\ConversionProfiles\0\AutoSave") as clave:
            estado["autoguardado"] = winreg.QueryValueEx(clave, "Enabled")[0] == "True"
            estado["carpeta_autoguardado"] = winreg.QueryValueEx(clave, "TargetDirectory")[0]
    except Exception as e:  # noqa: BLE001
        estado["error"] = str(e)
    print(json.dumps(estado, ensure_ascii=False, indent=2))
    ok = estado["datos"] and estado["impresora_printable"] and estado["autoguardado"]
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    pasos = {"datos": datos, "clawpdf": clawpdf, "colas": colas}
    if not argv or argv[0] not in [*pasos, "verificar"]:
        print(__doc__)
        return 2
    if argv[0] == "verificar":
        return verificar()
    pasos[argv[0]]()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
