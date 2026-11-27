from decimal import Decimal

import pytest
from django.urls import reverse

from tarifas.models import Configuracion, CostoHoja, CostoTinta, PrecioCopia


# --- Pantalla Tarifas -------------------------------------------------------
def test_menu_lleva_a_tarifas_propias(client):
    html = client.get("/historial/").content.decode()
    assert 'href="/tarifas/"' in html and 'href="/admin/tarifas/"' not in html


def test_pantalla_tarifas_muestra_todo(client, epson):
    html = client.get(reverse("tarifas:editar")).content.decode()
    for texto in ["Papel", "Tinta", "Copias", "Margen", "Glossy", "4x6", "Cian", "Negro"]:
        assert texto in html


def test_guardar_tarifas(client, epson):
    hoja = CostoHoja.objects.get(impresora=epson, tipo_papel__nombre="Glossy", tamano="4x6")
    from tarifas.forms import formularios_de

    datos = {}
    for f in formularios_de(epson):
        if hasattr(f, "management_form"):
            for campo in f.management_form:
                datos[campo.html_name] = campo.value()
            for sub in f.forms:
                for campo in sub:
                    datos[campo.html_name] = "" if campo.value() is None else str(campo.value())
        else:
            for campo in f:
                datos[campo.html_name] = "" if campo.value() is None else str(campo.value())
    prefijo = next(k for k, v in datos.items() if k.endswith("-id") and str(v) == str(hoja.pk))[: -len("-id")]
    datos[f"{prefijo}-costo"] = "12.50"
    datos[f"{prefijo}-precio_minimo"] = "30"
    datos["general-margen"] = "0.60"
    datos["copia-bn"] = "5"
    datos["copia-color"] = "15"
    r = client.post(reverse("tarifas:editar") + f"?impresora={epson.pk}", datos)
    assert r.status_code == 302, r.content.decode()[:500]
    hoja.refresh_from_db()
    assert (hoja.costo, hoja.precio_minimo) == (Decimal("12.50"), Decimal("30"))
    assert Configuracion.obtener().margen == Decimal("0.60")
    assert PrecioCopia.objects.get(impresora=epson, tipo="color").precio == Decimal("15")


def test_cambiar_botella_recalcula_costo_cm2(epson):
    from tarifas.forms import guardar_tinta

    k = CostoTinta.objects.get(impresora=epson, canal="K")
    guardar_tinta(k, precio_botella=Decimal("700"), rendimiento=4000, costo_cm2=k.costo_cm2)
    k.refresh_from_db()
    assert k.costo_cm2 == (Decimal("700") / (Decimal(4000) * Decimal("603.22") * Decimal("0.05"))).quantize(Decimal("0.00000001"))


def test_costo_cm2_calibrado_se_respeta_si_la_botella_no_cambia(epson):
    from tarifas.forms import guardar_tinta

    k = CostoTinta.objects.get(impresora=epson, canal="K")
    guardar_tinta(k, precio_botella=k.precio_botella, rendimiento=k.rendimiento_paginas, costo_cm2=Decimal("0.0123"))
    k.refresh_from_db()
    assert k.costo_cm2 == Decimal("0.0123")


def test_valores_negativos_rechazados(client, epson):
    r = client.post(reverse("tarifas:editar") + f"?impresora={epson.pk}", {"general-margen": "-1"})
    assert r.status_code == 200 and Configuracion.obtener().margen == Decimal("0.50")


# --- Solo el superusuario toca precios -------------------------------------
PROTEGIDAS_GET = ["tarifas:editar", "perfiles:nuevo"]


@pytest.mark.parametrize("nombre", PROTEGIDAS_GET)
def test_empleado_no_entra(cliente_empleado, nombre, epson):
    assert cliente_empleado.get(reverse(nombre)).status_code == 403


@pytest.mark.parametrize("nombre", PROTEGIDAS_GET)
def test_anonimo_va_a_entrar(cliente_anonimo, nombre, epson):
    r = cliente_anonimo.get(reverse(nombre))
    assert r.status_code == 302 and r.url.startswith("/entrar/")


def test_empleado_no_cambia_perfiles_ni_calibracion(cliente_empleado, perfil, epson):
    for url, datos in [
        (reverse("perfiles:editar", args=[perfil.pk]), {"nombre": "x"}),
        (reverse("perfiles:eliminar", args=[perfil.pk]), {}),
        (reverse("perfiles:preferencias", args=[perfil.pk]), {}),
        (reverse("tarifas:recarga"), {"impresora": epson.pk, "canal": "K", "precio_botella": "1"}),
        (reverse("tarifas:aplicar", args=[epson.pk, "K"]), {}),
        (reverse("impresora:guardar", args=[epson.pk]), {"alias": "x"}),
    ]:
        assert cliente_empleado.post(url, datos).status_code == 403, url


def test_empleado_si_vende_copias_e_imprime(cliente_empleado, epson):
    assert cliente_empleado.get("/copias/").status_code == 200
    assert cliente_empleado.post("/copias/", {"impresora": epson.pk, "tipo": "bn", "cantidad": 2}).status_code == 302
    assert cliente_empleado.get("/").status_code == 200


def test_empleado_no_anula_copias(cliente_empleado, epson):
    from trabajos.models import VentaCopia

    v = VentaCopia.objects.create(impresora=epson, tipo="bn", cantidad=1, precio_unitario=5, total=5)
    assert cliente_empleado.post(reverse("trabajos:anular_copia", args=[v.pk])).status_code == 403


def test_pagina_entrar_y_salir(cliente_anonimo, admin_user):
    assert "Entrar" in cliente_anonimo.get("/entrar/").content.decode()
    r = cliente_anonimo.post("/entrar/", {"username": admin_user.username, "password": "clave-de-prueba"})
    assert r.status_code == 302
    assert "Salir" in cliente_anonimo.get("/historial/").content.decode()


# --- Ícono -------------------------------------------------------------------
def test_icono_en_el_navegador(client):
    html = client.get("/historial/").content.decode()
    assert 'rel="icon"' in html and "favicon.svg" in html
    r = client.get("/favicon.ico")
    assert r.status_code in (200, 301, 302)


def test_empleado_no_ve_botones_de_dueno(cliente_empleado, perfil, epson):
    from trabajos.models import VentaCopia

    VentaCopia.objects.create(impresora=epson, tipo="bn", cantidad=1, precio_unitario=5, total=5)
    assert "Nuevo perfil" not in cliente_empleado.get("/perfiles/").content.decode()
    assert ">Anular<" not in cliente_empleado.get("/copias/").content.decode()
    assert "Registrar recarga" not in cliente_empleado.get("/tarifas/calibracion/").content.decode()
    html = cliente_empleado.get("/impresoras/").content.decode()
    assert ">Guardar<" not in html and "solo para el dueño" in html
