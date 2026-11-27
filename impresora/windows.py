"""Backend real para Windows: driver nativo (DocumentProperties) + impresión GDI.

Debe ejecutarse en la sesión de escritorio del usuario (no como servicio) para que
la ventana de preferencias del driver pueda mostrarse.
"""

import ctypes
from ctypes import wintypes
from typing import Iterable

import win32print
from PIL import Image, ImageWin

from .base import ErrorImpresora, InfoPapel, envolver_errores
from .estado import motivo_bloqueo
from .devmode import con_copias

DM_OUT_BUFFER = 2
DM_IN_PROMPT = 4
DM_IN_BUFFER = 8
IDOK = 1
IDCANCEL = 2

HORZRES, VERTRES = 8, 10
LOGPIXELSX, LOGPIXELSY = 88, 90
PHYSICALWIDTH, PHYSICALHEIGHT = 110, 111
PHYSICALOFFSETX, PHYSICALOFFSETY = 112, 113

_winspool = ctypes.WinDLL("winspool.drv", use_last_error=True)
_gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
_user32 = ctypes.WinDLL("user32", use_last_error=True)

_winspool.OpenPrinterW.argtypes = [wintypes.LPWSTR, ctypes.POINTER(wintypes.HANDLE), ctypes.c_void_p]
_winspool.OpenPrinterW.restype = wintypes.BOOL
_winspool.ClosePrinter.argtypes = [wintypes.HANDLE]
_winspool.ClosePrinter.restype = wintypes.BOOL
_winspool.DocumentPropertiesW.argtypes = [
    wintypes.HWND, wintypes.HANDLE, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
]
_winspool.DocumentPropertiesW.restype = wintypes.LONG

_gdi32.CreateDCW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p]
_gdi32.CreateDCW.restype = wintypes.HDC
_gdi32.DeleteDC.argtypes = [wintypes.HDC]
_gdi32.GetDeviceCaps.argtypes = [wintypes.HDC, ctypes.c_int]
_gdi32.GetDeviceCaps.restype = ctypes.c_int


class DOCINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_int),
        ("lpszDocName", wintypes.LPCWSTR),
        ("lpszOutput", wintypes.LPCWSTR),
        ("lpszDatatype", wintypes.LPCWSTR),
        ("fwType", wintypes.DWORD),
    ]


_gdi32.StartDocW.argtypes = [wintypes.HDC, ctypes.POINTER(DOCINFOW)]
_gdi32.StartDocW.restype = ctypes.c_int
for _f in ("StartPage", "EndPage", "EndDoc", "AbortDoc"):
    getattr(_gdi32, _f).argtypes = [wintypes.HDC]
    getattr(_gdi32, _f).restype = ctypes.c_int
_user32.GetForegroundWindow.restype = wintypes.HWND


class _Impresora:
    def __init__(self, nombre: str):
        self.nombre = nombre
        self.handle = wintypes.HANDLE()

    def __enter__(self):
        if not _winspool.OpenPrinterW(self.nombre, ctypes.byref(self.handle), None):
            raise ErrorImpresora(f"No se pudo abrir la impresora «{self.nombre}»")
        return self.handle

    def __exit__(self, *exc):
        _winspool.ClosePrinter(self.handle)


def _document_properties(impresora: str, entrada: bytes | None, preguntar: bool) -> bytes | None:
    with _Impresora(impresora) as h:
        tamano = _winspool.DocumentPropertiesW(None, h, impresora, None, None, 0)
        if tamano <= 0:
            raise ErrorImpresora("El driver no devolvió su configuración")
        salida = ctypes.create_string_buffer(tamano)
        modo = DM_OUT_BUFFER
        buf_entrada = None
        if entrada is not None:
            buf_entrada = ctypes.create_string_buffer(entrada, max(len(entrada), tamano))
            modo |= DM_IN_BUFFER
        hwnd = None
        if preguntar:
            modo |= DM_IN_PROMPT
            hwnd = _user32.GetForegroundWindow()
        r = _winspool.DocumentPropertiesW(hwnd, h, impresora, salida, buf_entrada, modo)
        if r == IDCANCEL and preguntar:
            return None
        if r < 0:
            raise ErrorImpresora("El driver rechazó la configuración")
        return salida.raw


class _DC:
    def __init__(self, impresora: str, devmode: bytes):
        self.impresora = impresora
        self.buffer = ctypes.create_string_buffer(devmode, len(devmode))
        self.hdc = None

    def __enter__(self):
        self.hdc = _gdi32.CreateDCW("WINSPOOL", self.impresora, None, self.buffer)
        if not self.hdc:
            raise ErrorImpresora(f"No se pudo preparar la impresora «{self.impresora}»")
        return self.hdc

    def __exit__(self, *exc):
        _gdi32.DeleteDC(self.hdc)


class ControladorWindows:
    @envolver_errores
    def listar_impresoras(self) -> list[str]:
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        return [p[2] for p in win32print.EnumPrinters(flags)]

    @envolver_errores
    def devmode_predeterminado(self, impresora: str) -> bytes:
        return _document_properties(impresora, None, preguntar=False)

    @envolver_errores
    def abrir_preferencias(self, impresora: str, devmode: bytes) -> bytes | None:
        return _document_properties(impresora, devmode, preguntar=True)

    @envolver_errores
    def info_papel(self, impresora: str, devmode: bytes) -> InfoPapel:
        with _DC(impresora, devmode) as hdc:
            cap = lambda i: _gdi32.GetDeviceCaps(hdc, i)  # noqa: E731
            dpi_x, dpi_y = cap(LOGPIXELSX), cap(LOGPIXELSY)
            mm_x = lambda px: px / dpi_x * 25.4  # noqa: E731
            mm_y = lambda px: px / dpi_y * 25.4  # noqa: E731
            return InfoPapel(
                ancho_mm=mm_x(cap(PHYSICALWIDTH)),
                alto_mm=mm_y(cap(PHYSICALHEIGHT)),
                imprimible_x_mm=mm_x(cap(PHYSICALOFFSETX)),
                imprimible_y_mm=mm_y(cap(PHYSICALOFFSETY)),
                imprimible_ancho_mm=mm_x(cap(HORZRES)),
                imprimible_alto_mm=mm_y(cap(VERTRES)),
            )

    @envolver_errores
    def version_driver(self, impresora: str) -> str:
        h = win32print.OpenPrinter(impresora)
        try:
            nombre = win32print.GetPrinter(h, 2)["pDriverName"]
            try:
                info = win32print.GetPrinterDriver(h, None, 6)
                version = info.get("DriverVersion", "")
            except Exception:
                version = win32print.GetPrinterDriver(h, None, 2).get("Version", "")
            return f"{nombre} v{version}"
        finally:
            win32print.ClosePrinter(h)

    @staticmethod
    def _verificar_disponible(impresora: str) -> None:
        h = win32print.OpenPrinter(impresora)
        try:
            info = win32print.GetPrinter(h, 2)
        finally:
            win32print.ClosePrinter(h)
        motivo = motivo_bloqueo(info.get("Attributes", 0), info.get("Status", 0))
        if motivo:
            raise ErrorImpresora(motivo)

    @envolver_errores
    def imprimir(
        self,
        impresora: str,
        devmode: bytes,
        paginas: Iterable[Image.Image],
        nombre_documento: str,
    ) -> None:
        self._verificar_disponible(impresora)
        try:
            with _DC(impresora, con_copias(devmode, 1)) as hdc:
                ancho, alto = _gdi32.GetDeviceCaps(hdc, HORZRES), _gdi32.GetDeviceCaps(hdc, VERTRES)
                info = DOCINFOW(ctypes.sizeof(DOCINFOW), nombre_documento[:200], None, None, 0)
                if _gdi32.StartDocW(hdc, ctypes.byref(info)) <= 0:
                    raise ErrorImpresora("La impresora no aceptó el trabajo (¿está encendida?)")
                try:
                    for pagina in paginas:
                        if _gdi32.StartPage(hdc) <= 0:
                            raise ErrorImpresora("Error al iniciar la página")
                        ImageWin.Dib(pagina.convert("RGB")).draw(hdc, (0, 0, ancho, alto))
                        if _gdi32.EndPage(hdc) <= 0:
                            raise ErrorImpresora("Error al enviar la página a la impresora")
                except BaseException:
                    _gdi32.AbortDoc(hdc)
                    raise
                if _gdi32.EndDoc(hdc) <= 0:
                    raise ErrorImpresora("La impresora no terminó de recibir el trabajo")
        except ErrorImpresora:
            raise
        except Exception as e:  # cualquier otro fallo del sistema
            raise ErrorImpresora(f"Error al imprimir: {e}") from e


_instancia: ControladorWindows | None = None


def instancia() -> ControladorWindows:
    global _instancia
    if _instancia is None:
        _instancia = ControladorWindows()
    return _instancia
