from decimal import Decimal

from django.conf import settings
from django.db import models


class Consola(models.Model):
    nombre = models.CharField(max_length=80)
    imagen = models.ImageField(upload_to="consolas/", blank=True)
    precio_hora = models.DecimalField("precio por hora", max_digits=8, decimal_places=2)
    precio_media_hora = models.DecimalField("precio por media hora", max_digits=8, decimal_places=2)
    activa = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre

    def alquiler_activo(self):
        return self.alquileres.filter(estado="activo").first()


class Alquiler(models.Model):
    ESTADOS = [("activo", "En uso"), ("terminado", "Terminado"), ("cancelado", "Cancelado")]

    consola = models.ForeignKey(Consola, on_delete=models.PROTECT, related_name="alquileres")
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    minutos = models.PositiveIntegerField()
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    estado = models.CharField(max_length=10, choices=ESTADOS, default="activo")
    terminado_en = models.DateTimeField(null=True, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-inicio"]
        constraints = [
            models.UniqueConstraint(fields=["consola"], condition=models.Q(estado="activo"), name="un_alquiler_activo_por_consola")
        ]
