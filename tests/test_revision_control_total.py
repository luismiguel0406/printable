"""Pruebas de los hallazgos de la revisión final de feat/control-total."""
import shutil
import threading
import time
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.urls import reverse
from django.utils import timezone

from trabajos.models import Bloqueo, Trabajo
from trabajos.vigilancia import Vigilante, es_del_sistema

FIX = Path(__file__).resolve().parent / "fixtures"
EPSON = "EPSON L355 Series"


# Hallazgo 1
def test_historial_muestra_bloqueos_en_el_contenido(client, db):
    Bloqueo.objects.create(impresora_nombre=EPSON, documento="Directo.docx", usuario="ana")
    html = client.get(reverse("trabajos:historial")).content.decode()
    titulo = html.split("<title>")[1].split("</title>")[0]
    assert "Impresiones bloqueadas" not in titulo
    assert "Directo.docx" in html.split("<main>")[1]


# Hallazgos 2 y 3: migración desde una base de datos v1
V1 = [("impresora", None), ("perfiles", "0001_initial"), ("tarifas", "0003_recargatinta"),
      ("trabajos", "0002_trabajo_ruta_normalizada_trabajo_tipo_documento")]


@pytest.mark.django_db(transaction=True)
def test_migracion_v1_con_nombre_distinto_conserva_tarifas_y_perfiles():
    ex = MigrationExecutor(connection)
    ex.migrate(V1)
    viejo = ex.loader.project_state([n for n in V1 if n[1]]).apps
    tipo = viejo.get_model("tarifas", "TipoPapel").objects.get(nombre="Glossy")
    p = viejo.get_model("perfiles", "PerfilImpresion").objects.create(
        nombre="Foto", impresora="EPSON L355 Series (Copiar 1)", devmode=b"x" * 260, tamano="4x6",
        ancho_mm=101.6, alto_mm=152.4, imprimible_x_mm=0, imprimible_y_mm=0,
        imprimible_ancho_mm=101.6, imprimible_alto_mm=152.4, tipo_papel=tipo)
    viejo.get_model("perfiles", "PerfilImpresion").objects.create(
        nombre="HP", impresora="HP DeskJet 2700", devmode=b"x" * 260, tamano="Carta",
        ancho_mm=215.9, alto_mm=279.4, imprimible_x_mm=0, imprimible_y_mm=0,
        imprimible_ancho_mm=215.9, imprimible_alto_mm=279.4, tipo_papel=tipo)
    viejo.get_model("trabajos", "Trabajo").objects.create(nombre_original="a.pdf", perfil=p, estado="impreso")
    viejo.get_model("trabajos", "Trabajo").objects.create(nombre_original="b.pdf", estado="impreso")

    ex = MigrationExecutor(connection)
    ex.loader.build_graph()
    ex.migrate(ex.loader.graph.leaf_nodes())
    nuevo = ex.loader.project_state(ex.loader.graph.leaf_nodes()).apps
    Impresora = nuevo.get_model("impresora", "Impresora")
    CostoTinta = nuevo.get_model("tarifas", "CostoTinta")
    epson = Impresora.objects.get(nombre_windows="EPSON L355 Series (Copiar 1)")
    assert epson.predeterminada and Impresora.objects.filter(nombre_windows=EPSON).count() == 0
    assert CostoTinta.objects.filter(impresora=epson).exclude(costo_cm2=0).count() == 4
    hp = Impresora.objects.get(nombre_windows="HP DeskJet 2700")
    assert CostoTinta.objects.filter(impresora=hp).count() == 4
    assert nuevo.get_model("perfiles", "PerfilImpresion").objects.get(nombre="Foto").impresora_id == epson.pk
    trabajos = nuevo.get_model("trabajos", "Trabajo").objects
    assert trabajos.filter(impresora__isnull=True).count() == 0
    assert trabajos.get(nombre_original="b.pdf").impresora_id == epson.pk


# Hallazgo 4
def test_colas_se_revisan_mientras_se_captura(tmp_path):
    v = Vigilante(tmp_path, controlador=object())
    llamadas = []
    v.revisar_carpeta = lambda ahora: time.sleep(1.5)
    v.revisar_colas = lambda: llamadas.append(1)
    v._sincronizar = lambda: None
    v.iniciar()
    time.sleep(1.2)
    v.detener()
    assert len(llamadas) >= 2
    assert {"vigilante-colas", "vigilante-carpeta"} <= {t.name for t in threading.enumerate()}


# Hallazgo 5
@pytest.fixture
def capturado(settings, tmp_path, controlador_falso, db):
    settings.MEDIA_ROOT = tmp_path / "media"
    entrada = tmp_path / "entrada"
    entrada.mkdir()
    shutil.copy(FIX / "una.pdf", entrada / "Recibo.pdf")
    v = Vigilante(entrada, controlador_falso)
    v.revisar_carpeta(0)
    return v.revisar_carpeta(1)[0]


def test_capturado_sigue_en_bandeja_despues_de_abrirlo(client, capturado, crear_perfil):
    p = crear_perfil("Doc")
    client.post(reverse("trabajos:estimacion", args=[capturado.pk]), {
        "impresora": p.impresora_id, "perfil": p.pk, "perfil_manual": "1", "copias": 1, "paginas": "", "escala": "ajustar"})
    assert "Recibo" in client.get(reverse("trabajos:bandeja")).content.decode()
    client.post(reverse("trabajos:quitar", args=[capturado.pk]))
    assert "Recibo" not in client.get(reverse("trabajos:bandeja")).content.decode()


def test_historial_enlaza_trabajos_sin_imprimir(client, capturado):
    assert f"?trabajo={capturado.pk}" in client.get(reverse("trabajos:historial")).content.decode()


# Re-graduado: un archivo bloqueado por Windows no detiene el resto
def test_archivo_bloqueado_no_detiene_la_revision(settings, tmp_path, controlador_falso, db, monkeypatch):
    settings.MEDIA_ROOT = tmp_path / "media"
    entrada = tmp_path / "entrada"
    entrada.mkdir()
    shutil.copy(FIX / "una.pdf", entrada / "a.pdf")
    shutil.copy(FIX / "una.pdf", entrada / "b.pdf")
    v = Vigilante(entrada, controlador_falso)
    v.revisar_carpeta(0)
    original = shutil.move

    def mover(origen, destino):
        if str(origen).endswith("a.pdf"):
            raise PermissionError("en uso por otro proceso")
        return original(origen, destino)

    monkeypatch.setattr(shutil, "move", mover)
    capturados = v.revisar_carpeta(1)
    assert [t.nombre_original for t in capturados] == ["b"]
    assert (entrada / "a.pdf").exists()


# Re-graduado: no basta con poner "Printable#<id>" en el nombre del documento
def test_trabajo_no_enviado_no_autoriza(db):
    t = Trabajo.objects.create(nombre_original="viejo")
    assert not es_del_sistema(f"Printable#{t.pk} tarea.docx")


def test_trabajo_enviado_hace_rato_no_autoriza(db):
    t = Trabajo.objects.create(nombre_original="viejo", enviado_en=timezone.now() - timedelta(hours=3))
    assert not es_del_sistema(f"Printable#{t.pk} tarea.docx")


def test_trabajo_recien_enviado_autoriza(db):
    t = Trabajo.objects.create(nombre_original="nuevo", enviado_en=timezone.now())
    assert es_del_sistema(f"Printable#{t.pk} nuevo")


def test_imprimir_marca_enviado(client, crear_perfil, controlador_falso, settings, tmp_path):
    from trabajos import servicios

    settings.MEDIA_ROOT = tmp_path / "media"
    p = crear_perfil("Doc")
    t = Trabajo.objects.create(nombre_original="x", perfil=p, paginas=[1], copias=1, tipo_documento="pdf",
                               ruta_normalizada=str(FIX / "una.pdf"), total_paginas=1, total=Decimal("5"))
    servicios.imprimir_trabajo(t)
    t.refresh_from_db()
    assert t.enviado_en is not None
