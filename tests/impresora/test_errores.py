import pytest

from impresora.base import ErrorImpresora, envolver_errores
from impresora.estado import motivo_bloqueo


# Hallazgo 7
def test_envolver_convierte_cualquier_error():
    class C:
        @envolver_errores
        def f(self):
            raise OSError("pywintypes.error: (1801, 'OpenPrinter', 'nombre no válido')")

    with pytest.raises(ErrorImpresora, match="1801"):
        C().f()


def test_envolver_respeta_error_impresora():
    @envolver_errores
    def f():
        raise ErrorImpresora("igual")

    with pytest.raises(ErrorImpresora, match="^igual$"):
        f()


# Hallazgo 8
@pytest.mark.parametrize(
    "atributos,estado,bloquea",
    [(0, 0, False), (0x400, 0, True), (0, 0x80, True), (0, 0x2, True), (0, 0x10, True), (0, 0x1000, True), (0, 0x400, False)],
)
def test_motivo_bloqueo(atributos, estado, bloquea):
    assert (motivo_bloqueo(atributos, estado) is not None) == bloquea
