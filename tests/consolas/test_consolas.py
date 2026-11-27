from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from consolas.models import Alquiler, Consola
from consolas.servicios import precio_por_minutos


@pytest.fixture(autouse=True)
def media_temporal(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def ps(db):
    return Consola.objects.create(nombre="PlayStation 1", precio_hora=Decimal("100"), precio_media_hora=Decimal("60"))


def iniciar(cliente, consola, minutos):
    return cliente.post(reverse("consolas:iniciar", args=[consola.pk]), {"minutos": minutos})


@pytest.mark.parametrize("minutos,esperado", [(30, "60"), (60, "100"), (90, "160"), (120, "200"), (150, "260")])
def test_precio(ps, minutos, esperado):
    assert precio_por_minutos(ps, minutos) == Decimal(esperado)


def test_iniciar_cobra_y_cuenta(cliente_empleado, ps):
    antes = timezone.now()
    r = iniciar(cliente_empleado, ps, 60)
    assert r.status_code == 302
    a = Alquiler.objects.get()
    assert a.estado == "activo" and a.total == Decimal("100") and a.minutos == 60
    assert timedelta(minutes=59) < a.fin - antes <= timedelta(minutes=61)


@pytest.mark.parametrize("minutos", ["0", "45", "750", "x", "-30"])
def test_minutos_invalidos(client, ps, minutos):
    iniciar(client, ps, minutos)
    assert not Alquiler.objects.exists()


def test_no_inicia_si_esta_ocupada(client, ps):
    iniciar(client, ps, 30)
    r = iniciar(client, ps, 30)
    assert Alquiler.objects.count() == 1 and r.status_code == 302


def test_extender_suma_tiempo_y_cobro(client, ps):
    iniciar(client, ps, 60)
    a = Alquiler.objects.get()
    fin = a.fin
    client.post(reverse("consolas:extender", args=[a.pk]), {"minutos": 30})
    a.refresh_from_db()
    assert a.minutos == 90 and a.total == Decimal("160") and a.fin - fin == timedelta(minutes=30)


def test_extender_un_alquiler_vencido_cuenta_desde_ahora(client, ps):
    iniciar(client, ps, 30)
    a = Alquiler.objects.get()
    Alquiler.objects.filter(pk=a.pk).update(inicio=timezone.now() - timedelta(hours=1), fin=timezone.now() - timedelta(minutes=30))
    client.post(reverse("consolas:extender", args=[a.pk]), {"minutos": 30})
    a.refresh_from_db()
    assert a.fin > timezone.now() + timedelta(minutes=29)


def test_terminar_libera(cliente_empleado, ps):
    iniciar(cliente_empleado, ps, 60)
    a = Alquiler.objects.get()
    cliente_empleado.post(reverse("consolas:terminar", args=[a.pk]))
    a.refresh_from_db()
    assert a.estado == "terminado" and a.terminado_en and a.total == Decimal("100")
    assert iniciar(cliente_empleado, ps, 30).status_code == 302 and Alquiler.objects.count() == 2


def test_cancelar_solo_dueno(client, cliente_empleado, ps):
    iniciar(client, ps, 60)
    a = Alquiler.objects.get()
    assert cliente_empleado.post(reverse("consolas:cancelar", args=[a.pk])).status_code == 403
    client.post(reverse("consolas:cancelar", args=[a.pk]))
    a.refresh_from_db()
    assert a.estado == "cancelado"


def test_pantalla_muestra_libre_y_ocupada(client, ps):
    otra = Consola.objects.create(nombre="Xbox", precio_hora=Decimal("120"), precio_media_hora=Decimal("70"))
    iniciar(client, ps, 60)
    html = client.get(reverse("consolas:lista")).content.decode()
    assert "PlayStation 1" in html and "Xbox" in html
    assert 'data-fin="' in html and "1 h · RD$ 120.00" in html and "30 min · RD$ 70.00" in html
    assert otra


def test_estado_parcial_para_resincronizar(client, ps):
    iniciar(client, ps, 30)
    r = client.get(reverse("consolas:tarjetas"))
    assert r.status_code == 200 and 'data-fin="' in r.content.decode()


def test_consola_con_imagen(client, ps, tmp_path):
    ruta = tmp_path / "ps.png"
    Image.new("RGB", (40, 30), "navy").save(ruta)
    r = client.post(reverse("consolas:editar", args=[ps.pk]), {
        "nombre": "PlayStation 1", "precio_hora": "100", "precio_media_hora": "60",
        "imagen": SimpleUploadedFile("ps.png", ruta.read_bytes(), content_type="image/png")})
    assert r.status_code == 302
    ps.refresh_from_db()
    assert ps.imagen and ps.imagen.url in client.get(reverse("consolas:lista")).content.decode()


def test_agregar_consola_y_permisos(client, cliente_empleado, db):
    datos = {"nombre": "Nintendo Switch", "precio_hora": "150", "precio_media_hora": "80"}
    assert cliente_empleado.post(reverse("consolas:administrar"), datos).status_code == 403
    assert client.post(reverse("consolas:administrar"), datos).status_code == 302
    assert Consola.objects.filter(nombre="Nintendo Switch").exists()


def test_precio_negativo(client, db):
    r = client.post(reverse("consolas:administrar"), {"nombre": "X", "precio_hora": "-1", "precio_media_hora": "5"})
    assert r.status_code == 200 and not Consola.objects.exists()


def test_consola_desactivada_no_aparece(client, ps):
    client.post(reverse("consolas:activa", args=[ps.pk]))
    assert 'data-consola="' not in client.get(reverse("consolas:lista")).content.decode()


def test_resumen_incluye_consolas(client, ps):
    from trabajos.resumen import resumen_del_dia

    iniciar(client, ps, 60)
    iniciar_cancelado = Alquiler.objects.create(consola=ps, inicio=timezone.now(), fin=timezone.now(), minutos=30,
                                                total=Decimal("60"), estado="cancelado")
    r = resumen_del_dia()
    assert r.consolas == Decimal("100") and r.total == Decimal("100") and iniciar_cancelado
    assert "Consolas" in client.get("/historial/").content.decode()


def test_menu_tiene_consolas(client, db):
    assert 'href="/consolas/"' in client.get("/historial/").content.decode()


def test_iniciar_y_extender_avisan_al_navegador(client, ps):
    r = iniciar(client, ps, 30)
    a = Alquiler.objects.get()
    assert r.url == f"/consolas/?evento=inicio&alquiler={a.pk}"
    r = client.post(reverse("consolas:extender", args=[a.pk]), {"minutos": 30})
    assert r.url == f"/consolas/?evento=extender&alquiler={a.pk}&minutos=30"


def test_tarjeta_tiene_barra_de_vida_y_datos(client, ps):
    iniciar(client, ps, 60)
    html = client.get(reverse("consolas:lista")).content.decode()
    assert 'class="vida"' in html and 'data-inicio="' in html and "GAME OVER" in html


def test_libre_muestra_press_start(client, ps):
    assert "PRESS START" in client.get(reverse("consolas:lista")).content.decode()

def test_libre_no_tiene_lineas_de_tv(client, ps):
    assert "tv-lineas" not in client.get(reverse("consolas:lista")).content.decode()
