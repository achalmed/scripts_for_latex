// DialogoRubrica — «Autoevaluación con la rúbrica» (decisiones §1.22; contrato §12, `rubrica` y `autoevaluar`; mejora C11.2):
// antes de entregar, el autor puntúa cada criterio de la rúbrica que le toca (la del curso o la del tipo de documento, en
// el formato común) y justifica el puntaje con lo que se ve en el trabajo. Cada criterio: su nombre y su peso, sus
// niveles del mejor al peor con su descriptor (se elige uno), la justificación y «Guardar» (el clic es la confirmación;
// el marco lo escribe en el registro del proyecto). Arriba, la nota propia sobre 100 y lo que falta.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.Dialog {
    showCloseButton: false            // ya hay botones al pie: sin la × roja del encabezado
    id: dialogo
    readonly property var e: studio.entrega
    readonly property var r: e.rubrica

    title: "Autoevaluación" + (r.titulo ? ": " + r.titulo : "")
    preferredWidth: Kirigami.Units.gridUnit * 44
    preferredHeight: Kirigami.Units.gridUnit * 40
    standardButtons: Kirigami.Dialog.Close
    padding: Kirigami.Units.largeSpacing

    function abrir() { e.leerRubrica(); open() }

    Connections {
        target: dialogo.e
        function onAutoevaluado(d) {
            if (d.error) ventana.mensajes.mostrar(d.error, "aviso")
            else if (d.escrito) ventana.mensajes.mostrar("Autoevaluación guardada.", "positivo")
        }
    }

    QQC2.ScrollView {
        id: vista
        contentWidth: availableWidth
        QQC2.ScrollBar.horizontal.policy: QQC2.ScrollBar.AlwaysOff
        ColumnLayout {
            width: vista.availableWidth
            spacing: Kirigami.Units.largeSpacing

            RowLayout {
                Layout.fillWidth: true
                visible: !!dialogo.r.hay
                spacing: Kirigami.Units.largeSpacing
                Kirigami.Heading {
                    level: 2
                    text: dialogo.r.faltan ? (dialogo.r.faltan === 1 ? "Falta 1 criterio" : "Faltan " + dialogo.r.faltan + " criterios")
                          : dialogo.r.nota !== null && dialogo.r.nota !== undefined ? "Nota propia: " + dialogo.r.nota + " de 100" : ""
                }
                QQC2.Label {
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    color: (dialogo.r.vetos || []).length ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.disabledTextColor
                    text: ((dialogo.r.vetos || []).length ? "Veto en " + dialogo.r.vetos.join(", ") + " · " : "")
                          + (dialogo.r.origen === "proyecto" ? "La rúbrica del curso" : "La rúbrica del tipo de documento")
                }
            }
            QQC2.Label {                                       // por qué · fuente
                Layout.fillWidth: true
                visible: text !== ""
                wrapMode: Text.WordWrap
                font: Kirigami.Theme.smallFont
                color: Kirigami.Theme.disabledTextColor
                text: [(dialogo.r.porque || "").replace(/\.$/, ""), dialogo.r.fuente].filter(x => !!x).join(" · ")
            }
            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: dialogo.r.cambio === true
                type: Kirigami.MessageType.Warning
                text: "La rúbrica cambió desde que te autoevaluaste: revisa los puntajes."
            }
            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: !!dialogo.r.error
                type: Kirigami.MessageType.Error
                text: dialogo.r.error || ""
            }
            Kirigami.PlaceholderMessage {
                Layout.fillWidth: true
                visible: !dialogo.r.hay && !dialogo.r.error
                icon.name: "view-task-symbolic"
                text: "Este documento no tiene rúbrica"
                explanation: "Si es de un curso, el marco la toma del registro del proyecto (la del docente); si no, de su tipo."
            }

            Repeater {
                model: dialogo.r.criterios || []
                ColumnLayout {
                    id: criterio
                    required property var modelData
                    readonly property var c: modelData
                    property string elegido: c.puntaje
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Kirigami.Separator { Layout.fillWidth: true }
                    RowLayout {
                        Layout.fillWidth: true
                        Rectangle {
                            implicitWidth: Kirigami.Units.gridUnit * 0.55
                            implicitHeight: implicitWidth
                            radius: width / 2
                            color: criterio.c.puntaje ? Kirigami.Theme.positiveTextColor : "transparent"
                            border.width: criterio.c.puntaje ? 0 : 1.5
                            border.color: Kirigami.Theme.disabledTextColor
                        }
                        Kirigami.Heading { level: 4; text: criterio.c.nombre; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        QQC2.Label { text: "peso " + criterio.c.peso; color: Kirigami.Theme.disabledTextColor; font: Kirigami.Theme.smallFont }
                    }
                    QQC2.ButtonGroup { id: grupoNiveles }
                    Repeater {
                        model: criterio.c.niveles
                        QQC2.RadioButton {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.leftMargin: Kirigami.Units.gridUnit
                            QQC2.ButtonGroup.group: grupoNiveles
                            checked: criterio.elegido === modelData.texto
                            text: modelData.texto + (modelData.nombre ? " · " + modelData.nombre : "") + ": " + modelData.descriptor
                            onToggled: if (checked) criterio.elegido = modelData.texto
                            contentItem: QQC2.Label {
                                leftPadding: parent.indicator.width + parent.spacing
                                text: parent.text
                                wrapMode: Text.WordWrap
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }
                    QQC2.TextArea {
                        id: justificacion
                        Layout.fillWidth: true
                        Layout.leftMargin: Kirigami.Units.gridUnit
                        Layout.minimumHeight: Kirigami.Units.gridUnit * 3
                        wrapMode: TextEdit.Wrap
                        text: criterio.c.justificacion
                        placeholderText: "Por qué ese nivel: lo que se ve en el trabajo (sección, página, ejemplo)"
                        Accessible.name: "Justificación de «" + criterio.c.nombre + "»"
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: Kirigami.Units.gridUnit
                        QQC2.Label {
                            Layout.fillWidth: true
                            text: criterio.c.fecha ? "Guardado el " + criterio.c.fecha : ""
                            font: Kirigami.Theme.smallFont
                            color: Kirigami.Theme.disabledTextColor
                        }
                        QQC2.Button {
                            text: "Guardar"; icon.name: "document-save"
                            enabled: dialogo.e.puedeAutoevaluar && criterio.elegido !== ""
                                     && (criterio.elegido !== criterio.c.puntaje || justificacion.text.trim() !== criterio.c.justificacion)
                            opacity: enabled ? 1 : 0.5
                            onClicked: dialogo.e.autoevaluar(criterio.c.clave, criterio.elegido, justificacion.text)
                        }
                    }
                }
            }
        }
    }
}
