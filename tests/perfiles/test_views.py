from django.urls import reverse

from perfiles.models import PerfilImpresion
from tarifas.models import TipoPapel

IMP = "EPSON L355 Series"


def test_nuevo_perfil_toma_devmode_predeterminado(client, db, controlador_falso, epson):
    glossy = TipoPapel.objects.get(nombre="Glossy")
    r = client.post(
        reverse("perfiles:nuevo"),
        {"nombre": "Foto glossy", "impresora": epson.pk, "tipo_papel": glossy.pk, "factor_calidad": "1.3",
         "uso_sugerido": "color"},
    )
    p = PerfilImpresion.objects.get(nombre="Foto glossy")
    assert bytes(p.devmode) == controlador_falso.devmode_predeterminado(IMP)
    assert r.status_code == 302 and r.url == reverse("perfiles:editar", args=[p.pk])
    assert p.impresora == epson and p.uso_sugerido == "color"


def test_uso_sugerido_repetido_muestra_error(client, crear_perfil):
    crear_perfil("Color A", uso="color")
    p = crear_perfil("Color B")
    r = client.post(reverse("perfiles:editar", args=[p.pk]),
                    {"nombre": "Color B", "tipo_papel": p.tipo_papel_id, "factor_calidad": "1", "uso_sugerido": "color"})
    assert r.status_code == 200 and "ya es el perfil para color" in r.content.decode()


def test_preferencias_guarda_cambios(client, perfil, controlador_falso):
    client.post(reverse("perfiles:preferencias", args=[perfil.pk]))
    perfil.refresh_from_db()
    assert perfil.calidad == 600


def test_preferencias_cancelado_no_cambia(client, perfil, controlador_falso):
    controlador_falso.cancelar = True
    antes = bytes(perfil.devmode)
    client.post(reverse("perfiles:preferencias", args=[perfil.pk]))
    perfil.refresh_from_db()
    assert bytes(perfil.devmode) == antes


def test_lista_muestra_revisar(client, perfil):
    PerfilImpresion.objects.filter(pk=perfil.pk).update(version_driver="viejo")
    html = client.get(reverse("perfiles:lista")).content.decode()
    assert "Documento" in html and "Revisar" in html


def test_editar_avisa_personalizado(client, crear_perfil):
    p = crear_perfil("Raro", ancho_mm=100, alto_mm=100)
    html = client.get(reverse("perfiles:editar", args=[p.pk])).content.decode()
    assert "Agrega este tamaño en Tarifas" in html


def test_eliminar_y_duplicar(client, perfil):
    client.post(reverse("perfiles:duplicar", args=[perfil.pk]))
    assert PerfilImpresion.objects.filter(nombre="Copia de Documento").exists()
    client.post(reverse("perfiles:eliminar", args=[perfil.pk]))
    assert not PerfilImpresion.objects.filter(pk=perfil.pk).exists()


def test_predeterminado_por_vista(client, perfil):
    client.post(reverse("perfiles:predeterminado", args=[perfil.pk]))
    perfil.refresh_from_db()
    assert perfil.predeterminado
