"""Convierte un .doc/.docx a PDF con Microsoft Word (solo Windows).

Uso: python -m trabajos.word_a_pdf ENTRADA SALIDA
Corre en su propio proceso para que COM quede aislado del servidor web.
"""

import sys

WD_FORMAT_PDF = 17


def convertir(entrada: str, salida: str) -> None:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(entrada, ReadOnly=True, AddToRecentFiles=False)
        try:
            doc.SaveAs2(salida, FileFormat=WD_FORMAT_PDF)
        finally:
            doc.Close(False)
    finally:
        if word is not None:
            word.Quit()
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    convertir(sys.argv[1], sys.argv[2])
