from django import forms

from impresora import obtener_controlador
from impresora.base import ErrorImpresora

from .models import PerfilImpresion


class EditarPerfilForm(forms.ModelForm):
    class Meta:
        model = PerfilImpresion
        fields = ["nombre", "tipo_papel", "factor_calidad"]


class NuevoPerfilForm(EditarPerfilForm):
    impresora = forms.ChoiceField(label="Impresora")

    class Meta(EditarPerfilForm.Meta):
        fields = ["nombre", "impresora", "tipo_papel", "factor_calidad"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            impresoras = obtener_controlador().listar_impresoras()
        except ErrorImpresora:
            impresoras = []
        self.fields["impresora"].choices = [(i, i) for i in impresoras]
        epson = [i for i in impresoras if "L355" in i]
        if epson:
            self.fields["impresora"].initial = epson[0]
