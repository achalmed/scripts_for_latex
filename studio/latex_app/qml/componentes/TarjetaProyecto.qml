// TarjetaProyecto — un documento en la página de proyectos (rediseño del 2026-11-17, decisiones §1.17): la miniatura de
// la primera página de su PDF (o el icono de su estado si aún no tiene), su título, su tipo y cuándo se compiló, y un
// punto con su estado. Clic: elegirlo (Ctrl+clic: marcarlo para compilar en cola); doble clic: abrirlo. Sin colores
// propios: el estado toma los del tema (positivo, neutro, negativo).
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

QQC2.AbstractButton {
    id: raiz

    property var fila: ({ nombre: "", titulo: "", tipo: "", hace: "", estado: "", clave: "", nivel: "", problemas: "", relativa: "", pdf: "", ruta: "" })
    property bool elegida: false
    property bool marcada: false
    readonly property color colorEstado: fila.nivel === "negativo" ? Kirigami.Theme.negativeTextColor
                                       : fila.nivel === "neutro" ? Kirigami.Theme.neutralTextColor
                                       : fila.nivel === "positivo" ? Kirigami.Theme.positiveTextColor
                                       : fila.nivel === "activo" ? Kirigami.Theme.activeTextColor : Kirigami.Theme.disabledTextColor
    // el texto sobre la elegida: con «Lliphi Dark» (el bloque lleno de gui-comun 4.4), el resaltado; si no, el de siempre
    readonly property color tinta: elegida ? EstiloSeleccion.texto(Kirigami.Theme.textColor, Kirigami.Theme.highlightedTextColor) : Kirigami.Theme.textColor
    readonly property color tenue: elegida ? EstiloSeleccion.texto(Kirigami.Theme.disabledTextColor, Qt.alpha(Kirigami.Theme.highlightedTextColor, 0.75))
                                           : Kirigami.Theme.disabledTextColor

    // el nombre que se enseña de un archivo: «carpeta/main.tex» → «carpeta»; «otro.tex» → «otro»
    function nombreVisible(ruta) {
        const partes = ruta.split("/").filter(x => x !== "")
        const archivo = (partes.pop() || "").replace(/\.tex$/, "")
        return archivo === "main" && partes.length > 0 ? partes.pop() : archivo
    }

    signal elegir(bool marcar)
    signal abrir()

    hoverEnabled: true
    padding: Kirigami.Units.largeSpacing
    topPadding: Kirigami.Units.smallSpacing * 1.5
    Accessible.name: (fila.titulo || fila.nombre) + ", " + fila.estado
    onClicked: elegir(false)
    onDoubleClicked: abrir()
    TapHandler { acceptedModifiers: Qt.ControlModifier; onTapped: raiz.elegir(true) }

    background: Rectangle {
        radius: Kirigami.Units.cornerRadius * 2
        // la elegida como el esquema de color de la ventana (EstiloSeleccion, gui-comun 4.4): con el predeterminado,
        // teñida del acento con su borde; con «Lliphi Dark», el bloque lleno como en Dolphin. Al pasar, un velo tenue
        color: raiz.elegida ? EstiloSeleccion.fondo(Kirigami.Theme.backgroundColor, Kirigami.Theme.highlightColor, raiz.hovered ? 0.14 : 0.10)
             : raiz.hovered ? Qt.alpha(Kirigami.Theme.textColor, 0.04) : Kirigami.Theme.backgroundColor
        border.width: raiz.elegida ? 2 : 1
        border.color: raiz.elegida ? Kirigami.Theme.highlightColor
                    : raiz.marcada ? Qt.alpha(Kirigami.Theme.highlightColor, 0.6) : Qt.alpha(Kirigami.Theme.textColor, raiz.hovered ? 0.25 : 0.14)
    }

    contentItem: ColumnLayout {
        spacing: Kirigami.Units.smallSpacing
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: width * 0.62
            radius: Kirigami.Units.cornerRadius
            color: Qt.alpha(Kirigami.Theme.textColor, 0.04)
            clip: true
            Image {
                id: miniatura
                anchors.fill: parent
                anchors.margins: 1
                fillMode: Image.PreserveAspectCrop
                verticalAlignment: Image.AlignTop
                asynchronous: true
                cache: false
                source: { studio.miniaturas.version; return studio.miniaturas.url(raiz.fila.pdf || "") }
                visible: status === Image.Ready
            }
            Kirigami.Icon {
                anchors.centerIn: parent
                visible: miniatura.status !== Image.Ready
                // sin miniatura, un icono simbólico tenue (antes, la cruz roja de 48 px de «data-error» dominaba la
                // cuadrícula): el error ya lo dice el punto y la línea de estado de abajo
                source: raiz.fila.clave === "errores" ? "dialog-error-symbolic" : "text-x-generic-symbolic"
                implicitWidth: Kirigami.Units.iconSizes.medium
                implicitHeight: implicitWidth
                isMask: true
                color: raiz.fila.clave === "errores" ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.disabledTextColor
                opacity: 0.6
            }
            Rectangle {                                        // marcada para la cola
                visible: raiz.marcada
                anchors.top: parent.top; anchors.right: parent.right; anchors.margins: Kirigami.Units.smallSpacing
                width: Kirigami.Units.iconSizes.smallMedium; height: width; radius: width / 2
                color: Kirigami.Theme.highlightColor
                Kirigami.Icon { anchors.centerIn: parent; source: "checkmark-symbolic"; isMask: true; implicitWidth: Kirigami.Units.iconSizes.small; implicitHeight: implicitWidth; color: Kirigami.Theme.highlightedTextColor }
            }
        }
        QQC2.Label {
            Layout.fillWidth: true
            // sin título, el nombre del archivo; si es «main.tex» (seis de cada nueve), el de su carpeta
            text: raiz.fila.titulo || raiz.nombreVisible((raiz.fila.relativa || raiz.fila.nombre || ""))
            font.weight: Font.Medium
            color: raiz.tinta
            elide: Text.ElideRight
            maximumLineCount: 2
            wrapMode: Text.Wrap
        }
        QQC2.Label {
            Layout.fillWidth: true
            text: raiz.fila.tipo + " · " + raiz.fila.hace
            font: Kirigami.Theme.smallFont
            color: raiz.tenue
            elide: Text.ElideRight
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing
            Rectangle { implicitWidth: Kirigami.Units.smallSpacing * 2; implicitHeight: implicitWidth; radius: width / 2; color: raiz.colorEstado }
            QQC2.Label {
                Layout.fillWidth: true
                text: raiz.fila.clave === "compilado" || !raiz.fila.problemas || raiz.fila.problemas === "—" || raiz.fila.problemas === "ninguno"
                      ? raiz.fila.estado : raiz.fila.problemas
                font: Kirigami.Theme.smallFont
                color: raiz.fila.nivel === "negativo" ? Kirigami.Theme.negativeTextColor : raiz.tinta
                elide: Text.ElideRight
            }
        }
    }
    QQC2.ToolTip.text: fila.relativa
    QQC2.ToolTip.visible: hovered
    QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay * 3
}
