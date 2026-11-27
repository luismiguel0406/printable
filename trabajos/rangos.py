"""Interpreta rangos de páginas como «1, 3-5»."""

import re

_PARTE = re.compile(r"^(\d+)(?:-(\d+))?$")


def parsear_rango(texto: str, total: int) -> list[int]:
    texto = (texto or "").strip()
    if not texto:
        return list(range(1, total + 1))
    paginas: set[int] = set()
    for parte in texto.split(","):
        parte = parte.strip().replace(" ", "")
        m = _PARTE.match(parte)
        if not m:
            raise ValueError(f"Páginas no válidas: «{parte or texto}». Usa por ejemplo 1, 3-5")
        inicio = int(m.group(1))
        fin = int(m.group(2) or inicio)
        if inicio > fin:
            raise ValueError(f"Páginas no válidas: «{parte}» (el inicio es mayor que el final)")
        if inicio < 1 or fin > total:
            raise ValueError(f"Página fuera de rango en «{parte}»: el documento tiene {total} página(s)")
        paginas.update(range(inicio, fin + 1))
    return sorted(paginas)
