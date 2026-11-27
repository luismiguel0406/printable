from django.urls import path

from . import views

app_name = "impresora"
urlpatterns = [
    path("", views.lista, name="lista"),
    path("buscar/", views.buscar, name="buscar"),
    path("<int:pk>/", views.guardar, name="guardar"),
    path("<int:pk>/predeterminada/", views.predeterminada, name="predeterminada"),
]
