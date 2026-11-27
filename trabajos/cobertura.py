"""Medición de cobertura de tinta CMYK de una página rasterizada."""

from dataclasses import dataclass

from PIL import Image, ImageChops, ImageMath, ImageStat


@dataclass(frozen=True)
class Cobertura:
    c: float
    m: float
    y: float
    k: float

    def como_dict(self) -> dict[str, float]:
        return {"c": self.c, "m": self.m, "y": self.y, "k": self.k}


def _a_rgb(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        fondo = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(fondo, rgba).convert("RGB")
    return img.convert("RGB")


def _media(banda: Image.Image) -> float:
    return round(ImageStat.Stat(banda).mean[0] / 255, 4)


def medir_cobertura(img: Image.Image, monocromo: bool) -> Cobertura:
    rgb = _a_rgb(img)
    if monocromo:
        k = ImageChops.invert(rgb.convert("L"))
        return Cobertura(0.0, 0.0, 0.0, _media(k))

    r, g, b = rgb.split()
    maximo = ImageChops.lighter(ImageChops.lighter(r, g), b)
    k = ImageChops.invert(maximo)

    def canal(x: Image.Image) -> Image.Image:
        # C = (1 - R - K) / (1 - K) = (max - R) / max, en escala 0–255
        res = ImageMath.lambda_eval(
            lambda a: (a["float"](a["mx"]) - a["float"](a["x"])) * 255.0
            / a["max"](a["float"](a["mx"]), 1.0),
            mx=maximo,
            x=x,
        )
        return res.convert("L")

    return Cobertura(_media(canal(r)), _media(canal(g)), _media(canal(b)), _media(k))
