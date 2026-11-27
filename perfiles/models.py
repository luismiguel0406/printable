from decimal import Decimal

from django.db import models

from impresora.base import InfoPapel

CALIDADES = {-1: "Borrador", -2: "Baja", -3: "Media", -4: "Alta"}


class PerfilImpresion(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    impresora = models.ForeignKey(
        "impresora.Impresora", on_delete=models.PROTECT, related_name="perfiles"
    )
    uso_sugerido = models.CharField(
        "uso sugerido", max_length=5, blank=True, default="",
        choices=[("", "—"), ("color", "Para color"), ("bn", "Para B/N")],
        help_text="El sistema lo sugiere según el documento tenga color o no",
    )
    devmode = models.BinaryField()
    version_driver = models.CharField(max_length=200, blank=True)
    tamano = models.CharField("tamaño", max_length=30)
    ancho_mm = models.FloatField()
    alto_mm = models.FloatField()
    imprimible_x_mm = models.FloatField()
    imprimible_y_mm = models.FloatField()
    imprimible_ancho_mm = models.FloatField()
    imprimible_alto_mm = models.FloatField()
    color = models.BooleanField(default=True)
    calidad = models.IntegerField(default=0)
    orientacion = models.IntegerField(default=1)
    tipo_papel = models.ForeignKey("tarifas.TipoPapel", on_delete=models.PROTECT)
    factor_calidad = models.DecimalField(
        "factor de tinta", max_digits=4, decimal_places=2, default=Decimal("1.00"),
        help_text="Multiplicador de tinta: 1.00 normal, 1.30 foto alta calidad",
    )
    predeterminado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "perfil de impresión"
        verbose_name_plural = "perfiles de impresión"
        ordering = ["-predeterminado", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["impresora", "uso_sugerido"], condition=~models.Q(uso_sugerido=""),
                name="un_uso_sugerido_por_impresora",
            )
        ]

    def __str__(self):
        return self.nombre

    def info_papel(self) -> InfoPapel:
        return InfoPapel(
            self.ancho_mm, self.alto_mm, self.imprimible_x_mm, self.imprimible_y_mm,
            self.imprimible_ancho_mm, self.imprimible_alto_mm,
        )

    def area_cm2(self) -> Decimal:
        return (Decimal(str(self.ancho_mm)) * Decimal(str(self.alto_mm)) / 100).quantize(
            Decimal("0.01")
        )

    def calidad_texto(self) -> str:
        if self.calidad > 0:
            return f"{self.calidad} ppp"
        return CALIDADES.get(self.calidad, "Según el driver")

    def requiere_revision(self) -> bool:
        from impresora import obtener_controlador
        from impresora.base import ErrorImpresora

        try:
            return (
                obtener_controlador().version_driver(self.impresora.nombre_windows)
                != self.version_driver
            )
        except ErrorImpresora:
            return True
