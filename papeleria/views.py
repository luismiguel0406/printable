from decimal import Decimal

from django import forms
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from config.permisos import solo_dueno
from trabajos.resumen import inicio_de_hoy, resumen_del_dia

from .models import Articulo, LineaVenta, Venta

MAX_CANTIDAD = 999


class ArticuloForm(forms.ModelForm):
    precio = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2, label="Precio (RD$)")

    class Meta:
        model = Articulo
        fields = ["nombre", "precio"]

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        repetido = Articulo.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk)
        if repetido.exists():
            raise forms.ValidationError(f"El artículo «{nombre}» ya existe.")
        return nombre


def _lineas_del_post(post) -> tuple[list[tuple[Articulo, int]], str | None]:
    pedidas = {}
    for clave, valor in post.items():
        if not clave.startswith("articulo_"):
            continue
        try:
            pk, cantidad = int(clave.removeprefix("articulo_")), int(valor)
        except ValueError:
            return [], "Revisa las cantidades: deben ser números enteros."
        if not 1 <= cantidad <= MAX_CANTIDAD:
            return [], f"Cada cantidad debe estar entre 1 y {MAX_CANTIDAD}."
        pedidas[pk] = cantidad
    if not pedidas:
        return [], "Agrega al menos un artículo a la venta."
    articulos = {a.pk: a for a in Articulo.objects.filter(pk__in=pedidas, activo=True)}
    if len(articulos) != len(pedidas):
        return [], "Algún artículo ya no está disponible. Recarga la página."
    return [(articulos[pk], cant) for pk, cant in pedidas.items()], None


def _pantalla(request, error=None, status=200):
    hoy = inicio_de_hoy()
    ventas = Venta.objects.filter(fecha__gte=hoy).prefetch_related("lineas")
    total_hoy = sum((v.total for v in ventas if not v.anulada), Decimal("0"))
    return render(request, "papeleria/vender.html", {
        "articulos": Articulo.objects.filter(activo=True),
        "ventas": ventas[:100],
        "total_hoy": total_hoy,
        "error": error,
        "resumen": resumen_del_dia(),
    }, status=status)


def vender(request):
    if request.method != "POST":
        return _pantalla(request)
    lineas, error = _lineas_del_post(request.POST)
    if error:
        return _pantalla(request, error)
    with transaction.atomic():
        venta = Venta.objects.create(usuario=request.user if request.user.is_authenticated else None)
        total = Decimal("0")
        for articulo, cantidad in lineas:
            subtotal = articulo.precio * cantidad
            LineaVenta.objects.create(venta=venta, articulo=articulo, nombre=articulo.nombre,
                                      precio_unitario=articulo.precio, cantidad=cantidad, subtotal=subtotal)
            total += subtotal
        venta.total = total
        venta.save(update_fields=["total"])
    messages.info(request, f"Venta cobrada: RD$ {total:,.2f}")
    return redirect("papeleria:vender")


@solo_dueno
@require_POST
def anular(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    venta.anulada = True
    venta.save(update_fields=["anulada"])
    messages.info(request, f"Venta de RD$ {venta.total:,.2f} anulada.")
    return redirect("papeleria:vender")


@solo_dueno
def articulos(request):
    form = ArticuloForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.info(request, f"Artículo «{form.instance}» agregado.")
        return redirect("papeleria:articulos")
    return render(request, "papeleria/articulos.html", {"form": form, "articulos": Articulo.objects.all()})


@solo_dueno
@require_POST
def articulo_editar(request, pk):
    articulo = get_object_or_404(Articulo, pk=pk)
    form = ArticuloForm(request.POST, instance=articulo)
    if form.is_valid():
        form.save()
        messages.info(request, f"Artículo «{articulo}» guardado.")
    else:
        messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
    return redirect("papeleria:articulos")


@solo_dueno
@require_POST
def articulo_activo(request, pk):
    articulo = get_object_or_404(Articulo, pk=pk)
    articulo.activo = not articulo.activo
    articulo.save(update_fields=["activo"])
    return redirect("papeleria:articulos")
