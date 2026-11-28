from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from auditoria.models import ImpresionFuera, PeriodoSinVigilancia

pytestmark = pytest.mark.django_db
BANNER = "Hubo impresiones fuera del sistema"


def fuera(n=1, paginas=3, fecha=None):
    return ImpresionFuera.objects.create(id_registro=n, fecha=fecha or timezone.now(), impresora="EPSON L355 Series",
                                         documento=f"doc{n}.docx", usuario="Caja", paginas=paginas)


def test_banner_aparece_con_pendientes(client):
    PeriodoSinVigilancia.objects.create(inicio=timezone.now() - timedelta(hours=1), fin=timezone.now())
    assert BANNER in client.get(reverse("consolas:lista")).content.decode()


def test_banner_no_aparece_sin_pendientes(client):
    fuera().__class__.objects.update(revisado=True)
    assert BANNER not in client.get(reverse("consolas:lista")).content.decode()


def test_historial_lista_impresiones_fuera_y_paginas_de_hoy(client):
    fuera(1, 3); fuera(2, 4); fuera(3, 10, fecha=timezone.now() - timedelta(days=2))
    html = client.get(reverse("trabajos:historial")).content.decode()
    assert 'id="fuera"' in html and "doc1.docx" in html and "doc3.docx" in html
    assert "7 páginas hoy" in html


def test_empleado_no_puede_revisar(cliente_empleado):
    fuera()
    r = cliente_empleado.post(reverse("auditoria:revisar"))
    assert r.status_code == 403
    assert ImpresionFuera.objects.filter(revisado=False).count() == 1
    assert "Marcar como revisado" not in cliente_empleado.get(reverse("trabajos:historial")).content.decode()


def test_dueno_revisa_y_banner_desaparece(client):
    fuera()
    PeriodoSinVigilancia.objects.create(inicio=timezone.now() - timedelta(hours=1), fin=timezone.now())
    assert "Marcar como revisado" in client.get(reverse("trabajos:historial")).content.decode()
    r = client.post(reverse("auditoria:revisar"))
    assert r.status_code == 302
    assert BANNER not in client.get(reverse("consolas:lista")).content.decode()
