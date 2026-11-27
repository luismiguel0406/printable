"""Solo el dueño (superusuario) puede cambiar precios, perfiles e impresoras."""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.shortcuts import render


def solo_dueno(vista):
    @wraps(vista)
    def envuelta(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), "/entrar/")
        if not request.user.is_superuser:
            return render(request, "sin_permiso.html", status=403)
        return vista(request, *args, **kwargs)

    return envuelta
