from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.urls import include, path, re_path
from django.views.static import serve

from . import views
from .primer_uso import primer_uso

urlpatterns = [
    path("admin/", admin.site.urls),
    path("tema/", views.tema, name="tema"),
    path("primer-uso/", primer_uso, name="primer_uso"),
    path("entrar/", auth_views.LoginView.as_view(template_name="entrar.html"), name="entrar"),
    path("salir/", auth_views.LogoutView.as_view(next_page="/"), name="salir"),
    path("favicon.ico", RedirectView.as_view(url="/static/favicon.ico", permanent=True)),
    path("perfiles/", include("perfiles.urls")),
    path("tarifas/", include("tarifas.urls")),
    path("impresoras/", include("impresora.urls")),
    path("papeleria/", include("papeleria.urls")),
    path("consolas/", include("consolas.urls")),
    path("", include("trabajos.urls")),
    # App local de un solo usuario: Django sirve estáticos y archivos subidos.
    re_path(r"^static/(?P<path>.*)$", serve, {"document_root": settings.STATIC_ROOT}),
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
