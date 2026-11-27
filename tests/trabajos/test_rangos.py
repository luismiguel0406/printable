import pytest

from trabajos.rangos import parsear_rango


@pytest.mark.parametrize(
    "t,esp",
    [("", [1, 2, 3, 4]), ("  ", [1, 2, 3, 4]), ("2", [2]), ("1, 3-4", [1, 3, 4]), ("4,1", [1, 4]), ("2-2", [2]), ("1,1,2", [1, 2])],
)
def test_rango_ok(t, esp):
    assert parsear_rango(t, 4) == esp


@pytest.mark.parametrize("t", ["0", "5", "3-1", "a", "1-", "-2", "1,,2", "1-9"])
def test_rango_invalido(t):
    with pytest.raises(ValueError, match="[Pp]ágina"):
        parsear_rango(t, 4)


@pytest.mark.parametrize("ns,texto", [([1, 2, 3, 5], "1-3, 5"), ([4, 2], "2, 4"), ([7], "7"), ([], "")])
def test_comprimir_rango(ns, texto):
    from trabajos.rangos import comprimir_rango

    assert comprimir_rango(ns) == texto
