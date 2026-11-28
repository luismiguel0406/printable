from pathlib import Path

from instalador.clawpdf import RAIZ_REGISTRO, valores_registro
from instalador.configurar import comando_colas, es_impresora_real


def test_valores_registro_autoguardado(tmp_path):
    carpeta = Path(r"C:\ProgramData\Printable\entrada")
    v = valores_registro(carpeta)
    assert RAIZ_REGISTRO == r"Software\clawSoft\clawPDF\Settings"
    perfil = v[r"ConversionProfiles\0"]
    assert perfil["FileNameTemplate"] == "<Title>_<DateTime:yyyyMMddHHmmss>"
    assert perfil["OpenViewer"] == "False" and perfil["ShowProgress"] == "False"
    assert perfil["SkipPrintDialog"] == "True" and perfil["OutputFormat"] == "Pdf"
    auto = v[r"ConversionProfiles\0\AutoSave"]
    assert auto["Enabled"] == "True" and auto["EnsureUniqueFilenames"] == "True"
    assert auto["TargetDirectory"] == "C:\\ProgramData\\Printable\\entrada\\"  # con barra final
    mapeo = v[r"ApplicationSettings\PrinterMappings\0"]
    assert mapeo == {"PrinterName": "Printable", "ProfileGuid": perfil["Guid"]}
    assert v[r"ApplicationSettings\PrinterMappings"]["numClasses"] == "1"


def test_comando_colas():
    assert comando_colas("HP DeskJet 2700") == [
        "rundll32.exe", "printui.dll,PrintUIEntry", "/Xs", "/n", "HP DeskJet 2700", "attributes", "+queued"]


def test_impresoras_reales():
    assert es_impresora_real("EPSON L355 Series") and es_impresora_real("HP DeskJet 2700")
    assert not es_impresora_real("Printable") and not es_impresora_real("Microsoft Print to PDF")
    assert not es_impresora_real("clawPDF") and not es_impresora_real("Fax")


def test_xml_tarea_corre_como_system_y_se_repite():
    import xml.etree.ElementTree as ET

    from instalador.configurar import xml_tarea

    texto = xml_tarea(Path(r"C:\Program Files\Printable\python"), Path(r"C:\Program Files\Printable\app"))
    ET.fromstring(texto.encode("utf-16"))  # debe ser XML válido (Task Scheduler lo pide en UTF-16)
    assert "<UserId>S-1-5-18</UserId>" in texto and "<Interval>PT5M</Interval>" in texto
    assert "<MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>" in texto
    assert "<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>" in texto and "<BootTrigger>" in texto
    assert r"C:\Program Files\Printable\python\pythonw.exe" in texto
    assert r"&quot;C:\Program Files\Printable\app\vigilante_servicio.py&quot;" in texto


def test_comando_permisos_usuarios_modificar():
    from instalador.configurar import comando_permisos

    assert comando_permisos(Path(r"C:\ProgramData\Printable")) == [
        "icacls", r"C:\ProgramData\Printable", "/grant", "*S-1-5-32-545:(OI)(CI)M", "/T", "/C", "/Q"]


def test_comando_registro():
    from instalador.configurar import comando_registro

    assert comando_registro() == ["wevtutil", "sl", "Microsoft-Windows-PrintService/Operational", "/e:true"]


def test_comandos_vigilante_y_quitar():
    from instalador.configurar import TAREA, comandos_quitar, comandos_vigilante

    assert TAREA == r"Printable\Vigilante"
    crear, correr = comandos_vigilante(Path("t.xml"))
    assert crear == ["schtasks", "/Create", "/TN", TAREA, "/XML", "t.xml", "/F"]
    assert correr == ["schtasks", "/Run", "/TN", TAREA]
    assert comandos_quitar() == [["schtasks", "/End", "/TN", TAREA], ["schtasks", "/Delete", "/TN", TAREA, "/F"]]
