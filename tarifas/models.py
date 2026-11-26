from decimal import Decimal

from django.db import models

CANALES = [("C", "Cian"), ("M", "Magenta"), ("Y", "Amarillo"), ("K", "Negro")]


class TipoPapel(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "tipo de papel"
        verbose_name_plural = "tipos de papel"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class CostoHoja(models.Model):
    tipo_papel = models.ForeignKey(TipoPapel, on_delete=models.CASCADE, related_name="costos")
    tamano = models.CharField("tamaño", max_length=30)
    costo = models.DecimalField("costo por hoja", max_digits=10, decimal_places=2)
    precio_minimo = models.DecimalField("precio mínimo", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "costo de hoja"
        verbose_name_plural = "costos de hoja"
        ordering = ["tipo_papel__nombre", "tamano"]
        constraints = [
            models.UniqueConstraint(fields=["tipo_papel", "tamano"], name="costo_hoja_unico")
        ]

    def __str__(self):
        return f"{self.tipo_papel} {self.tamano}"


class CostoTinta(models.Model):
    canal = models.CharField(max_length=1, choices=CANALES, unique=True)
    costo_cm2 = models.DecimalField(
        "costo por cm² al 100 %", max_digits=12, decimal_places=8
    )
    precio_botella = models.DecimalField(max_digits=10, decimal_places=2)
    rendimiento_paginas = models.PositiveIntegerField("rendimiento (páginas)")

    class Meta:
        verbose_name = "costo de tinta"
        verbose_name_plural = "costos de tinta"
        ordering = ["canal"]

    def __str__(self):
        return self.get_canal_display()


class Configuracion(models.Model):
    margen = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.50"),
        help_text="0.50 = 50 % sobre el costo",
    )
    redondeo = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("1.00"),
        help_text="El precio se redondea hacia arriba a un múltiplo de este valor",
    )
    moneda = models.CharField(max_length=10, default="RD$")

    class Meta:
        verbose_name = "configuración"
        verbose_name_plural = "configuración"

    def __str__(self):
        return "Configuración"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def obtener(cls) -> "Configuracion":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
