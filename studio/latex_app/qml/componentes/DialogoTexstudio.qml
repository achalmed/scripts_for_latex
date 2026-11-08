// DialogoTexstudio — muestra qué cambiaría en la configuración de otro programa para trabajar con LaTeX Studio y lo
// aplica o lo deshace solo al confirmar, con ese programa cerrado (al salir reescribe su configuración). Por omisión,
// TeXstudio («Compilar desde TeXstudio con LaTeX Studio…»: su «Compilar» corre studio/compilar.py, la receta de esta
// ventana); Main.qml lo usa también para Okular (Mayús+clic en el PDF vuelve al código aquí). Los datos y la escritura son
// de studio.sistema (latex_app/texstudio.py, latex_app/okular.py).
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.Dialog {
    id: dialogo
    property string programa: "TeXstudio"
    property var estadoDe: () => studio.sistema.estadoTexstudio()
    property var aplicarDe: () => studio.sistema.configurarTexstudio()
    property var deshacerDe: () => studio.sistema.deshacerTexstudio()
    property string explicacion: "Así cualquier documento abierto aquí compila igual desde TeXstudio: con el compilador de "
        + "su marco (docencia, escritura, marco_documental…), latexmk o LuaLaTeX + Biber, y su PDF y sus problemas aparecen "
        + "en esta ventana. Se cambian solo estas claves de "
    property string hecho: "Listo: «Compilar» de TeXstudio usa ahora la receta de LaTeX Studio."
    property string yaEsta: "TeXstudio ya compila con LaTeX Studio: F5 y F6 corren la misma receta que esta ventana."
    property var estado: ({ instalado: false, abierto: false, existe: false, configurado: false, ini: "", enlace: "", orden: "", cambios: [] })
    title: "Compilar desde TeXstudio con LaTeX Studio"
    preferredWidth: Kirigami.Units.gridUnit * 44
    standardButtons: Kirigami.Dialog.Close
    padding: Kirigami.Units.largeSpacing

    function abrir() {
        dialogo.estado = dialogo.estadoDe()
        dialogo.open()
    }
    function hecha(error, aviso) {
        if (error) { ventana.mensajes.mostrar(error, "error"); dialogo.estado = dialogo.estadoDe(); return }
        ventana.mensajes.mostrar(aviso, "positivo")
        dialogo.close()
    }

    customFooterActions: [
        Kirigami.Action {
            text: "Actualizar"; icon.name: "view-refresh"
            tooltip: "Volver a mirar si " + dialogo.programa + " está abierto y su configuración"
            onTriggered: dialogo.estado = dialogo.estadoDe()
        },
        Kirigami.Action {
            text: "Deshacer"; icon.name: "edit-undo"
            enabled: dialogo.estado.instalado && !dialogo.estado.abierto
            tooltip: "Restaurar la configuración de " + dialogo.programa + " anterior al último cambio"
            onTriggered: dialogo.hecha(dialogo.deshacerDe(), dialogo.programa + " vuelve a su configuración anterior.")
        },
        Kirigami.Action {
            text: "Aplicar"; icon.name: "dialog-ok-apply"
            enabled: dialogo.estado.instalado && dialogo.estado.existe && !dialogo.estado.abierto && dialogo.estado.cambios.length > 0
            onTriggered: dialogo.hecha(dialogo.aplicarDe(), dialogo.hecho)
        }
    ]

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: !dialogo.estado.instalado
            type: Kirigami.MessageType.Error
            text: dialogo.programa + " no está instalado."
        }
        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: dialogo.estado.instalado && dialogo.estado.abierto
            type: Kirigami.MessageType.Warning
            text: dialogo.programa + " está abierto. Ciérralo y pulsa «Actualizar»: al salir reescribe su configuración y se perdería el cambio."
        }
        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: dialogo.estado.instalado && !dialogo.estado.existe
            type: Kirigami.MessageType.Warning
            text: dialogo.programa + " aún no tiene configuración: ábrelo y ciérralo una vez, y pulsa «Actualizar»."
        }
        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: dialogo.estado.enlace !== ""
            type: Kirigami.MessageType.Information
            text: "La configuración de " + dialogo.programa + " es un enlace a " + dialogo.estado.enlace + ": el cambio queda en ese archivo (el enlace se conserva)."
        }
        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: dialogo.estado.configurado
            type: Kirigami.MessageType.Positive
            text: dialogo.yaEsta
        }
        QQC2.Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: dialogo.explicacion + dialogo.estado.ini + " (se guarda un respaldo al lado):"
        }
        Repeater {
            model: dialogo.estado.cambios
            delegate: ColumnLayout {
                required property var modelData
                Layout.fillWidth: true
                spacing: 0
                QQC2.Label { text: modelData.clave; font.bold: true }
                QQC2.Label {
                    Layout.fillWidth: true
                    wrapMode: Text.WrapAnywhere
                    font.family: Kirigami.Theme.fixedWidthFont.family
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    text: "− " + (modelData.actual || "(sin valor)") + "\n+ " + modelData.nuevo
                }
            }
        }
    }
}
