from django.urls import path

from . import views

app_name = "trabajos"
urlpatterns = [
    path("", views.imprimir, name="imprimir"),
    path("trabajos/<int:pk>/estimacion/", views.estimacion, name="estimacion"),
    path("trabajos/<int:pk>/imprimir/", views.confirmar, name="confirmar"),
    path("historial/", views.historial, name="historial"),
]
