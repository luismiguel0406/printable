import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CODIGO = """
import json, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
from django.conf import settings
import django; django.setup()
print(json.dumps({
  "db": str(settings.DATABASES["default"]["NAME"]), "media": str(settings.MEDIA_ROOT),
  "entrada": str(settings.CARPETA_ENTRADA), "static": str(settings.STATIC_ROOT),
  "log": settings.LOGGING["handlers"]["archivo"]["filename"] if "archivo" in settings.LOGGING.get("handlers", {}) else None,
}))
"""


def ajustes(**env):
    entorno = {k: v for k, v in os.environ.items() if k not in ("PRINTABLE_DATOS", "PRINTABLE_ENTRADA")}
    entorno.update(env)
    salida = subprocess.run([sys.executable, "-c", CODIGO], cwd=RAIZ, env=entorno, capture_output=True, text=True, check=True)
    return json.loads(salida.stdout.strip().splitlines()[-1])


def test_con_carpeta_de_datos(tmp_path):
    datos = tmp_path / "Datos de Printable ñ"
    a = ajustes(PRINTABLE_DATOS=str(datos))
    assert a["db"] == str(datos / "db.sqlite3")
    assert a["media"] == str(datos / "media")
    assert a["entrada"] == str(datos / "entrada")
    assert a["log"] == str(datos / "logs" / "printable.log")
    assert a["static"] == str(RAIZ / "staticfiles")
    assert (datos / ".clave_secreta").exists() and (datos / "logs").is_dir()


def test_entrada_explicita_gana(tmp_path):
    assert ajustes(PRINTABLE_DATOS=str(tmp_path), PRINTABLE_ENTRADA=str(tmp_path / "otra"))["entrada"] == str(tmp_path / "otra")


def test_sin_carpeta_de_datos_como_antes():
    a = ajustes()
    assert a["db"] == str(RAIZ / "db.sqlite3") and a["media"] == str(RAIZ / "media")
    assert a["entrada"] == r"C:\printable\entrada"
