from decimal import Decimal as D

import pytest

from tarifas.precio import Tarifas, cargar_tarifas, precio_pagina
from trabajos.cobertura import Cobertura

T = Tarifas(
    costo_cm2={"C": D("0.01"), "M": D("0.01"), "Y": D("0.01"), "K": D("0.02")},
    costo_hoja={("Glossy", "4x6"): (D("10"), D("25"))},
    margen=D("0.5"),
    redondeo=D("5"),
)


def test_precio():
    p = precio_pagina(Cobertura(0.5, 0.5, 0.5, 0.1), D("154.84"), "Glossy", "4x6", D("1.3"), T)
    # tinta = (0.5*0.01*3 + 0.1*0.02) * 154.84 * 1.3 = 3.421964
    assert p.tinta == pytest.approx(D("3.421964"), abs=D("0.000001"))
    assert p.papel == D("10")
    assert p.costo == p.papel + p.tinta
    assert p.precio == D("25")  # 13.42 * 1.5 = 20.13 < mínimo 25


def test_precio_redondea_hacia_arriba():
    p = precio_pagina(Cobertura(1, 1, 1, 1), D("154.84"), "Glossy", "4x6", D("1"), T)
    # tinta = 0.05 * 154.84 = 7.742; costo 17.742; ×1.5 = 26.613 → 30
    assert p.precio == D("30")


def test_redondeo_exacto_no_sube():
    t = Tarifas(T.costo_cm2, {("Glossy", "4x6"): (D("20"), D("0"))}, D("0.5"), D("5"))
    assert precio_pagina(Cobertura(0, 0, 0, 0), D("1"), "Glossy", "4x6", D("1"), t).precio == D("30")


def test_falta_costo_hoja():
    with pytest.raises(KeyError, match="Bond.*Carta"):
        precio_pagina(Cobertura(0, 0, 0, 0), D("1"), "Bond", "Carta", D("1"), T)


def test_cargar_tarifas(db):
    t = cargar_tarifas()
    assert set(t.costo_cm2) == {"C", "M", "Y", "K"}
    assert ("Glossy", "4x6") in t.costo_hoja
    assert t.margen == D("0.50") and t.redondeo == D("1.00")
