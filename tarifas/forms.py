"""Formularios de la pantalla Tarifas (por impresora)."""

from decimal import Decimal

from django import forms
from django.forms import modelformset_factory

from .models import Configuracion, CostoHoja, CostoTinta, PrecioCopia

AREA_CARTA_CM2 = Decimal("603.22")
COBERTURA_REFERENCIA = Decimal("0.05")
CERO = Decimal("0")


def costo_por_cm2(precio_botella: Decimal, rendimiento: int) -> Decimal:
    if not rendimiento:
        return CERO
    return (precio_botella / (Decimal(rendimiento) * AREA_CARTA_CM2 * COBERTURA_REFERENCIA)).quantize(
        Decimal("0.00000001")
    )


def guardar_tinta(tinta: CostoTinta, precio_botella: Decimal, rendimiento: int, costo_cm2: Decimal) -> None:
    """Si cambió la botella o su rendimiento, se recalcula el costo por cm²; si no,
    se respeta el valor escrito (por ejemplo, el que dejó la calibración)."""
    if precio_botella != tinta.precio_botella or rendimiento != tinta.rendimiento_paginas:
        costo_cm2 = costo_por_cm2(precio_botella, rendimiento)
    tinta.precio_botella, tinta.rendimiento_paginas, tinta.costo_cm2 = precio_botella, rendimiento, costo_cm2
    tinta.save()


class HojaForm(forms.ModelForm):
    costo = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2)
    precio_minimo = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2)

    class Meta:
        model = CostoHoja
        fields = ["costo", "precio_minimo"]


class TintaForm(forms.ModelForm):
    precio_botella = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2)
    rendimiento_paginas = forms.IntegerField(min_value=0)
    costo_cm2 = forms.DecimalField(min_value=0, max_digits=12, decimal_places=8)

    class Meta:
        model = CostoTinta
        fields = ["precio_botella", "rendimiento_paginas", "costo_cm2"]


HojasFormSet = modelformset_factory(CostoHoja, form=HojaForm, extra=0)
TintasFormSet = modelformset_factory(CostoTinta, form=TintaForm, extra=0)


class CopiasForm(forms.Form):
    bn = forms.DecimalField(min_value=0, max_digits=8, decimal_places=2, label="Copia B/N")
    color = forms.DecimalField(min_value=0, max_digits=8, decimal_places=2, label="Copia a color")


class GeneralForm(forms.ModelForm):
    margen = forms.DecimalField(min_value=0, max_digits=5, decimal_places=2, help_text="0.50 = 50 % sobre el costo")
    redondeo = forms.DecimalField(min_value=0, max_digits=8, decimal_places=2,
                                  help_text="El precio sube al múltiplo más cercano (1 = al peso, 5 = de 5 en 5)")

    class Meta:
        model = Configuracion
        fields = ["margen", "redondeo"]


def formularios_de(impresora, data=None):
    from .servicios import crear_tarifas_para

    crear_tarifas_para(impresora)  # por si faltara alguna fila
    precios = {p.tipo: p.precio for p in PrecioCopia.objects.filter(impresora=impresora)}
    return [
        HojasFormSet(data, prefix="hoja", queryset=CostoHoja.objects.filter(impresora=impresora)
                     .select_related("tipo_papel").order_by("tipo_papel__nombre", "tamano")),
        TintasFormSet(data, prefix="tinta", queryset=CostoTinta.objects.filter(impresora=impresora).order_by("canal")),
        CopiasForm(data, prefix="copia", initial={"bn": precios.get("bn", CERO), "color": precios.get("color", CERO)}),
        GeneralForm(data, prefix="general", instance=Configuracion.obtener()),
    ]


def guardar(impresora, formularios) -> None:
    hojas, tintas, copias, general = formularios
    hojas.save()
    for f in tintas.forms:
        original = CostoTinta.objects.get(pk=f.instance.pk)
        d = f.cleaned_data
        guardar_tinta(original, d["precio_botella"], d["rendimiento_paginas"], d["costo_cm2"])
    for tipo in ("bn", "color"):
        PrecioCopia.objects.update_or_create(impresora=impresora, tipo=tipo, defaults={"precio": copias.cleaned_data[tipo]})
    general.save()
