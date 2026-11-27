from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower


class Articulo(models.Model):
    nombre = models.CharField(max_length=120)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        constraints = [models.UniqueConstraint(Lower("nombre"), name="articulo_nombre_unico")]

    def __str__(self):
        return self.nombre


class Venta(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    anulada = models.BooleanField(default=False)

    class Meta:
        ordering = ["-fecha"]


class LineaVenta(models.Model):
    """Nombre y precio se copian al vender: cambiar el catálogo no altera ventas viejas."""

    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="lineas")
    articulo = models.ForeignKey(Articulo, null=True, on_delete=models.SET_NULL)
    nombre = models.CharField(max_length=120)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
