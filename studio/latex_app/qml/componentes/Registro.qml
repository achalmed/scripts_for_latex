// Registro — la salida íntegra de la última corrida del documento actual (el --log de main.sh en la caché del studio, o
// el .log que el motor dejó junto al .tex si una corrida falló fuera de la ventana), monoespaciada, solo lectura.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

ColumnLayout {
    readonly property var d: studio.documentos
    spacing: 0
    QQC2.Label {
        visible: d.origenProblemas !== "" && d.registro !== ""
        Layout.fillWidth: true
        Layout.margins: Kirigami.Units.largeSpacing
        text: d.origenProblemas
        elide: Text.ElideMiddle
        font: Kirigami.Theme.smallFont
        color: Kirigami.Theme.disabledTextColor
    }
    VistaTexto {
        Layout.fillWidth: true
        Layout.fillHeight: true
        texto: d.registro
        mensajeVacio: !d.hayActual ? "Ningún documento" : "Sin registro todavía: compila el documento (F5); la salida íntegra del motor, Biber y los índices queda aquí"
        iconoVacio: "text-x-log"
        nombreAccesible: "Registro de " + (d.nombre || "ningún documento")
    }
}
