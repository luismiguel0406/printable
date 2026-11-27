"""Tamaños de papel conocidos y reconocimiento por medidas en mm."""

TAMANOS: dict[str, tuple[float, float]] = {
    "Carta": (215.9, 279.4),
    "A4": (210, 297),
    "Legal": (215.9, 355.6),
    "4x6": (101.6, 152.4),
    "5x7": (127, 177.8),
    "8x10": (203.2, 254),
}

PERSONALIZADO = "Personalizado"
TOLERANCIA_MM = 2.0


def tamanos_conocidos() -> dict[str, tuple[float, float]]:
    """Los tamaños que Luis tiene en Tarifas; si la base no está lista, los de fábrica."""
    try:
        from tarifas.models import TamanoPapel

        propios = {t.nombre: (t.ancho_mm, t.alto_mm) for t in TamanoPapel.objects.all()}
        return propios or TAMANOS
    except Exception:
        return TAMANOS


def reconocer(ancho_mm: float, alto_mm: float, tamanos: dict | None = None) -> str:
    corto, largo = sorted((ancho_mm, alto_mm))
    for nombre, (w, h) in (tamanos if tamanos is not None else tamanos_conocidos()).items():
        w, h = sorted((w, h))
        if abs(corto - w) <= TOLERANCIA_MM and abs(largo - h) <= TOLERANCIA_MM:
            return nombre
    return PERSONALIZADO
