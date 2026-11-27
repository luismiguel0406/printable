"""Interpreta el estado de la cola de Windows (PRINTER_INFO_2) antes de imprimir."""

PRINTER_ATTRIBUTE_WORK_OFFLINE = 0x400
PRINTER_STATUS_ERROR = 0x2
PRINTER_STATUS_PAPER_OUT = 0x10
PRINTER_STATUS_OFFLINE = 0x80
PRINTER_STATUS_NOT_AVAILABLE = 0x1000

_MOTIVOS = [
    (PRINTER_STATUS_OFFLINE, "La impresora está apagada o desconectada"),
    (PRINTER_STATUS_NOT_AVAILABLE, "La impresora está apagada o desconectada"),
    (PRINTER_STATUS_PAPER_OUT, "La impresora no tiene papel"),
    (PRINTER_STATUS_ERROR, "La impresora tiene un error: revísala"),
]


def motivo_bloqueo(atributos: int, estado: int) -> str | None:
    if atributos & PRINTER_ATTRIBUTE_WORK_OFFLINE:
        return "La impresora está en modo «sin conexión» en Windows"
    for bandera, mensaje in _MOTIVOS:
        if estado & bandera:
            return mensaje
    return None
