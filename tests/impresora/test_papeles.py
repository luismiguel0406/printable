import pytest

from impresora.papeles import TAMANOS, reconocer


@pytest.mark.parametrize(
    "w,h,esperado",
    [
        (215.9, 279.4, "Carta"),
        (279.4, 215.9, "Carta"),
        (101, 153, "4x6"),
        (210, 297, "A4"),
        (127, 177.8, "5x7"),
        (100, 100, "Personalizado"),
    ],
)
def test_reconocer(w, h, esperado):
    assert reconocer(w, h) == esperado


def test_tamanos_conocidos():
    assert TAMANOS["Oficio"] == (215.9, 355.6)
    assert TAMANOS["8x10"] == (203.2, 254)
