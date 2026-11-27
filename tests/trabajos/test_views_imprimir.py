from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from trabajos.models import Trabajo

FIX = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture(autouse=True)
def media_temporal(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


def subir(client, nombre, contenido):
    return client.post(reverse("trabajos:imprimir"), {"archivo": SimpleUploadedFile(nombre, contenido)})


def estimar(client, trabajo, perfil, copias=1, paginas="", escala="ajustar"):
    return client.post(
        reverse("trabajos:estimacion", args=[trabajo.pk]),
        {"impresora": perfil.impresora_id, "perfil": perfil.pk, "perfil_manual": "1",
         "copias": copias, "paginas": paginas, "escala": escala},
    )


@pytest.fixture
def trabajo_cuatro_paginas(client, db):
    subir(client, "cuatro.pdf", (FIX / "cuatro.pdf").read_bytes())
    return Trabajo.objects.get()


@pytest.fixture
def trabajo_estimado_2_copias(client, db, perfil_glossy_4x6):
    subir(client, "una.pdf", (FIX / "una.pdf").read_bytes())
    t = Trabajo.objects.get()
    estimar(client, t, perfil_glossy_4x6, copias=2)
    t.refresh_from_db()
    return t


def confirmar(client, t):
    t.refresh_from_db()
    return client.post(reverse("trabajos:confirmar", args=[t.pk]), {"huella": t.huella()})


def test_pagina_principal(client, db):
    r = client.get("/")
    assert r.status_code == 200 and "Arrastra" in r.content.decode()


def test_subir_pdf_y_estimar(client, db, perfil_glossy_4x6):
    r = subir(client, "a.pdf", (FIX / "una.pdf").read_bytes())
    t = Trabajo.objects.get()
    assert r.status_code == 302 and f"trabajo={t.pk}" in r.url
    assert t.total_paginas == 1
    r = estimar(client, t, perfil_glossy_4x6, copias=2)
    html = r.content.decode()
    t.refresh_from_db()
    assert "RD$" in html and "data:image/png;base64" in html
    assert t.total > 0 and t.copias == 2 and t.perfil_nombre == "Foto glossy 4x6"
    assert t.area_cm2 > 0 and len(t.coberturas) == 1


def test_archivo_roto_muestra_error(client, db):
    r = subir(client, "r.pdf", b"basura")
    assert r.status_code == 200 and "dañado" in r.content.decode()
    assert Trabajo.objects.count() == 0


def test_extension_no_permitida(client, db):
    r = subir(client, "virus.exe", b"MZ")
    assert r.status_code == 200 and "no soportado" in r.content.decode()


def test_pdf_protegido_muestra_error(client, db):
    r = subir(client, "p.pdf", (FIX / "protegido.pdf").read_bytes())
    assert "contraseña" in r.content.decode()


def test_rango_invalido_muestra_error(client, trabajo_cuatro_paginas, perfil_glossy_4x6):
    r = estimar(client, trabajo_cuatro_paginas, perfil_glossy_4x6, paginas="9")
    assert r.status_code == 200 and "página" in r.content.decode().lower()
    assert "Imprimir —" not in r.content.decode()


def test_sin_tarifa_muestra_error(client, trabajo_cuatro_paginas, crear_perfil):
    p = crear_perfil("Raro", ancho_mm=100, alto_mm=100)
    r = estimar(client, trabajo_cuatro_paginas, p)
    assert "Agrégala en Tarifas" in r.content.decode()


def test_imprimir_envia_paginas_por_copias(client, trabajo_estimado_2_copias, controlador_falso):
    confirmar(client, trabajo_estimado_2_copias)
    impresora, devmode, paginas, nombre = controlador_falso.impresos[0]
    assert len(paginas) == 2 and nombre == f"Printable#{trabajo_estimado_2_copias.pk} una.pdf"
    assert Trabajo.objects.get().estado == "impreso"


def test_no_imprime_dos_veces(client, trabajo_estimado_2_copias, controlador_falso):
    confirmar(client, trabajo_estimado_2_copias)
    confirmar(client, trabajo_estimado_2_copias)
    assert len(controlador_falso.impresos) == 1


def test_impresora_falla_queda_error(client, trabajo_estimado_2_copias, controlador_falso):
    controlador_falso.fallar = True
    confirmar(client, trabajo_estimado_2_copias)
    t = Trabajo.objects.get(estado="error")
    assert t.estado == "error" and "desconectada" in t.mensaje_error


def test_confirmar_sin_estimar(client, trabajo_cuatro_paginas, controlador_falso):
    client.post(reverse("trabajos:confirmar", args=[trabajo_cuatro_paginas.pk]))
    assert controlador_falso.impresos == []
