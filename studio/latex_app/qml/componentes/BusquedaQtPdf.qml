// BusquedaQtPdf — la búsqueda dentro del PDF (PdfSearchModel) sobre el documento de VisorPdf. Aparte, como
// DocumentoQtPdf, para que VisorPdf no importe QtQuick.Pdf. Cuenta los resultados sin bloquear la ventana (`count` crece
// mientras busca) y da el resultado actual con su página y su punto (`currentResultLink`).
import QtQuick
import QtQuick.Pdf

PdfSearchModel {}
