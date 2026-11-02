// ListaProblemas — los errores y avisos del proyecto como errores presentables (R9): título comprensible, archivo y
// línea, causa probable y acción recomendada, y el detalle técnico (las líneas del registro) desplegable. Un clic o
// Intro va a la línea en el editor; F8 recorre. Filtros por nivel arriba. Componente candidato a gui-comun 3.0.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

ColumnLayout {
    id: raiz
    readonly property var c: studio.compilacion
    spacing: 0

    function icono(nivel) { return nivel === "error" ? "data-error" : nivel === "aviso" ? "data-warning" : "format-justify-fill" }
    function color(nivel) { return nivel === "error" ? Kirigami.Theme.negativeTextColor : nivel === "aviso" ? Kirigami.Theme.neutralTextColor : Kirigami.Theme.disabledTextColor }

    Connections { target: raiz.c; function onProblemasCambiados() { lista.currentIndex = raiz.c.problemaActual } }

    RowLayout {
        Layout.fillWidth: true
        Layout.margins: Kirigami.Units.smallSpacing
        spacing: Kirigami.Units.smallSpacing
        QQC2.ToolButton { checkable: true; checked: raiz.c.mostrarErrores; onToggled: raiz.c.mostrarErrores = checked; icon.name: "data-error"; text: raiz.c.nErrores; Accessible.name: "Errores: " + raiz.c.nErrores; QQC2.ToolTip.text: "Errores"; QQC2.ToolTip.visible: hovered }
        QQC2.ToolButton { checkable: true; checked: raiz.c.mostrarAvisos; onToggled: raiz.c.mostrarAvisos = checked; icon.name: "data-warning"; text: raiz.c.nAvisos; Accessible.name: "Avisos: " + raiz.c.nAvisos; QQC2.ToolTip.text: "Avisos"; QQC2.ToolTip.visible: hovered }
        QQC2.ToolButton { checkable: true; checked: raiz.c.mostrarTipografia; onToggled: raiz.c.mostrarTipografia = checked; icon.name: "format-justify-fill"; text: raiz.c.nTipografia; Accessible.name: "Tipografía: " + raiz.c.nTipografia; QQC2.ToolTip.text: "Avisos tipográficos (Overfull, Underfull)"; QQC2.ToolTip.visible: hovered }
        QQC2.Label { Layout.fillWidth: true; text: raiz.c.origenRegistro ? "de " + raiz.c.origenRegistro.split("/").pop() : ""; elide: Text.ElideMiddle; font: Kirigami.Theme.smallFont; color: Kirigami.Theme.disabledTextColor }
        QQC2.Button { text: "Revisar dependencias"; icon.name: "tools-check-spelling"; flat: true; enabled: studio.proyectos.hayAbierto; onClicked: raiz.c.revisarDependencias("") }
    }
    Kirigami.Separator { Layout.fillWidth: true }

    ListView {
        id: lista
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        model: raiz.c.problemas
        keyNavigationEnabled: true
        Accessible.name: "Problemas"
        QQC2.ScrollBar.vertical: QQC2.ScrollBar {}
        Keys.onReturnPressed: raiz.c.elegir(currentIndex)

        delegate: QQC2.ItemDelegate {
            id: fila
            required property var model
            required property int index
            property bool abierto: false
            width: lista.width
            highlighted: ListView.isCurrentItem
            onClicked: { lista.currentIndex = index; raiz.c.elegir(index) }
            Accessible.name: model.titulo + (model.linea ? ", línea " + model.linea : "")
            contentItem: RowLayout {
                spacing: Kirigami.Units.largeSpacing
                Kirigami.Icon { Layout.alignment: Qt.AlignTop; source: raiz.icono(fila.model.nivel); implicitWidth: Kirigami.Units.iconSizes.smallMedium; implicitHeight: implicitWidth }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing / 2
                    RowLayout {
                        Layout.fillWidth: true
                        QQC2.Label { text: fila.model.titulo; font.weight: Font.DemiBold; color: raiz.color(fila.model.nivel); elide: Text.ElideRight; Layout.fillWidth: true }
                        QQC2.Label { text: fila.model.relativa + (fila.model.linea ? ":" + fila.model.linea : ""); font.family: Kirigami.Theme.fixedWidthFont.family; font.pointSize: Kirigami.Theme.smallFont.pointSize; color: Kirigami.Theme.disabledTextColor }
                    }
                    QQC2.Label { visible: fila.model.causa !== ""; Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Causa probable: " + fila.model.causa }
                    QQC2.Label { visible: fila.model.accion !== ""; Layout.fillWidth: true; wrapMode: Text.WordWrap; text: "Qué hacer: " + fila.model.accion; color: Kirigami.Theme.textColor; font.italic: true }
                    QQC2.Label { visible: fila.model.titulo !== fila.model.mensaje; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere; text: fila.model.mensaje; font.family: Kirigami.Theme.fixedWidthFont.family; font.pointSize: Kirigami.Theme.smallFont.pointSize; color: Kirigami.Theme.disabledTextColor }
                    QQC2.Button {
                        visible: fila.model.detalle !== ""
                        flat: true
                        text: fila.abierto ? "Ocultar el detalle técnico" : "Detalle técnico"
                        icon.name: fila.abierto ? "arrow-up" : "arrow-down"
                        onClicked: fila.abierto = !fila.abierto
                    }
                    QQC2.Label {
                        visible: fila.abierto
                        Layout.fillWidth: true
                        text: fila.model.detalle
                        wrapMode: Text.WrapAnywhere
                        font.family: Kirigami.Theme.fixedWidthFont.family
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        textFormat: Text.PlainText
                    }
                }
            }
        }

        Kirigami.PlaceholderMessage {
            anchors.centerIn: parent
            width: parent.width - Kirigami.Units.gridUnit * 4
            visible: lista.count === 0
            icon.name: raiz.c.origenRegistro !== "" && raiz.c.nProblemas === 0 ? "data-success" : "data-information"
            text: !studio.proyectos.hayAbierto ? "Ningún proyecto abierto"
                  : raiz.c.origenRegistro === "" ? "Sin registro todavía" : raiz.c.nProblemas === 0 ? "Sin errores ni avisos" : "Todos los problemas están filtrados"
            explanation: studio.proyectos.hayAbierto && raiz.c.origenRegistro === "" ? "Compila (F5) para leer los errores y avisos con su archivo y su línea." : ""
        }
    }
}
