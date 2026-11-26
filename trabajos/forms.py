from django import forms

from perfiles.models import PerfilImpresion

from .models import ESCALAS


class SubirForm(forms.Form):
    archivo = forms.FileField(label="Archivo")


class OpcionesForm(forms.Form):
    perfil = forms.ModelChoiceField(PerfilImpresion.objects.all(), empty_label=None)
    copias = forms.IntegerField(min_value=1, max_value=99, initial=1)
    paginas = forms.CharField(required=False, label="Páginas", help_text="Vacío = todas. Ej.: 1, 3-5")
    escala = forms.ChoiceField(choices=ESCALAS, initial="ajustar")
