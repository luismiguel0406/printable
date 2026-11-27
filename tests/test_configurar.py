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
