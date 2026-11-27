from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from papeleria.models import Articulo, LineaVenta, Venta


@pytest.fixture
def cuaderno(db):
    return Articulo.objects.create(nombre="Cuaderno 100 hojas", precio=Decimal("85"))


@pytest.fixture
def lapiz(db):
    return Articulo.objects.create(nombre="Lápiz", precio=Decimal("10"))


def cobrar(cliente, **lineas):
    return cliente.post(reverse("papeleria:vender"), {f"articulo_{k}": v for k, v in lineas.items()})


# --- Catálogo ---------------------------------------------------------------
def test_dueno_agrega_articulo(client, db):
    r = client.post(reverse("papeleria:articulos"), {"nombre": "Folder", "precio": "15"})
    assert r.status_code == 302 and Articulo.objects.get(nombre="Folder").precio == Decimal("15")


@pytest.mark.parametrize("nombre,precio,mensaje", [("", "5", "obligatorio"), ("Lápiz", "5", "ya existe"), ("Regla", "-1", "mayor o igual")])
def test_articulo_invalido(client, lapiz, nombre, precio, mensaje):
    r = client.post(reverse("papeleria:articulos"), {"nombre": nombre, "precio": precio})
    assert r.status_code == 200 and mensaje in r.content.decode()


def test_editar_y_desactivar(client, lapiz):
    client.post(reverse("papeleria:articulo_editar", args=[lapiz.pk]), {"nombre": "Lápiz HB", "precio": "12"})
    client.post(reverse("papeleria:articulo_activo", args=[lapiz.pk]))
    lapiz.refresh_from_db()
    assert (lapiz.nombre, lapiz.precio, lapiz.activo) == ("Lápiz HB", Decimal("12"), False)
    assert 'data-nombre="Lápiz HB"' not in client.get(reverse("papeleria:vender")).content.decode()


def test_empleado_no_cambia_catalogo(cliente_empleado, lapiz):
    assert cliente_empleado.get(reverse("papeleria:articulos")).status_code == 403
    assert cliente_empleado.post(reverse("papeleria:articulo_editar", args=[lapiz.pk]), {"nombre": "x", "precio": "0"}).status_code == 403


# --- Vender -----------------------------------------------------------------
def test_vender_varios_articulos(cliente_empleado, cuaderno, lapiz):
    r = cobrar(cliente_empleado, **{str(cuaderno.pk): 1, str(lapiz.pk): 3})
    assert r.status_code == 302
    v = Venta.objects.get()
    assert v.total == Decimal("115") and v.lineas.count() == 2
    l = v.lineas.get(articulo=lapiz)
    assert (l.nombre, l.precio_unitario, l.cantidad, l.subtotal) == ("Lápiz", Decimal("10"), 3, Decimal("30"))


def test_precio_viejo_no_cambia(client, lapiz):
    cobrar(client, **{str(lapiz.pk): 2})
    lapiz.precio = Decimal("50")
    lapiz.save()
    assert Venta.objects.get().total == Decimal("20")


@pytest.mark.parametrize("cantidad", ["0", "-1", "1000", "dos"])
def test_cantidad_invalida(client, lapiz, cantidad):
    r = cobrar(client, **{str(lapiz.pk): cantidad})
    assert r.status_code == 200 and not Venta.objects.exists()


def test_venta_vacia(client, db):
    r = client.post(reverse("papeleria:vender"), {})
    assert r.status_code == 200 and "Agrega al menos un artículo" in r.content.decode()


def test_articulo_inactivo_o_inexistente(client, lapiz):
    lapiz.activo = False
    lapiz.save()
    assert cobrar(client, **{str(lapiz.pk): 1}).status_code == 200
    assert cobrar(client, **{"99999": 1}).status_code == 200
    assert not Venta.objects.exists()


def test_pantalla_muestra_ventas_y_total_de_hoy(client, cuaderno, lapiz):
    cobrar(client, **{str(cuaderno.pk): 2})
    html = client.get(reverse("papeleria:vender")).content.decode()
    assert "Cuaderno 100 hojas" in html and "RD$ 170.00" in html and 'data-precio="85' in html


def test_anular_solo_dueno(client, cliente_empleado, lapiz):
    cobrar(client, **{str(lapiz.pk): 1})
    v = Venta.objects.get()
    assert cliente_empleado.post(reverse("papeleria:anular", args=[v.pk])).status_code == 403
    client.post(reverse("papeleria:anular", args=[v.pk]))
    v.refresh_from_db()
    assert v.anulada


def test_menu_tiene_papeleria(client, db):
    assert 'href="/papeleria/"' in client.get("/historial/").content.decode()


# --- Resumen del día --------------------------------------------------------
def test_resumen_del_dia(db, epson, lapiz):
    from trabajos.models import Trabajo, VentaCopia
    from trabajos.resumen import resumen_del_dia

    ahora = timezone.now()
    Trabajo.objects.create(nombre_original="a", estado="impreso", total=Decimal("40"), enviado_en=ahora)
    Trabajo.objects.create(nombre_original="b", estado="impreso", total=Decimal("99"), enviado_en=ahora - timedelta(days=2))
    Trabajo.objects.create(nombre_original="c", estado="estimado", total=Decimal("77"))
    VentaCopia.objects.create(impresora=epson, tipo="bn", cantidad=2, precio_unitario=5, total=10)
    VentaCopia.objects.create(impresora=epson, tipo="bn", cantidad=2, precio_unitario=5, total=10, anulada=True)
    v = Venta.objects.create(total=Decimal("25"))
    Venta.objects.create(total=Decimal("100"), anulada=True)
    vieja = Venta.objects.create(total=Decimal("300"))
    Venta.objects.filter(pk=vieja.pk).update(fecha=ahora - timedelta(days=1, hours=1))
    r = resumen_del_dia()
    assert (r.impresiones, r.copias, r.papeleria, r.total) == (Decimal("40"), Decimal("10"), Decimal("25"), Decimal("75"))
    assert v


def test_resumen_en_historial_y_papeleria(client, db):
    for url in ["/historial/", "/papeleria/"]:
        assert "Hoy en caja" in client.get(url).content.decode()
