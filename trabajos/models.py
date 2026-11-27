from decimal import Decimal

from django.db import models

ESCALAS = [("ajustar", "Ajustar a la página"), ("real", "Tamaño real"), ("llenar", "Llenar (recortar)")]
ESTADOS = [
    ("estimado", "Pendiente"), ("impreso", "Impreso"), ("error", "Error"), ("descartado", "Descartado"),
]


class Trabajo(models.Model):
    archivo = models.FileField(upload_to="trabajos/%Y/%m/")
    nombre_original = models.CharField(max_length=255)
    ruta_normalizada = models.CharField(max_length=500, blank=True)
    tipo_documento = models.CharField(max_length=10, blank=True)  # "pdf" o "imagen"
    total_paginas = models.PositiveIntegerField(default=0)
    perfil = models.ForeignKey(
        "perfiles.PerfilImpresion", null=True, blank=True, on_delete=models.SET_NULL
    )
    perfil_nombre = models.CharField(max_length=80, blank=True)
    impresora = models.ForeignKey(
        "impresora.Impresora", null=True, blank=True, on_delete=models.SET_NULL
    )
    origen = models.CharField(
        max_length=10, choices=[("subido", "Subido"), ("capturado", "Ctrl+P")], default="subido"
    )
    paginas_color = models.JSONField(default=list, blank=True)
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
    enviado_en = models.DateTimeField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"{self.nombre_original} ({self.get_estado_display()})"

    def huella(self) -> str:
        """Identifica lo que se le mostró al usuario: si algo cambió, no se imprime."""
        import hashlib

        actualizado = self.perfil.actualizado.isoformat() if self.perfil else ""
        datos = f"{self.total}|{self.paginas}|{self.copias}|{self.escala}|{self.perfil_id}|{actualizado}"
        return hashlib.sha256(datos.encode()).hexdigest()[:16]


class Bloqueo(models.Model):
    """Trabajo enviado directo a una impresora, cancelado por el sistema."""

    impresora = models.ForeignKey(
        "impresora.Impresora", null=True, blank=True, on_delete=models.SET_NULL
    )
    impresora_nombre = models.CharField(max_length=200)
    documento = models.CharField(max_length=500)
    usuario = models.CharField(max_length=200, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    visto = models.BooleanField(default=False)
    tipo = models.CharField(
        max_length=10, default="bloqueo",
        choices=[("bloqueo", "Impresión directa bloqueada"), ("rechazado", "PDF de Ctrl+P ilegible")],
    )

    class Meta:
        ordering = ["-fecha"]
