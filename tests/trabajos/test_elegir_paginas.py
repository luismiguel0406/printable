from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from trabajos.models import Trabajo
from trabajos.servicios import miniaturas_paginas

FIX = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture(autouse=True)
def media_temporal(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


def subir(client, nombre):
    client.post(reverse("trabajos:imprimir"), {"archivo": SimpleUploadedFile(nombre, (FIX / nombre).read_bytes())})
    return Trabajo.objects.latest("pk")


def test_miniaturas_de_todas_las_paginas_y_cache(client, db, settings):
    t = subir(client, "cuatro.pdf")
    urls = miniaturas_paginas(t)
    assert len(urls) == 4 and all(u.startswith(settings.MEDIA_URL) for u in urls)
    archivos = sorted((Path(settings.MEDIA_ROOT) / "miniaturas" / str(t.pk)).glob("*.png"))
    assert len(archivos) == 4
    antes = archivos[0].stat().st_mtime_ns
    miniaturas_paginas(t)
    assert archivos[0].stat().st_mtime_ns == antes  # no se vuelven a generar


def test_selector_muestra_una_casilla_por_pagina(client, db):
    t = subir(client, "mixto.pdf")
    html = client.get(f"/?trabajo={t.pk}").content.decode()
    assert html.count('class="pagina-elegible"') == 2
    assert 'data-pagina="2" data-color="1"' in html and 'data-pagina="1" data-color="0"' in html
    assert "Solo color" in html and "Solo B/N" in html


def test_selector_marca_paginas_guardadas(client, db):
    t = subir(client, "cuatro.pdf")
    Trabajo.objects.filter(pk=t.pk).update(paginas=[2, 4])
    html = client.get(f"/?trabajo={t.pk}").content.decode()
    assert html.count("checked") >= 2
    assert 'value="2, 4"' in html or 'value="2,4"' in html


def test_documento_de_una_pagina_no_muestra_selector(client, db):
    t = subir(client, "una.pdf")
    assert 'class="pagina-elegible"' not in client.get(f"/?trabajo={t.pk}").content.decode()


def test_documento_muy_largo_no_genera_miniaturas(client, db, settings, monkeypatch):
    t = subir(client, "cuatro.pdf")
    monkeypatch.setattr("trabajos.views.MAX_PAGINAS_SELECTOR", 3)
    html = client.get(f"/?trabajo={t.pk}").content.decode()
    assert 'class="pagina-elegible"' not in html and "usa el campo Páginas" in html
