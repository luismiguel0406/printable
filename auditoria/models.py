from django.db import models


class Latido(models.Model):
    """Una sola fila: cuándo dio señales de vida el vigilante y hasta dónde se leyó el registro de Windows."""

    ultimo = models.DateTimeField(null=True)
    eventos_hasta = models.DateTimeField(null=True)

    @classmethod
    def obtener(cls) -> "Latido":
        return cls.objects.get_or_create(pk=1)[0]


class PeriodoSinVigilancia(models.Model):
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    revisado = models.BooleanField(default=False)

    class Meta:
        ordering = ["-inicio"]
        verbose_name_plural = "periodos sin vigilancia"


class ImpresionFuera(models.Model):
    """Algo que Windows imprimió en una impresora real sin pasar por Printable."""

    id_registro = models.BigIntegerField(unique=True)
    fecha = models.DateTimeField()
    impresora = models.CharField(max_length=200)
    documento = models.CharField(max_length=500)
    usuario = models.CharField(max_length=200, blank=True)
    paginas = models.PositiveIntegerField(default=0)
    revisado = models.BooleanField(default=False)

    class Meta:
        ordering = ["-fecha"]
        verbose_name_plural = "impresiones fuera del sistema"
