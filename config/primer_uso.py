"""Primer uso: si todavía no hay usuario, el sistema pide crearlo."""

from django import forms
from django.contrib.auth import login, password_validation
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

LIBRES = ("/primer-uso/", "/static/")


def hay_usuario() -> bool:
    return User.objects.filter(is_superuser=True).exists()


class PrimerUsoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._listo = False  # una vez creado el usuario no se vuelve a consultar

    def __call__(self, request):
        if not self._listo and not request.path.startswith(LIBRES):
            if hay_usuario():
                self._listo = True
            else:
                return redirect("/primer-uso/")
        return self.get_response(request)


class PrimerUsoForm(forms.Form):
    usuario = forms.CharField(max_length=150, label="Usuario")
    clave = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    clave2 = forms.CharField(label="Repite la contraseña", widget=forms.PasswordInput)

    def clean(self):
        d = super().clean()
        if d.get("clave") and d.get("clave2") and d["clave"] != d["clave2"]:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        if d.get("clave"):
            password_validation.validate_password(d["clave"], User(username=d.get("usuario", "")))
        return d


def primer_uso(request):
    if hay_usuario():
        return redirect("/")
    form = PrimerUsoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        usuario = User.objects.create_superuser(d["usuario"], "", d["clave"])
        login(request, usuario)
        return redirect("/impresoras/")
    return render(request, "primer_uso.html", {"form": form})
