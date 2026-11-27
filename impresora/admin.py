from django.contrib import admin

from .models import Impresora


@admin.register(Impresora)
class ImpresoraAdmin(admin.ModelAdmin):
    list_display = ["nombre_windows", "alias", "activa", "controlada", "virtual", "predeterminada"]
