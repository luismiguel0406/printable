from django.urls import path

from . import views

app_name = "papeleria"
urlpatterns = [
    path("", views.vender, name="vender"),
    path("ventas/<int:pk>/anular/", views.anular, name="anular"),
    path("articulos/", views.articulos, name="articulos"),
    path("articulos/<int:pk>/", views.articulo_editar, name="articulo_editar"),
    path("articulos/<int:pk>/activo/", views.articulo_activo, name="articulo_activo"),
]
