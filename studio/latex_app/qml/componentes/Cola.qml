// Cola — la cola de compilación (R15): lo compilado en esta sesión, lo que compila ahora y lo pendiente, cada uno con
// su resultado; Detener vacía la cola y para la compilación en curso.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

ColumnLayout {
    id: raiz
    readonly property var c: studio.compilacion
    spacing: 0
    RowLayout {
        Layout.fillWidth: true
        Layout.margins: Kirigami.Units.smallSpacing
        QQC2.Label { Layout.fillWidth: true; text: raiz.c.enCurso ? "Compilando " + raiz.c.rutaEnCurso.split("/").pop() + (raiz.c.enCola ? " · " + raiz.c.enCola + " en cola" : "") : (raiz.c.enCola ? raiz.c.enCola + " en cola" : "Sin compilaciones en cola"); elide: Text.ElideRight }
        QQC2.Button { text: "Detener"; icon.name: "process-stop"; enabled: raiz.c.enCurso || raiz.c.enCola > 0; onClicked: raiz.c.cancelar() }
    }
    Kirigami.Separator { Layout.fillWidth: true }
    ListView {
        id: lista
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        model: raiz.c.cola
        Accessible.name: "Cola de compilación"
        QQC2.ScrollBar.vertical: QQC2.ScrollBar {}
        delegate: QQC2.ItemDelegate {
            required property var model
            width: lista.width
            icon.name: model.icono
            text: model.nombre + " — " + model.estado + (model.detalle ? " · " + model.detalle : "")
            onDoubleClicked: studio.interfaz.pedir("abrir_proyecto", { ruta: model.ruta })
            QQC2.ToolTip.text: model.ruta
            QQC2.ToolTip.visible: hovered
            QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
        }
        Kirigami.PlaceholderMessage {
            anchors.centerIn: parent
            visible: lista.count === 0
            text: "La cola está vacía"
            explanation: "Marca varios proyectos en la página de proyectos y pulsa Compilar (Ctrl+Mayús+F5)."
        }
    }
}
