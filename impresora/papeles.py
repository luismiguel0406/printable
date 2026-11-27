"""Tamaños de papel conocidos y reconocimiento por medidas en mm."""

TAMANOS: dict[str, tuple[float, float]] = {
    "Carta": (215.9, 279.4),
    "A4": (210, 297),
    "Oficio": (215.9, 355.6),
    "4x6": (101.6, 152.4),
    "5x7": (127, 177.8),
    "8x10": (203.2, 254),
}

PERSONALIZADO = "Personalizado"
TOLERANCIA_MM = 2.0


def reconocer(ancho_mm: float, alto_mm: float) -> str:
    corto, largo = sorted((ancho_mm, alto_mm))
    for nombre, (w, h) in TAMANOS.items():
        if abs(corto - w) <= TOLERANCIA_MM and abs(largo - h) <= TOLERANCIA_MM:
            return nombre
    return PERSONALIZADO
