"""Sugiere impresora y perfil según si el documento tiene color."""

from dataclasses import dataclass

from impresora.models import Impresora

from .models import PerfilImpresion

USO_TEXTO = {"color": "para color", "bn": "para B/N"}


@dataclass
class Sugerencia:
    impresora: Impresora | None
    perfil: PerfilImpresion | None
    motivo: str


def _lista(numeros: list[int]) -> str:
    if len(numeros) == 1:
        return f"página {numeros[0]}"
    return "páginas " + ", ".join(map(str, numeros[:-1])) + f" y {numeros[-1]}"


def sugerir(
    paginas_color: list[bool], paginas: list[int], impresora: Impresora | None = None
) -> Sugerencia:
    impresora = impresora or Impresora.predeterminada_o_primera()
    if impresora is None:
        return Sugerencia(None, None, "No hay impresoras disponibles")
    con_color = [n for n in paginas if 0 < n <= len(paginas_color) and paginas_color[n - 1]]
    uso = "color" if con_color else "bn"
    if not con_color:
        motivo = "Sugerido: B/N — ninguna página tiene color"
    elif len(paginas_color) == 1:
        motivo = "Sugerido: Color — la imagen tiene color"
    else:
        motivo = f"Sugerido: Color — {_lista(con_color)}"

    perfiles = PerfilImpresion.objects.filter(impresora=impresora)
    perfil = perfiles.filter(uso_sugerido=uso).first()
    if perfil is None:
        perfil = perfiles.filter(predeterminado=True).first() or perfiles.order_by("nombre").first()
        if perfil is None:
            return Sugerencia(impresora, None, f"{impresora} no tiene perfiles todavía")
        motivo += f" (no hay perfil «{USO_TEXTO[uso]}» en esta impresora)"
    return Sugerencia(impresora, perfil, motivo)
