"""Copias hechas en la impresora y cuadre con su contador de páginas."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from config.permisos import solo_dueno
from impresora.models import Impresora
from tarifas.models import PrecioCopia

from .models import LecturaContador, Trabajo, VentaCopia

MAX_COPIAS = 999


def precio_copia(impresora: Impresora, tipo: str) -> Decimal:
    p = PrecioCopia.objects.filter(impresora=impresora, tipo=tipo).first()
    return p.precio if p else Decimal("0")


@dataclass
class FilaCuadre:
    desde: datetime
    hasta: datetime
    contadas: int  # según el contador de la impresora
    sistema: int  # páginas impresas desde el sistema
    copias: int  # copias registradas
    sin_registrar: int


def paginas_del_sistema(impresora, desde, hasta) -> int:
    trabajos = Trabajo.objects.filter(
        impresora=impresora, estado="impreso", enviado_en__gt=desde, enviado_en__lte=hasta
    ).only("paginas", "copias")
    return sum(len(t.paginas) * t.copias for t in trabajos)


def copias_registradas(impresora, desde, hasta) -> int:
    return VentaCopia.objects.filter(
        impresora=impresora, anulada=False, fecha__gt=desde, fecha__lte=hasta
    ).aggregate(n=Sum("cantidad"))["n"] or 0


def cuadre(impresora: Impresora, limite: int = 30) -> list[FilaCuadre]:
    lecturas = list(LecturaContador.objects.filter(impresora=impresora).order_by("fecha"))[-(limite + 1):]
    filas = []
    for anterior, actual in zip(lecturas, lecturas[1:]):
        contadas = actual.total_paginas - anterior.total_paginas
        sistema = paginas_del_sistema(impresora, anterior.fecha, actual.fecha)
        copias = copias_registradas(impresora, anterior.fecha, actual.fecha)
        filas.append(FilaCuadre(anterior.fecha, actual.fecha, contadas, sistema, copias,
                                contadas - sistema - copias))
    return list(reversed(filas))


class CopiaForm(forms.Form):
    impresora = forms.ModelChoiceField(Impresora.objects.none(), empty_label=None)
    tipo = forms.ChoiceField(choices=[("bn", "B/N"), ("color", "Color")])
    cantidad = forms.IntegerField(min_value=1, max_value=MAX_COPIAS, initial=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["impresora"].queryset = Impresora.objects.filter(activa=True, virtual=False)


class LecturaForm(forms.Form):
    impresora = forms.ModelChoiceField(Impresora.objects.none(), empty_label=None)
    total_paginas = forms.IntegerField(min_value=0, label="Total de páginas en la hoja de informe")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["impresora"].queryset = Impresora.objects.filter(activa=True, virtual=False)

    def clean(self):
        datos = super().clean()
        imp, total = datos.get("impresora"), datos.get("total_paginas")
        if imp is not None and total is not None:
            ultima = LecturaContador.objects.filter(impresora=imp).order_by("-fecha").first()
            if ultima and total < ultima.total_paginas:
                raise forms.ValidationError(
                    f"El número es menor que la última lectura ({ultima.total_paginas}). Revisa la hoja de informe."
                )
        return datos


def _impresora_elegida(request):
    pk = request.GET.get("impresora") or request.POST.get("impresora")
    qs = Impresora.objects.filter(activa=True, virtual=False)
    return (qs.filter(pk=pk).first() if str(pk).isdigit() else None) or Impresora.predeterminada_o_primera()


def _pantalla(request, copia_form=None, lectura_form=None, status=200):
    impresora = _impresora_elegida(request)
    hoy = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    ventas = VentaCopia.objects.filter(fecha__gte=hoy).select_related("impresora")
    total_hoy = ventas.filter(anulada=False).aggregate(t=Sum("total"))["t"] or Decimal("0")
    precios = {t: precio_copia(impresora, t) for t in ("bn", "color")} if impresora else {}
    inicial = {"impresora": impresora}
    return render(request, "trabajos/copias.html", {
        "impresora": impresora,
        "impresoras": Impresora.objects.filter(activa=True, virtual=False),
        "copia_form": copia_form or CopiaForm(initial=inicial),
        "lectura_form": lectura_form or LecturaForm(initial=inicial),
        "ventas": ventas[:50],
        "total_hoy": total_hoy,
        "precios": precios,
        "precios_en_cero": bool(precios) and not any(precios.values()),
        "cuadre": cuadre(impresora) if impresora else [],
        "ultima_lectura": LecturaContador.objects.filter(impresora=impresora).first() if impresora else None,
    }, status=status)


def copias(request):
    if request.method != "POST":
        return _pantalla(request)
    form = CopiaForm(request.POST)
    if not form.is_valid():
        return _pantalla(request, copia_form=form)
    d = form.cleaned_data
    precio = precio_copia(d["impresora"], d["tipo"])
    VentaCopia.objects.create(
        impresora=d["impresora"], tipo=d["tipo"], cantidad=d["cantidad"],
        precio_unitario=precio, total=precio * d["cantidad"],
    )
    tipo = "a color" if d["tipo"] == "color" else "B/N"
    messages.info(request, f"Registradas {d['cantidad']} copias {tipo}: RD$ {precio * d['cantidad']:.2f}")
    return redirect(f"/copias/?impresora={d['impresora'].pk}")


@solo_dueno
@require_POST
def anular(request, pk):
    v = get_object_or_404(VentaCopia, pk=pk)
    v.anulada = True
    v.save(update_fields=["anulada"])
    messages.info(request, f"Se anuló la venta de {v.cantidad} copias.")
    return redirect(f"/copias/?impresora={v.impresora_id or ''}")


@require_POST
def lectura(request):
    form = LecturaForm(request.POST)
    if not form.is_valid():
        return _pantalla(request, lectura_form=form)
    d = form.cleaned_data
    LecturaContador.objects.create(impresora=d["impresora"], fecha=timezone.now(), total_paginas=d["total_paginas"])
    messages.info(request, "Lectura del contador guardada.")
    return redirect(f"/copias/?impresora={d['impresora'].pk}")
