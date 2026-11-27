from django.db import transaction

from impresora import obtener_controlador
from impresora.devmode import leer_campos
from impresora.papeles import reconocer

from .models import PerfilImpresion


def aplicar_devmode(perfil: PerfilImpresion, devmode: bytes) -> None:
    ctrl = obtener_controlador()
    campos = leer_campos(devmode)
    info = ctrl.info_papel(perfil.impresora, devmode)
    perfil.devmode = devmode
    perfil.version_driver = ctrl.version_driver(perfil.impresora)
    perfil.tamano = reconocer(info.ancho_mm, info.alto_mm)
    perfil.ancho_mm = info.ancho_mm
    perfil.alto_mm = info.alto_mm
    perfil.imprimible_x_mm = info.imprimible_x_mm
    perfil.imprimible_y_mm = info.imprimible_y_mm
    perfil.imprimible_ancho_mm = info.imprimible_ancho_mm
    perfil.imprimible_alto_mm = info.imprimible_alto_mm
    perfil.color = campos.color
    perfil.calidad = campos.calidad
    perfil.orientacion = campos.orientacion
    perfil.save()


def crear_perfil(nombre, impresora, tipo_papel, factor_calidad) -> PerfilImpresion:
    perfil = PerfilImpresion(
        nombre=nombre, impresora=impresora, tipo_papel=tipo_papel, factor_calidad=factor_calidad
    )
    aplicar_devmode(perfil, obtener_controlador().devmode_predeterminado(impresora))
    return perfil


def configurar_en_driver(perfil: PerfilImpresion) -> bool:
    nuevo = obtener_controlador().abrir_preferencias(perfil.impresora, bytes(perfil.devmode))
    if nuevo is None:
        return False
    aplicar_devmode(perfil, nuevo)
    return True


def duplicar(perfil: PerfilImpresion, nombre: str) -> PerfilImpresion:
    copia = PerfilImpresion.objects.get(pk=perfil.pk)
    copia.pk = None
    copia.nombre = nombre
    copia.predeterminado = False
    copia.save()
    return copia


def nombre_libre(base: str) -> str:
    nombre, n = base, 2
    while PerfilImpresion.objects.filter(nombre=nombre).exists():
        nombre, n = f"{base} ({n})", n + 1
    return nombre


@transaction.atomic
def marcar_predeterminado(perfil: PerfilImpresion) -> None:
    PerfilImpresion.objects.exclude(pk=perfil.pk).update(predeterminado=False)
    perfil.predeterminado = True
    perfil.save(update_fields=["predeterminado"])
