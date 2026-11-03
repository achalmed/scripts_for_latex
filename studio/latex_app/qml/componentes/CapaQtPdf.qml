// CapaQtPdf — lo que se hace con el texto de una página del PDF cuando QtQuick.Pdf está instalado: seleccionar arrastrando
// (PdfSelection) y copiar, los enlaces del PDF (PdfLinkModel: internos → la página y el punto; externos → studio.visor,
// que solo abre http, https y mailto) y los resultados de la búsqueda (PdfSearchModel de VisorPdf) resaltados. Vive
// aparte, como PaginaQtPdf, para que VisorPdf no importe QtQuick.Pdf. Va encima de la página, con su mismo tamaño; todo
// lo de QtPdf está en puntos y se escala con `zoom` (píxeles por punto, el del visor).
// La marca de SyncTeX y el doble clic (PDF → código) siguen en VisorPdf: esta capa no toma el doble clic (un arrastre
// empieza a seleccionar; un clic suelto borra la selección; un doble clic no selecciona nada).
import QtQuick
import QtQuick.Shapes
import QtQuick.Pdf
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Item {
    id: raiz
    property var document: null
    property int pagina: 1                 // 1-based, como el modelo del visor
    property real zoom: 1
    property var busqueda: null            // el PdfSearchModel del visor (o null)
    readonly property string texto: seleccion.text
    readonly property bool arrastrando: arrastre.active

    signal irA(int pagina, real y)         // un enlace interno: página 1-based, y en puntos desde arriba
    signal enlaceExterno(string url)
    signal seleccionEmpezada()
    signal menuPedido(real x, real y)      // clic derecho, en coordenadas de la capa

    function copiar() { if (seleccion.text !== "") seleccion.copyToClipboard() }
    function seleccionarTodo() { seleccion.selectAll() }
    function limpiar() { seleccion.from = Qt.point(0, 0); seleccion.to = Qt.point(0, 0); seleccion.clear() }

    // la búsqueda: los resultados de esta página (en puntos); se piden de nuevo al cambiar la cadena o la página
    function actualizarResultados() { resultados.paths = raiz.busqueda ? raiz.busqueda.boundingPolygonsOnPage(raiz.pagina - 1) : [] }
    onPaginaChanged: actualizarResultados()
    onBusquedaChanged: actualizarResultados()
    Connections {
        target: raiz.busqueda
        ignoreUnknownSignals: true
        function onSearchStringChanged() { raiz.actualizarResultados() }
        function onCountChanged() { raiz.actualizarResultados() }
        function onCurrentPageBoundingPolygonsChanged() { raiz.actualizarResultados() }
    }

    Shape {
        anchors.fill: parent
        ShapePath {
            strokeWidth: -1
            fillColor: Qt.alpha(Kirigami.Theme.neutralTextColor, 0.35)
            scale: Qt.size(raiz.zoom, raiz.zoom)
            PathMultiline { id: resultados }
        }
        ShapePath {
            strokeWidth: -1
            fillColor: Qt.alpha(Kirigami.Theme.highlightColor, 0.35)
            scale: Qt.size(raiz.zoom, raiz.zoom)
            PathMultiline { paths: seleccion.geometry }
        }
    }
    Shape {
        anchors.fill: parent
        visible: raiz.busqueda !== null && raiz.busqueda.currentPage === raiz.pagina - 1 && raiz.busqueda.count > 0
        ShapePath {
            strokeWidth: 2
            strokeColor: Kirigami.Theme.highlightColor
            fillColor: "transparent"
            scale: Qt.size(raiz.zoom, raiz.zoom)
            PathMultiline { paths: raiz.busqueda ? raiz.busqueda.currentResultBoundingPolygons : [] }
        }
    }

    DragHandler {
        id: arrastre
        acceptedDevices: PointerDevice.Mouse | PointerDevice.Stylus
        acceptedButtons: Qt.LeftButton
        target: null
        onActiveChanged: if (active) raiz.seleccionEmpezada()
    }
    TapHandler {
        id: clic
        acceptedDevices: PointerDevice.Mouse | PointerDevice.Stylus
        acceptedButtons: Qt.LeftButton
    }
    TapHandler {
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad | PointerDevice.Stylus
        acceptedButtons: Qt.RightButton
        onTapped: (punto) => raiz.menuPedido(punto.position.x, punto.position.y)
    }
    HoverHandler { cursorShape: Qt.IBeamCursor }

    PdfSelection {
        id: seleccion
        anchors.fill: parent
        document: raiz.document
        page: raiz.pagina - 1
        renderScale: raiz.zoom
        from: arrastre.centroid.pressPosition
        to: arrastre.centroid.position
        // se conserva al soltar; un clic suelto (sin arrastre) la borra
        hold: !arrastre.active && !clic.pressed
    }

    Repeater {
        model: PdfLinkModel {
            document: raiz.document
            page: raiz.pagina - 1
        }
        delegate: Item {
            id: enlace
            required property rect rectangle
            required property url url
            required property int page
            required property point location
            x: rectangle.x * raiz.zoom
            y: rectangle.y * raiz.zoom
            width: rectangle.width * raiz.zoom
            height: rectangle.height * raiz.zoom
            readonly property string destino: page >= 0 ? "Ir a la página " + (page + 1) : String(url)
            Accessible.role: Accessible.Link
            Accessible.name: destino
            HoverHandler { id: sobreEnlace; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                acceptedButtons: Qt.LeftButton
                gesturePolicy: TapHandler.ReleaseWithinBounds
                onTapped: {
                    if (enlace.page >= 0) raiz.irA(enlace.page + 1, enlace.location.y)
                    else raiz.enlaceExterno(String(enlace.url))
                }
            }
            Rectangle {
                anchors.fill: parent
                visible: sobreEnlace.hovered
                color: "transparent"
                border.color: Kirigami.Theme.linkColor
                border.width: 1
                radius: 2
            }
            QQC2.ToolTip.visible: sobreEnlace.hovered
            QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
            QQC2.ToolTip.text: destino
        }
    }
}
