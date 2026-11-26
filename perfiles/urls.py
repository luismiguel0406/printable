from django.urls import path

from . import views

app_name = "perfiles"
urlpatterns = [
    path("", views.lista, name="lista"),
    path("nuevo/", views.nuevo, name="nuevo"),
    path("<int:pk>/", views.editar, name="editar"),
    path("<int:pk>/preferencias/", views.preferencias, name="preferencias"),
    path("<int:pk>/duplicar/", views.duplicar, name="duplicar"),
    path("<int:pk>/eliminar/", views.eliminar, name="eliminar"),
    path("<int:pk>/predeterminado/", views.predeterminado, name="predeterminado"),
]
