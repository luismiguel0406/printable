from django.urls import path

from . import copias, views

app_name = "trabajos"
urlpatterns = [
    path("", views.imprimir, name="imprimir"),
    path("trabajos/<int:pk>/estimacion/", views.estimacion, name="estimacion"),
    path("trabajos/<int:pk>/imprimir/", views.confirmar, name="confirmar"),
    path("historial/", views.historial, name="historial"),
    path("bandeja/", views.bandeja, name="bandeja"),
    path("copias/", copias.copias, name="copias"),
    path("copias/<int:pk>/anular/", copias.anular, name="anular_copia"),
    path("copias/contador/", copias.lectura, name="lectura"),
    path("trabajos/<int:pk>/quitar/", views.quitar, name="quitar"),
    path("bloqueos/<int:pk>/visto/", views.bloqueo_visto, name="bloqueo_visto"),
]
