from django.urls import path

from . import views

app_name = "tarifas"
urlpatterns = [
    path("calibracion/", views.calibracion, name="calibracion"),
    path("calibracion/recarga/", views.recarga, name="recarga"),
    path("calibracion/<int:impresora>/<str:canal>/aplicar/", views.aplicar, name="aplicar"),
]
