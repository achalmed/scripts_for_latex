// RegistroCompilacion — el registro íntegro de la última compilación del proyecto abierto (el --log de main.sh, o el
// .log del motor en la carpeta de auxiliares del marco o de latexmk), monoespaciado y de solo lectura.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

ColumnLayout {
    readonly property var c: studio.compilacion
    spacing: 0
    QQC2.Label {
        visible: c.origenRegistro !== ""
        Layout.fillWidth: true
        Layout.margins: Kirigami.Units.smallSpacing
        text: c.origenRegistro
        elide: Text.ElideMiddle
        font: Kirigami.Theme.smallFont
        color: Kirigami.Theme.disabledTextColor
    }
    VistaTexto {
        Layout.fillWidth: true
        Layout.fillHeight: true
        texto: c.registro
        mensajeVacio: studio.proyectos.hayAbierto ? "Sin registro todavía: compila el proyecto (F5)" : "Ningún proyecto abierto"
        iconoVacio: "text-x-log"
        nombreAccesible: "Registro de la compilación"
    }
}
