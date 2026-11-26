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
