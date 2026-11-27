"""Vigilante: recoge lo impreso con Ctrl+P y cancela lo que se mande directo a una impresora."""

import logging
import re
import shutil
import threading
import time
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import close_old_connections
from django.utils import timezone

from impresora.base import ErrorImpresora
from impresora.models import Impresora

from .conversion import ArchivoNoValido, normalizar
from .models import Bloqueo, Trabajo

log = logging.getLogger(__name__)

PREFIJO = re.compile(r"^Printable#(\d+) ")
SUFIJO_FECHA = re.compile(r"_\d{8,14}$")
ESPERA_RECHAZO = 60  # segundos
INTERVALO_COLAS = 0.5
INTERVALO_CARPETA = 1.0
INTERVALO_IMPRESORAS = 30.0
VIGENCIA_ENVIO = timezone.timedelta(hours=2)  # un trabajo del sistema puede tardar en salir


def es_del_sistema(documento: str) -> bool:
    m = PREFIJO.match(documento or "")
    return bool(m) and Trabajo.objects.filter(
        pk=int(m.group(1)), enviado_en__gte=timezone.now() - VIGENCIA_ENVIO
    ).exists()


def _nombre_trabajo(ruta: Path) -> str:
    try:
        import pymupdf

        with pymupdf.open(ruta) as doc:
            titulo = (doc.metadata or {}).get("title", "").strip()
        if titulo:
            return titulo
    except Exception:
        pass
    return SUFIJO_FECHA.sub("", ruta.stem) or ruta.stem


def _mover_sin_pisar(origen: Path, carpeta: Path) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / origen.name
    n = 2
    while destino.exists():
        destino = carpeta / f"{origen.stem} ({n}){origen.suffix}"
        n += 1
    shutil.move(str(origen), destino)
    return destino


class Vigilante:
    def __init__(self, carpeta: Path, controlador=None):
        self.carpeta = Path(carpeta)
        self.controlador = controlador
        self._vistos: dict[str, tuple[int, float]] = {}  # nombre → (tamaño, primera vez)
        self._manejados: set[tuple[str, int]] = set()
        self._hilos: list[threading.Thread] = []
        self._parar = threading.Event()

    def _ctrl(self):
        if self.controlador is None:
            from impresora import obtener_controlador

            self.controlador = obtener_controlador()
        return self.controlador

    # --- Ctrl+P → carpeta de entrada ---------------------------------------
    def revisar_carpeta(self, ahora: float) -> list[Trabajo]:
        capturados = []
        presentes = set()
        for archivo in sorted(p for p in self.carpeta.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"):
            presentes.add(archivo.name)
            try:
                tamano = archivo.stat().st_size
            except OSError:
                continue
            try:
                trabajo = self._capturar(archivo, tamano, ahora)
            except OSError as e:  # p. ej. clawPDF todavía tiene el archivo abierto
                log.info("Aún no se puede tomar %s: %s", archivo.name, e)
                continue
            if trabajo is not None:
                capturados.append(trabajo)
        for nombre in set(self._vistos) - presentes:
            del self._vistos[nombre]
        return capturados

    def _capturar(self, archivo: Path, tamano: int, ahora: float) -> Trabajo | None:
        from .servicios import crear_trabajo_desde

        anterior = self._vistos.get(archivo.name)
        primera = anterior[1] if anterior else ahora
        if anterior is None or anterior[0] != tamano or tamano == 0:
            self._vistos[archivo.name] = (tamano, primera)
            return None
        try:
            normalizar(archivo, archivo.parent)
        except ArchivoNoValido:
            if ahora - primera >= ESPERA_RECHAZO:
                _mover_sin_pisar(archivo, self.carpeta / "rechazados")
                log.warning("PDF ilegible movido a rechazados: %s", archivo.name)
                self._vistos.pop(archivo.name, None)
            return None
        nombre = _nombre_trabajo(archivo)
        hoy = date.today()
        carpeta_media = Path(settings.MEDIA_ROOT) / "trabajos" / f"{hoy:%Y}" / f"{hoy:%m}"
        nombre_disponible = Path(
            default_storage.get_available_name(f"trabajos/{hoy:%Y}/{hoy:%m}/{archivo.name}")
        ).name
        carpeta_media.mkdir(parents=True, exist_ok=True)
        destino = carpeta_media / nombre_disponible
        shutil.move(str(archivo), destino)
        self._vistos.pop(archivo.name, None)
        try:
            return crear_trabajo_desde(destino, nombre, "capturado")
        except ArchivoNoValido:
            _mover_sin_pisar(destino, self.carpeta / "rechazados")
            return None

    # --- Impresiones directas -------------------------------------------------
    def revisar_colas(self) -> list[Bloqueo]:
        bloqueos = []
        ctrl = self._ctrl()
        for imp in Impresora.objects.filter(controlada=True, activa=True, virtual=False):
            try:
                cola = ctrl.listar_trabajos(imp.nombre_windows)
            except ErrorImpresora:
                continue
            for trabajo in cola:
                if es_del_sistema(trabajo.documento):
                    continue
                clave = (imp.nombre_windows, trabajo.id)
                try:
                    ctrl.cancelar_trabajo(imp.nombre_windows, trabajo.id)
                except ErrorImpresora as e:
                    log.error("No se pudo cancelar %s en %s: %s", trabajo.documento, imp, e)
                if clave in self._manejados:
                    continue
                self._manejados.add(clave)
                bloqueos.append(Bloqueo.objects.create(
                    impresora=imp, impresora_nombre=imp.nombre_windows,
                    documento=trabajo.documento[:500], usuario=trabajo.usuario[:200],
                ))
        return bloqueos

    # --- Bucle ----------------------------------------------------------------
    def ciclo(self, ahora: float, *, colas: bool = True, carpeta: bool = True, impresoras: bool = False) -> None:
        for tarea, activa in [
            (lambda: self.revisar_colas(), colas),
            (lambda: self.revisar_carpeta(ahora), carpeta),
            (self._sincronizar, impresoras),
        ]:
            if not activa:
                continue
            try:
                tarea()
            except Exception:
                log.exception("Error en el vigilante")

    @staticmethod
    def _sincronizar():
        from impresora.servicios import sincronizar_impresoras

        sincronizar_impresoras()

    def _repetir(self, tarea, intervalo: float) -> None:
        while not self._parar.is_set():
            close_old_connections()
            try:
                tarea()
            except Exception:
                log.exception("Error en el vigilante")
            self._parar.wait(intervalo)

    def _bucle_carpeta(self) -> None:
        ultima_sincronizacion = float("-inf")
        while not self._parar.is_set():
            close_old_connections()
            ahora = time.monotonic()
            hacer_sync = ahora - ultima_sincronizacion >= INTERVALO_IMPRESORAS
            self.ciclo(ahora, colas=False, carpeta=True, impresoras=hacer_sync)
            if hacer_sync:
                ultima_sincronizacion = ahora
            self._parar.wait(INTERVALO_CARPETA)

    def iniciar(self) -> None:
        """Dos hilos: las colas nunca esperan a que termine una captura larga."""
        (self.carpeta / "rechazados").mkdir(parents=True, exist_ok=True)
        self._hilos = [
            threading.Thread(target=self._repetir, args=(lambda: self.revisar_colas(), INTERVALO_COLAS),
                             name="vigilante-colas", daemon=True),
            threading.Thread(target=self._bucle_carpeta, name="vigilante-carpeta", daemon=True),
        ]
        for hilo in self._hilos:
            hilo.start()

    def detener(self) -> None:
        self._parar.set()
