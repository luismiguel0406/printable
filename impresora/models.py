from django.db import models


class Impresora(models.Model):
    nombre_windows = models.CharField("nombre en Windows", max_length=200, unique=True)
    alias = models.CharField(max_length=80, blank=True)
    controlada = models.BooleanField(default=True, help_text="Bloquear lo que se imprima directo")
    virtual = models.BooleanField(default=False)
    predeterminada = models.BooleanField(default=False)
    activa = models.BooleanField(default=True, help_text="Sigue instalada en Windows")
    en_linea = models.BooleanField(default=True, help_text="Encendida y conectada según Windows")
    motivo_no_disponible = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["-predeterminada", "nombre_windows"]
        verbose_name_plural = "impresoras"

    def __str__(self):
        return self.alias or self.nombre_windows

    @classmethod
    def disponibles(cls):
        return cls.objects.filter(activa=True, en_linea=True, virtual=False)

    @classmethod
    def predeterminada_o_primera(cls) -> "Impresora | None":
        return cls.disponibles().order_by("-predeterminada", "nombre_windows").first()
