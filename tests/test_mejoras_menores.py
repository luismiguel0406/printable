"""Mejoras menores pendientes de la revisión de control total."""
import shutil
from pathlib import Path

import pytest
from django.conf import settings as conf
from django.contrib.auth.models import User
from django.urls import reverse
from PIL import Image

from impresora.models import Impresora
from impresora.servicios import sincronizar_impresoras
from trabajos.color import es_color
from trabajos.models import Bloqueo, Trabajo
from trabajos.vigilancia import Vigilante

FIX = Path(__file__).resolve().parent / "fixtures"
EPSON = "EPSON L355 Series"


@pytest.fixture
def entrada(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    carpeta = tmp_path / "entrada"
    carpeta.mkdir()
    return carpeta


# 1. PDF sin %%EOF al final = todavía se está escribiendo
def test_pdf_sin_fin_no_se_captura(entrada, controlador_falso, db):
    datos = (FIX / "cuatro.pdf").read_bytes()
    corte = datos.rfind(b"%%EOF")
    (entrada / "largo.pdf").write_bytes(datos[:corte])
    v = Vigilante(entrada, controlador_falso)
    v.revisar_carpeta(0)
    assert v.revisar_carpeta(1) == [] and v.revisar_carpeta(2) == []
    (entrada / "largo.pdf").write_bytes(datos)
    v.revisar_carpeta(3)
    assert len(v.revisar_carpeta(4)) == 1


# 2. PDF ilegible deja aviso en pantalla
def test_pdf_rechazado_avisa(client, entrada, controlador_falso, db):
    (entrada / "roto.pdf").write_bytes(b"%PDF basura %%EOF")
    v = Vigilante(entrada, controlador_falso)
    v.revisar_carpeta(0)
    v.revisar_carpeta(61)
    aviso = Bloqueo.objects.get(tipo="rechazado")
    assert aviso.documento == "roto.pdf"
    html = client.get(reverse("trabajos:bandeja")).content.decode()
    assert "No se pudo leer «roto.pdf»" in html and "rechazados" in html


# 3. Cambiar impresoras requiere usuario
def test_impresoras_requiere_usuario(cliente_anonimo, epson, admin_user):
    r = cliente_anonimo.post(reverse("impresora:guardar", args=[epson.pk]), {"alias": "x"})
    assert r.status_code == 302 and r.url.startswith("/entrar/")
    epson.refresh_from_db()
    assert epson.controlada and epson.alias == ""
    cliente_anonimo.force_login(admin_user)
    cliente_anonimo.post(reverse("impresora:guardar", args=[epson.pk]), {"alias": "Epson fotos"})
    epson.refresh_from_db()
    assert epson.alias == "Epson fotos" and not epson.controlada


def test_lista_de_impresoras_se_ve_sin_usuario(cliente_anonimo, epson):
    assert cliente_anonimo.get(reverse("impresora:lista")).status_code == 200


# 4. Impresora apagada / sin conexión no se ofrece
def test_impresora_sin_conexion_no_se_ofrece(db, controlador_falso, hp):
    controlador_falso.sin_conexion = {"HP DeskJet 2700"}
    sincronizar_impresoras()
    hp.refresh_from_db()
    assert hp.activa and not hp.en_linea
    assert hp not in Impresora.disponibles()
    controlador_falso.sin_conexion = set()
    sincronizar_impresoras()
    assert hp in Impresora.disponibles()


# 5. Papel amarillento es B/N; resaltador y rosado fuerte son color
def test_papel_amarillento_es_bn():
    assert not es_color(Image.new("RGB", (50, 50), (240, 228, 195)))


@pytest.mark.parametrize("rgb", [(255, 255, 100), (255, 150, 180), (220, 20, 20)])
def test_colores_claros_reales_son_color(rgb):
    assert es_color(Image.new("RGB", (50, 50), rgb))


# 6. Aviso de tarifas en cero
def test_aviso_tarifas_en_cero(client, settings, tmp_path, perfil_hp):
    settings.MEDIA_ROOT = tmp_path / "media"
    from django.core.files.uploadedfile import SimpleUploadedFile

    client.post(reverse("trabajos:imprimir"), {"archivo": SimpleUploadedFile("una.pdf", (FIX / "una.pdf").read_bytes())})
    t = Trabajo.objects.get()
    html = client.post(reverse("trabajos:estimacion", args=[t.pk]), {
        "impresora": perfil_hp.impresora_id, "perfil": perfil_hp.pk, "perfil_manual": "1",
        "copias": 1, "paginas": "", "escala": "ajustar"}).content.decode()
    assert "tarifas de esta impresora están en 0" in html


# 7. SQLite aguanta escrituras del vigilante y del servidor a la vez
def test_sqlite_configurado_para_concurrencia():
    opciones = conf.DATABASES["default"].get("OPTIONS", {})
    assert opciones.get("timeout", 0) >= 20
    assert "journal_mode=WAL" in opciones.get("init_command", "")


# 8. Impresora sugerida = la del último trabajo
def test_impresora_del_ultimo_trabajo(client, settings, tmp_path, epson, hp, perfil_hp, crear_perfil):
    settings.MEDIA_ROOT = tmp_path / "media"
    crear_perfil("Epson doc")
    Trabajo.objects.create(nombre_original="anterior", impresora=hp, estado="impreso")
    from django.core.files.uploadedfile import SimpleUploadedFile

    client.post(reverse("trabajos:imprimir"), {"archivo": SimpleUploadedFile("una.pdf", (FIX / "una.pdf").read_bytes())})
    t = Trabajo.objects.latest("pk")
    html = client.get(f"/?trabajo={t.pk}").content.decode()
    selector = html.split('id="id_impresora"')[1].split("</select>")[0]
    assert f'<option value="{hp.pk}" selected>' in selector


# 9. Un bloqueo que se repite después de vaciarse la cola se registra otra vez
def test_bloqueo_repetido_tras_vaciarse_la_cola(db, epson, controlador_falso, tmp_path):
    v = Vigilante(tmp_path, controlador_falso)
    controlador_falso.encolar(EPSON, "Tarea")
    v.revisar_colas()
    v.revisar_colas()  # cola vacía: se olvida el trabajo
    controlador_falso._siguiente_id = 1  # Windows reinicia los números
    controlador_falso.encolar(EPSON, "Tarea")
    v.revisar_colas()
    assert Bloqueo.objects.filter(tipo="bloqueo").count() == 2
    assert len(v._manejados) <= 1
