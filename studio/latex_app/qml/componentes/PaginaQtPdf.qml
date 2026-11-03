// PaginaQtPdf — una página del PDF pintada por Qt (PdfPageImage) a la resolución de sourceSize. Solo se carga si
// QtQuick.Pdf está instalado (VisorPdf); el tamaño, el zoom, la marca de SyncTeX y el doble clic los pone VisorPdf.
// Ojo: asignar `document` (o terminar de cargarlo) devuelve `currentFrame` a 0 y rompe cualquier enlace con él, así
// que el fotograma se fija a mano cada vez que cambia la página, el documento o el estado (lo vigila una prueba).
import QtQuick
import QtQuick.Pdf

PdfPageImage {
    id: raiz
    property int pagina: 1

    function fijar() { if (raiz.currentFrame !== raiz.pagina - 1) raiz.currentFrame = raiz.pagina - 1 }

    asynchronous: true
    cache: false
    smooth: true
    mipmap: true
    fillMode: Image.Stretch

    // El papel: QtPdf pinta la página sin fondo (transparente) y en el tema oscuro el texto negro quedaba sobre gris.
    // El blanco es del documento, no de la interfaz: es lo que da un PDF sin fondo al imprimirse, lo que pintaba
    // pdftoppm y lo que muestra Okular por omisión. Va debajo de la página (z negativo).
    Rectangle { anchors.fill: parent; z: -1; color: "white" }

    onPaginaChanged: fijar()
    onDocumentChanged: fijar()
    onStatusChanged: fijar()
    Component.onCompleted: fijar()
}
