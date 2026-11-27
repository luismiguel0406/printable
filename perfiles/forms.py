from django import forms

from impresora.models import Impresora

from .models import PerfilImpresion

USOS = {"color": "para color", "bn": "para B/N"}


class EditarPerfilForm(forms.ModelForm):
    class Meta:
        model = PerfilImpresion
        fields = ["nombre", "tipo_papel", "factor_calidad", "uso_sugerido"]

    def _impresora(self):
        return self.instance.impresora if self.instance.pk else self.cleaned_data.get("impresora")

    def clean_uso_sugerido(self):
        uso = self.cleaned_data["uso_sugerido"]
        impresora = self._impresora()
        if uso and impresora:
            otros = PerfilImpresion.objects.filter(impresora=impresora, uso_sugerido=uso)
            if self.instance.pk:
                otros = otros.exclude(pk=self.instance.pk)
            if otros.exists():
                raise forms.ValidationError(
                    f"«{otros.first()}» ya es el perfil {USOS[uso]} de esta impresora."
                )
        return uso


class NuevoPerfilForm(EditarPerfilForm):
    impresora = forms.ModelChoiceField(Impresora.objects.none(), label="Impresora", empty_label=None)
    field_order = ["nombre", "impresora", "tipo_papel", "factor_calidad", "uso_sugerido"]

    class Meta(EditarPerfilForm.Meta):
        fields = ["nombre", "tipo_papel", "factor_calidad", "uso_sugerido"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["impresora"].queryset = Impresora.disponibles()
        self.fields["impresora"].initial = Impresora.predeterminada_o_primera()
