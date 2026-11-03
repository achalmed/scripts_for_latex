// DocumentoQtPdf — el PDF abierto con QtQuick.Pdf. Vive en su propio archivo para que VisorPdf no importe QtQuick.Pdf:
// VisorPdf lo carga con un Loader solo si el módulo está (studio.visor.motor === "qtpdf"); sin él, usa pdftoppm.
import QtQuick
import QtQuick.Pdf

PdfDocument {}
