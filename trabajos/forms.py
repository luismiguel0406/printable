from django import forms

from impresora.models import Impresora
from perfiles.models import PerfilImpresion

from .models import ESCALAS


class SubirForm(forms.Form):
    archivo = forms.FileField(label="Archivo")


class OpcionesForm(forms.Form):
    impresora = forms.ModelChoiceField(Impresora.objects.none(), empty_label=None)
    perfil = forms.ModelChoiceField(PerfilImpresion.objects.all(), required=False, empty_label=None)
    perfil_manual = forms.CharField(required=False, widget=forms.HiddenInput)
    copias = forms.IntegerField(min_value=1, max_value=99, initial=1)
    paginas = forms.CharField(required=False, label="Páginas", help_text="Vacío = todas. Ej.: 1, 3-5")
    escala = forms.ChoiceField(choices=ESCALAS, initial="ajustar")

    def __init__(self, *args, impresora=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["impresora"].queryset = Impresora.disponibles()
        self.fields["impresora"].widget.attrs["onchange"] = "document.getElementById('id_perfil_manual').value='0'"
        self.fields["perfil"].widget.attrs["onchange"] = "document.getElementById('id_perfil_manual').value='1'"
        if impresora is not None:
            self.fields["perfil"].queryset = PerfilImpresion.objects.filter(impresora=impresora)
