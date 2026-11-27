from django.urls import path

from . import views

app_name = "tarifas"
urlpatterns = [
    path("", views.editar, name="editar"),
    path("papeles/agregar/", views.tipo_agregar, name="tipo_agregar"),
    path("papeles/<int:pk>/quitar/", views.tipo_quitar, name="tipo_quitar"),
    path("tamanos/agregar/", views.tamano_agregar, name="tamano_agregar"),
    path("tamanos/<int:pk>/quitar/", views.tamano_quitar, name="tamano_quitar"),
    path("calibracion/", views.calibracion, name="calibracion"),
    path("calibracion/recarga/", views.recarga, name="recarga"),
    path("calibracion/<int:impresora>/<str:canal>/aplicar/", views.aplicar, name="aplicar"),
]
