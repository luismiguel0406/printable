import socket

import pytest

import lanzador
from config import servir


def test_servidor_activo():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen()
    puerto = s.getsockname()[1]
    assert servir.servidor_activo(puerto)
    s.close()
    assert not servir.servidor_activo(puerto)


def test_segunda_ejecucion_solo_abre_el_navegador(monkeypatch):
    abiertos, arrancados = [], []
    monkeypatch.setattr(servir, "servidor_activo", lambda puerto=8000: True)
    monkeypatch.setattr(lanzador.webbrowser, "open", abiertos.append)
    monkeypatch.setattr(lanzador, "iniciar", lambda abrir: arrancados.append(abrir))
    assert lanzador.main(["--abrir"]) == 0
    assert abiertos == ["http://127.0.0.1:8000/"] and arrancados == []


def test_primera_ejecucion_arranca(monkeypatch):
    arrancados = []
    monkeypatch.setattr(servir, "servidor_activo", lambda puerto=8000: False)
    monkeypatch.setattr(lanzador, "iniciar", lambda abrir: arrancados.append(abrir))
    assert lanzador.main([]) == 0 and arrancados == [False]
    lanzador.main(["--abrir"])
    assert arrancados == [False, True]


def test_datos_por_defecto_en_programdata(monkeypatch):
    import os

    entorno = {k: v for k, v in os.environ.items() if k != "PRINTABLE_DATOS"}
    entorno["PROGRAMDATA"] = r"C:\ProgramData"
    monkeypatch.setattr(os, "environ", entorno)
    lanzador.preparar_entorno()
    assert os.environ["PRINTABLE_DATOS"].endswith("Printable")
    assert os.environ["DJANGO_SETTINGS_MODULE"] == "config.settings"
