import pytest
from django.urls import reverse

from tarifas.models import Configuracion


def test_tema_por_defecto_es_cian(client, db):
    html = client.get("/historial/").content.decode()
    assert '<html lang="es" data-tema="cian" data-modo="oscuro">' in html


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


def test_modo_por_defecto_oscuro(client, db):
    assert 'data-modo="oscuro"' in client.get("/historial/").content.decode()


@pytest.mark.parametrize("modo", ["claro", "oscuro"])
def test_cambiar_modo(client, db, modo):
    r = client.post(reverse("tema"), {"modo": modo, "siguiente": "/copias/"})
    assert r.status_code == 302 and r.url == "/copias/"
    assert Configuracion.obtener().modo == modo
    assert f'data-modo="{modo}"' in client.get("/historial/").content.decode()


def test_modo_no_cambia_el_color(client, db):
    client.post(reverse("tema"), {"tema": "violeta"})
    client.post(reverse("tema"), {"modo": "claro"})
    c = Configuracion.obtener()
    assert (c.tema, c.modo) == ("violeta", "claro")


def test_modo_invalido(client, db):
    assert client.post(reverse("tema"), {"modo": "sepia"}).status_code == 400


def test_boton_de_modo_en_el_menu(client, db):
    html = client.get("/historial/").content.decode()
    assert 'aria-label="Cambiar a modo claro"' in html
    client.post(reverse("tema"), {"modo": "claro"})
    assert 'aria-label="Cambiar a modo oscuro"' in client.get("/historial/").content.decode()


def test_admin_sigue_el_modo(client, db, admin_user):
    client.force_login(admin_user)
    client.post(reverse("tema"), {"modo": "claro"})
    assert 'localStorage.setItem("theme", "light")' in client.get("/admin/").content.decode()
