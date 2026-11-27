from django.urls import path

from . import views

app_name = "consolas"
urlpatterns = [
    path("", views.lista, name="lista"),
    path("tarjetas/", views.tarjetas, name="tarjetas"),
    path("<int:pk>/iniciar/", views.iniciar, name="iniciar"),
    path("alquiler/<int:pk>/extender/", views.extender, name="extender"),
    path("alquiler/<int:pk>/terminar/", views.terminar, name="terminar"),
    path("alquiler/<int:pk>/cancelar/", views.cancelar, name="cancelar"),
    path("administrar/", views.administrar, name="administrar"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/activa/", views.activa, name="activa"),
]
