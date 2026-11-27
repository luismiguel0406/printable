from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("tema/", views.tema, name="tema"),
    path("perfiles/", include("perfiles.urls")),
    path("tarifas/", include("tarifas.urls")),
    path("impresoras/", include("impresora.urls")),
    path("", include("trabajos.urls")),
    # App local de un solo usuario: Django sirve estáticos y archivos subidos.
    re_path(r"^static/(?P<path>.*)$", serve, {"document_root": settings.STATIC_ROOT}),
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
