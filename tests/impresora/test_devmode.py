import struct

import pytest

from impresora.base import CamposDevmode
from impresora.devmode import con_copias, leer_campos


def _raw(paper=1, length=2794, width=2159, orient=1, quality=-4, color=2, copies=1, drv=0x0400):
    """DEVMODEW de 220 bytes públicos + 40 bytes privados del driver."""
    buf = bytearray(260)
    buf[0:10] = "EPSON".encode("utf-16-le")
    struct.pack_into("<HHHH", buf, 64, 0x0401, drv, 220, 40)
    struct.pack_into("<h", buf, 76, orient)
    struct.pack_into("<hhh", buf, 78, paper, length, width)
    struct.pack_into("<h", buf, 86, copies)
    struct.pack_into("<hh", buf, 90, quality, color)
    buf[220:] = bytes(range(40))
    return bytes(buf)


def test_leer_campos():
    c = leer_campos(_raw(paper=1, length=2794, width=2159, orient=1, quality=-4, color=2, copies=3, drv=0x0400))
    assert c == CamposDevmode(1, 2159, 2794, 1, -4, True, 3, 0x0400)


def test_leer_campos_monocromo():
    assert leer_campos(_raw(color=1)).color is False


def test_con_copias_no_toca_parte_privada():
    raw = _raw(copies=5)
    nuevo = con_copias(raw, 1)
    assert leer_campos(nuevo).copias == 1
    assert nuevo[220:] == raw[220:]
    assert len(nuevo) == len(raw)


def test_devmode_corto():
    with pytest.raises(ValueError):
        leer_campos(b"\x00" * 10)
    with pytest.raises(ValueError):
        con_copias(b"\x00" * 10, 1)
