import pytest
from django.contrib.auth.models import User

pytestmark = pytest.mark.sin_usuario


def test_sin_usuario_redirige_a_primer_uso(client, db):
    r = client.get("/historial/")
    assert r.status_code == 302 and r.url == "/primer-uso/"


def test_estaticos_no_redirigen(client, db):
    assert client.get("/static/js/htmx.min.js").status_code != 302


def test_crear_usuario(client, db):
    r = client.post("/primer-uso/", {"usuario": "luis", "clave": "Tinta-2026-L355", "clave2": "Tinta-2026-L355"})
    assert r.status_code == 302 and r.url == "/impresoras/"
    u = User.objects.get(username="luis")
    assert u.is_superuser and u.is_staff
    assert client.get("/historial/").status_code == 200  # ya con sesión y sin redirección


@pytest.mark.parametrize("c1,c2,mensaje", [("Tinta-2026-L355", "otra-cosa-9", "no coinciden"), ("123", "123", "contraseña")])
def test_claves_invalidas(client, db, c1, c2, mensaje):
    r = client.post("/primer-uso/", {"usuario": "luis", "clave": c1, "clave2": c2})
    assert r.status_code == 200 and mensaje in r.content.decode()
    assert not User.objects.exists()


def test_con_usuario_primer_uso_redirige_al_inicio(client, db):
    User.objects.create_superuser("ya", "", "x")
    r = client.get("/primer-uso/")
    assert r.status_code == 302 and r.url == "/"
