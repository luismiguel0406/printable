from decimal import Decimal

from django.db import models

ESCALAS = [("ajustar", "Ajustar a la página"), ("real", "Tamaño real"), ("llenar", "Llenar (recortar)")]
ESTADOS = [("estimado", "Estimado"), ("impreso", "Impreso"), ("error", "Error")]


class Trabajo(models.Model):
    archivo = models.FileField(upload_to="trabajos/%Y/%m/")
    nombre_original = models.CharField(max_length=255)
    total_paginas = models.PositiveIntegerField(default=0)
    perfil = models.ForeignKey(
        "perfiles.PerfilImpresion", null=True, blank=True, on_delete=models.SET_NULL
    )
    perfil_nombre = models.CharField(max_length=80, blank=True)
    escala = models.CharField(max_length=10, choices=ESCALAS, default="ajustar")
    paginas = models.JSONField(default=list)
    copias = models.PositiveIntegerField(default=1)
    coberturas = models.JSONField(default=list)
    precio_unitario_por_pagina = models.JSONField(default=list)
    area_cm2 = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    factor_calidad = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("1.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    estado = models.CharField(max_length=10, choices=ESTADOS, default="estimado")
    mensaje_error = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"{self.nombre_original} ({self.get_estado_display()})"
