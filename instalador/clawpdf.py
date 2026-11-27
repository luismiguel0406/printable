"""Configuración de clawPDF para Printable (mismo formato de registro que PDFCreator)."""

from pathlib import PureWindowsPath

RAIZ_REGISTRO = r"Software\clawSoft\clawPDF\Settings"
NOMBRE_IMPRESORA = "Printable"
GUID_PERFIL = "DefaultGuid"  # el perfil predeterminado de clawPDF


def valores_registro(carpeta_entrada) -> dict[str, dict[str, str]]:
    """Subclave (relativa a RAIZ_REGISTRO) → valores de texto a escribir en HKCU."""
    destino = str(PureWindowsPath(carpeta_entrada))
    if not destino.endswith("\\"):
        destino += "\\"  # clawPDF/PDFCreator esperan la barra final
    return {
        r"ConversionProfiles\0": {
            "Guid": GUID_PERFIL,
            "FileNameTemplate": "<Title>_<DateTime:yyyyMMddHHmmss>",
            "OutputFormat": "Pdf",
            "OpenViewer": "False",
            "ShowProgress": "False",
            "SkipPrintDialog": "True",
        },
        r"ConversionProfiles\0\AutoSave": {
            "Enabled": "True",
            "TargetDirectory": destino,
            "EnsureUniqueFilenames": "True",
        },
        r"ApplicationSettings\PrinterMappings": {"numClasses": "1"},
        r"ApplicationSettings\PrinterMappings\0": {
            "PrinterName": NOMBRE_IMPRESORA,
            "ProfileGuid": GUID_PERFIL,
        },
    }
