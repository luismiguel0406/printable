from django.contrib import admin

from .models import Configuracion, CostoHoja, CostoTinta, TipoPapel


class CostoHojaInline(admin.TabularInline):
    model = CostoHoja
    extra = 0


@admin.register(TipoPapel)
class TipoPapelAdmin(admin.ModelAdmin):
    inlines = [CostoHojaInline]


@admin.register(CostoHoja)
class CostoHojaAdmin(admin.ModelAdmin):
    list_display = ["impresora", "tipo_papel", "tamano", "costo", "precio_minimo"]
    list_editable = ["costo", "precio_minimo"]
    list_filter = ["impresora", "tipo_papel"]


@admin.register(CostoTinta)
class CostoTintaAdmin(admin.ModelAdmin):
    list_display = ["impresora", "canal", "costo_cm2", "precio_botella", "rendimiento_paginas"]
    list_filter = ["impresora"]


@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):
    list_display = ["margen", "redondeo", "moneda"]

    def has_add_permission(self, request):
        return not Configuracion.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


from .models import PrecioCopia, RecargaTinta  # noqa: E402


@admin.register(PrecioCopia)
class PrecioCopiaAdmin(admin.ModelAdmin):
    list_display = ["impresora", "tipo", "precio"]
    list_editable = ["precio"]


@admin.register(RecargaTinta)
class RecargaTintaAdmin(admin.ModelAdmin):
    list_display = ["impresora", "canal", "fecha", "precio_botella"]
    list_filter = ["impresora", "canal"]
