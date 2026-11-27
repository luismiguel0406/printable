import pytest
from django.urls import reverse

from tarifas.models import Configuracion


def test_tema_por_defecto_es_cian(client, db):
    html = client.get("/historial/").content.decode()
    assert '<html lang="es" data-tema="cian">' in html


@pytest.mark.parametrize("tema", ["cian", "azul", "violeta", "menta"])
def test_cambiar_tema(client, db, tema):
    r = client.post(reverse("tema"), {"tema": tema, "siguiente": "/perfiles/"})
    assert r.status_code == 302 and r.url == "/perfiles/"
    assert Configuracion.obtener().tema == tema
    assert f'data-tema="{tema}"' in client.get("/historial/").content.decode()


def test_tema_invalido(client, db):
    r = client.post(reverse("tema"), {"tema": "rojo"})
    assert r.status_code == 400 and Configuracion.obtener().tema == "cian"


def test_siguiente_externo_no_se_sigue(client, db):
    r = client.post(reverse("tema"), {"tema": "azul", "siguiente": "https://otro.sitio/"})
    assert r.url == "/"


def test_selector_en_el_menu(client, db):
    html = client.get("/historial/").content.decode()
    for nombre in ["Cian", "Azul", "Violeta", "Menta"]:
        assert f'aria-label="Tema {nombre}"' in html
