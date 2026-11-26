from django.urls import reverse

from trabajos.models import Trabajo


def test_historial_muestra_errores(client, db):
    Trabajo.objects.create(nombre_original="foto.jpg", estado="error", mensaje_error="Impresora desconectada")
    Trabajo.objects.create(nombre_original="doc.pdf", estado="impreso", total=50, paginas=[1], copias=2)
    html = client.get(reverse("trabajos:historial")).content.decode()
    assert "desconectada" in html and "doc.pdf" in html and "50" in html
