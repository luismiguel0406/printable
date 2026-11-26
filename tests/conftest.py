import pytest


@pytest.fixture
def controlador_falso(settings):
    settings.IMPRESORA_BACKEND = "falso"
    from impresora import falso

    falso.reiniciar()
    yield falso.instancia()
    falso.reiniciar()
