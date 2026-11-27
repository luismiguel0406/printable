from impresora.devmode import texto_version_driver


def test_usa_la_version_del_driver_correcto():
    drivers = [{"Name": "Otro", "DriverVersion": 1}, {"Name": "EPSON L355 Series", "DriverVersion": 281479271677952}]
    assert texto_version_driver("EPSON L355 Series", drivers) == "EPSON L355 Series v281479271677952"


def test_sin_version_usa_solo_el_nombre():
    assert texto_version_driver("HP DeskJet 2700", []) == "HP DeskJet 2700"
    assert texto_version_driver("HP DeskJet 2700", [{"Name": "HP DeskJet 2700"}]) == "HP DeskJet 2700"


def test_version_de_nivel_2():
    assert texto_version_driver("HP", [{"Name": "HP", "Version": 3}]) == "HP v3"
