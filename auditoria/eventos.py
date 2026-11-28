"""Eventos 307 (documento impreso) del registro Microsoft-Windows-PrintService/Operational."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class EventoImpresion:
    id_registro: int
    fecha: datetime
    documento: str
    usuario: str
    impresora: str
    paginas: int


def _local(nombre: str) -> str:
    return nombre.rsplit("}", 1)[-1]


def _hijo(elemento, nombre):
    return next((h for h in elemento if _local(h.tag) == nombre), None)


def _fecha(texto: str) -> datetime:
    base, _, fraccion = texto.rstrip("Z").partition(".")
    return datetime.fromisoformat(base).replace(microsecond=int((fraccion + "000000")[:6]), tzinfo=timezone.utc)


def parsear(xml: str) -> list[EventoImpresion]:
    eventos = []
    for ev in ET.fromstring(xml):
        sistema, datos = _hijo(ev, "System"), _hijo(ev, "UserData")
        if sistema is None or datos is None or _hijo(sistema, "EventID").text.strip() != "307":
            continue
        impreso = next(iter(datos), None)
        if impreso is None:
            continue
        p = {_local(h.tag): (h.text or "").strip() for h in impreso}
        try:
            paginas = int(p.get("Param8") or 0)
        except ValueError:
            paginas = 0
        eventos.append(EventoImpresion(
            id_registro=int(_hijo(sistema, "EventRecordID").text),
            fecha=_fecha(_hijo(sistema, "TimeCreated").get("SystemTime")),
            documento=p.get("Param2", ""),
            usuario=p.get("Param3", ""),
            impresora=p.get("Param5", ""),
            paginas=paginas,
        ))
    return eventos
