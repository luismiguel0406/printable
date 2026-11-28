import shutil
from pathlib import Path

import pytest
from django.urls import reverse
from django.utils import timezone

from trabajos.models import Bloqueo, Trabajo
from trabajos.vigilancia import Vigilante, es_del_sistema

FIX = Path(__file__).resolve().parent.parent / "fixtures"
EPSON = "EPSON L355 Series"


@pytest.fixture
def entrada(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    carpeta = tmp_path / "entrada"
    carpeta.mkdir()
    return carpeta


@pytest.fixture
def vigilante(entrada, controlador_falso, db):
    return Vigilante(entrada, controlador_falso)


def test_captura_pdf_estable(vigilante, entrada):
    shutil.copy(FIX / "una.pdf", entrada / "Factura_20261127093000.pdf")
    assert vigilante.revisar_carpeta(0) == []  # primera vez: solo mide
    [t] = vigilante.revisar_carpeta(1)
    assert t.origen == "capturado" and t.total_paginas == 1 and t.nombre_original == "Factura"
    assert not (entrada / "Factura_20261127093000.pdf").exists()
    assert Path(t.archivo.path).exists() and t.paginas_color == [False]


def test_pdf_a_medio_escribir_no_se_captura(vigilante, entrada):
    datos = (FIX / "una.pdf").read_bytes()
    destino = entrada / "doc.pdf"
    destino.write_bytes(datos[:200])
    vigilante.revisar_carpeta(0)
    destino.write_bytes(datos)
    assert vigilante.revisar_carpeta(1) == []  # el tamaño cambió
    assert len(vigilante.revisar_carpeta(2)) == 1


def test_pdf_ilegible_va_a_rechazados_tras_60s(vigilante, entrada):
    (entrada / "roto.pdf").write_bytes(b"%PDF basura")
    vigilante.revisar_carpeta(0)
    assert vigilante.revisar_carpeta(30) == [] and (entrada / "roto.pdf").exists()
    vigilante.revisar_carpeta(61)
    assert not (entrada / "roto.pdf").exists() and (entrada / "rechazados" / "roto.pdf").exists()


def test_mismo_nombre_dos_veces_no_se_pisa(vigilante, entrada):
    shutil.copy(FIX / "una.pdf", entrada / "carta.pdf")
    vigilante.revisar_carpeta(0)
    [a] = vigilante.revisar_carpeta(1)
    shutil.copy(FIX / "cuatro.pdf", entrada / "carta.pdf")
    vigilante.revisar_carpeta(2)
    [b] = vigilante.revisar_carpeta(3)
    assert a.archivo.path != b.archivo.path
    assert Path(a.archivo.path).exists() and Path(b.archivo.path).exists()
    assert (a.total_paginas, b.total_paginas) == (1, 4)


def test_titulo_del_pdf_como_nombre(vigilante, entrada):
    import pymupdf

    doc = pymupdf.open(FIX / "una.pdf")
    doc.set_metadata({"title": "Tarea de Historia"})
    doc.save(entrada / "x_20261127.pdf")
    vigilante.revisar_carpeta(0)
    [t] = vigilante.revisar_carpeta(1)
    assert t.nombre_original == "Tarea de Historia"


def test_bloquea_trabajo_directo(vigilante, controlador_falso):
    controlador_falso.encolar(EPSON, "Tarea.docx - Word", "pedro")
    [b] = vigilante.revisar_colas()
    assert b.documento == "Tarea.docx - Word" and b.usuario == "pedro"
    assert controlador_falso.cancelados == [(EPSON, 1)]
    assert controlador_falso.listar_trabajos(EPSON) == []


def test_no_cancela_trabajos_del_sistema(vigilante, controlador_falso):
    t = Trabajo.objects.create(nombre_original="foto.jpg", enviado_en=timezone.now())
    controlador_falso.encolar(EPSON, f"Printable#{t.pk} foto.jpg")
    assert vigilante.revisar_colas() == [] and controlador_falso.cancelados == []


def test_prefijo_con_id_inexistente_se_bloquea(vigilante, controlador_falso):
    controlador_falso.encolar(EPSON, "Printable#99999 x")
    assert len(vigilante.revisar_colas()) == 1


def test_no_vigila_no_controladas_ni_inactivas(vigilante, controlador_falso, hp, epson):
    hp.controlada = False
    hp.save()
    controlador_falso.encolar("HP DeskJet 2700", "Algo")
    epson.activa = False
    epson.save()
    controlador_falso.encolar(EPSON, "Otra cosa")
    assert vigilante.revisar_colas() == []


def test_no_registra_dos_veces_si_no_se_pudo_cancelar(vigilante, controlador_falso, monkeypatch):
    controlador_falso.encolar(EPSON, "Terco")
    monkeypatch.setattr(controlador_falso, "cancelar_trabajo", lambda i, n: None)
    vigilante.revisar_colas()
    vigilante.revisar_colas()
    assert Bloqueo.objects.count() == 1


@pytest.mark.parametrize("doc,esperado", [("Printable#{pk} a.pdf", True), ("Printable#{pk}", False), ("printable#{pk} a", False), ("x Printable#{pk} a", False)])
def test_es_del_sistema(db, doc, esperado):
    t = Trabajo.objects.create(nombre_original="a", enviado_en=timezone.now())
    assert es_del_sistema(doc.format(pk=t.pk)) is esperado


def test_bandeja_muestra_capturados_y_bloqueos(client, vigilante, entrada, controlador_falso):
    shutil.copy(FIX / "una.pdf", entrada / "Recibo.pdf")
    vigilante.revisar_carpeta(0)
    [t] = vigilante.revisar_carpeta(1)
    controlador_falso.encolar(EPSON, "Directo.txt - Bloc de notas")
    [b] = vigilante.revisar_colas()
    html = client.get(reverse("trabajos:bandeja")).content.decode()
    assert "Recibo" in html and f"?trabajo={t.pk}" in html and "Directo.txt" in html
    client.post(reverse("trabajos:bloqueo_visto", args=[b.pk]))
    assert "Directo.txt" not in client.get(reverse("trabajos:bandeja")).content.decode()
    assert "Directo.txt" in client.get(reverse("trabajos:historial")).content.decode()


def test_ciclo_no_muere_por_errores(vigilante, monkeypatch):
    monkeypatch.setattr(vigilante, "revisar_colas", lambda: 1 / 0)
    vigilante.ciclo(0)  # no lanza


def test_iniciar_solo_carpeta_no_crea_hilo_de_colas(tmp_path, controlador_falso):
    from trabajos.vigilancia import Vigilante

    v = Vigilante(tmp_path, controlador_falso)
    v.iniciar(colas=False, carpeta=True)
    try:
        assert [h.name for h in v._hilos] == ["vigilante-carpeta"]
    finally:
        v.detener()


def test_iniciar_solo_colas(tmp_path, controlador_falso):
    from trabajos.vigilancia import Vigilante

    v = Vigilante(tmp_path, controlador_falso)
    v.iniciar(colas=True, carpeta=False)
    try:
        assert [h.name for h in v._hilos] == ["vigilante-colas"]
    finally:
        v.detener()
