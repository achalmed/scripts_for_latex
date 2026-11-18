// DialogoEntrega — «Antes de entregar» (Ctrl+Alt+E; decisiones §1.21, contrato §12): los controles que el marco revisa
// antes de entregar el documento abierto (studio.entrega.resultado). Arriba, el veredicto: «Listo para entregar» o
// «Faltan N» (las fallas más los puntos manuales sin marcar; los avisos no bloquean). Cada control, en su grupo, con su
// punto de color, su línea tenue «por qué · fuente» y sus hallazgos: un clic lleva al archivo y la línea en el editor.
// Los puntos manuales tienen casilla y nota: sin casilla y con nota quedan justificados. La única acción rellena es
// «Revisar de nuevo»; la ventana no sabe qué es cada control: lo dice el marco.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.Dialog {
    id: dialogo
    readonly property var e: studio.entrega
    readonly property var r: e.resultado
    readonly property int visibles: 5             // los hallazgos de un control que se ven sin desplegarlo

    title: "Antes de entregar"
    preferredWidth: Kirigami.Units.gridUnit * 46
    preferredHeight: Kirigami.Units.gridUnit * 40
    standardButtons: Kirigami.Dialog.NoButton
    padding: Kirigami.Units.largeSpacing

    function abrir() { e.revisar(); open() }
    function colorDe(c) {
        if (c.estado === "falla") return Kirigami.Theme.negativeTextColor
        if (c.estado === "aviso") return Kirigami.Theme.neutralTextColor
        if (c.estado === "ok" || c.marcado) return Kirigami.Theme.positiveTextColor
        return Kirigami.Theme.disabledTextColor                         // manual sin marcar
    }
    function delGrupo(clave) { return (r.controles || []).filter(c => c.grupo === clave) }
    function resumen() {
        const partes = []
        if (r.fallas) partes.push(r.fallas + (r.fallas === 1 ? " falla" : " fallas"))
        if (r.pendientes) partes.push(r.pendientes + (r.pendientes === 1 ? " punto sin marcar" : " puntos sin marcar"))
        if (r.avisos) partes.push(r.avisos + (r.avisos === 1 ? " aviso" : " avisos"))
        if (r.lista && r.lista.nombre) partes.push("lista: " + r.lista.nombre)
        return partes.join(" · ")
    }
    function ir(h) {
        if (!h.ruta) return
        dialogo.close()
        ventana.irA(h.ruta, h.linea)
    }

    footer: QQC2.ToolBar {
        position: QQC2.ToolBar.Footer
        padding: Kirigami.Units.largeSpacing
        background: Item {}
        RowLayout {
            anchors.fill: parent
            spacing: Kirigami.Units.smallSpacing
            QQC2.Label {
                Layout.fillWidth: true
                elide: Text.ElideRight
                font: Kirigami.Theme.smallFont
                color: Kirigami.Theme.disabledTextColor
                text: dialogo.e.revisando ? "Revisando…" : "Un clic en un hallazgo lo abre en el editor. Revisar no escribe nada."
            }
            Chip { text: "Cerrar"; onClicked: dialogo.close() }
            Chip {
                text: "Revisar de nuevo"; icono: "view-refresh"; destacado: true
                enabled: !dialogo.e.revisando
                opacity: enabled ? 1 : 0.5
                ayuda: "Vuelve a correr los controles del marco sobre lo guardado"
                onClicked: dialogo.e.revisar()
            }
        }
    }

    QQC2.ScrollView {
        id: vista
        contentWidth: availableWidth
        QQC2.ScrollBar.horizontal.policy: QQC2.ScrollBar.AlwaysOff
        ColumnLayout {
            width: vista.availableWidth
            spacing: Kirigami.Units.largeSpacing

            // --- el veredicto
            RowLayout {
                Layout.fillWidth: true
                visible: (dialogo.r.controles || []).length > 0
                spacing: Kirigami.Units.largeSpacing
                Rectangle {
                    implicitWidth: Kirigami.Units.gridUnit * 0.9
                    implicitHeight: implicitWidth
                    radius: width / 2
                    color: dialogo.r.listo ? Kirigami.Theme.positiveTextColor : dialogo.r.fallas ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.neutralTextColor
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    Kirigami.Heading {
                        level: 2
                        text: dialogo.r.listo ? "Listo para entregar" : "Faltan " + dialogo.r.faltan
                        Accessible.name: text
                    }
                    QQC2.Label {
                        Layout.fillWidth: true
                        text: dialogo.resumen()
                        elide: Text.ElideRight
                        color: Kirigami.Theme.disabledTextColor
                    }
                }
            }
            QQC2.BusyIndicator {
                Layout.alignment: Qt.AlignHCenter
                visible: dialogo.e.revisando && (dialogo.r.controles || []).length === 0
                running: visible
            }
            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: !!dialogo.r.error
                type: Kirigami.MessageType.Error
                text: dialogo.r.error || ""
            }

            // --- los grupos, con sus controles
            Repeater {
                model: dialogo.r.grupos || []
                ColumnLayout {
                    id: grupo
                    required property var modelData
                    readonly property var controles: dialogo.delGrupo(modelData.clave)
                    Layout.fillWidth: true
                    visible: controles.length > 0
                    spacing: Kirigami.Units.smallSpacing
                    Kirigami.Heading { level: 4; text: grupo.modelData.nombre; Layout.topMargin: Kirigami.Units.smallSpacing }

                    Repeater {
                        model: grupo.controles
                        ColumnLayout {
                            id: fila
                            required property var modelData
                            readonly property var c: modelData
                            readonly property bool manual: c.estado === "manual"
                            property bool desplegado: false
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing / 2

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Kirigami.Units.smallSpacing
                                Rectangle {                        // el punto de color: hueco si es manual sin marcar
                                    Layout.alignment: Qt.AlignVCenter
                                    implicitWidth: Kirigami.Units.gridUnit * 0.55
                                    implicitHeight: implicitWidth
                                    radius: width / 2
                                    color: fila.manual && !fila.c.marcado ? "transparent" : dialogo.colorDe(fila.c)
                                    border.width: fila.manual && !fila.c.marcado ? 1.5 : 0
                                    border.color: dialogo.colorDe(fila.c)
                                }
                                QQC2.CheckBox {
                                    id: casilla
                                    visible: fila.manual
                                    checked: fila.c.marcado === "hecho"
                                    enabled: dialogo.e.puedeMarcar
                                    text: fila.c.nombre
                                    Layout.fillWidth: true
                                    onToggled: dialogo.e.marcar(fila.c.id, checked, nota.text)
                                }
                                QQC2.Label {
                                    visible: !fila.manual
                                    Layout.fillWidth: true
                                    text: fila.c.nombre
                                    font.weight: Font.Medium
                                    wrapMode: Text.WordWrap
                                }
                                QQC2.Label {
                                    text: fila.c.detalle || ""
                                    visible: text !== ""
                                    Layout.maximumWidth: Kirigami.Units.gridUnit * 18
                                    elide: Text.ElideRight
                                    color: Kirigami.Theme.disabledTextColor
                                }
                            }
                            QQC2.Label {                               // por qué · fuente
                                Layout.fillWidth: true
                                Layout.leftMargin: Kirigami.Units.gridUnit
                                visible: text !== ""
                                text: [(fila.c.porque || "").replace(/\.$/, ""), fila.c.fuente].filter(x => !!x).join(" · ")
                                wrapMode: Text.WordWrap
                                font: Kirigami.Theme.smallFont
                                color: Kirigami.Theme.disabledTextColor
                            }
                            QQC2.TextField {
                                id: nota
                                visible: fila.manual
                                enabled: dialogo.e.puedeMarcar
                                Layout.fillWidth: true
                                Layout.leftMargin: Kirigami.Units.gridUnit
                                text: fila.c.nota || ""
                                placeholderText: "Nota, o por qué no aplica (sin casilla, queda justificado)"
                                Accessible.name: "Nota de «" + fila.c.nombre + "»"
                                onEditingFinished: if (text.trim() !== (fila.c.nota || "")) dialogo.e.marcar(fila.c.id, casilla.checked, text)
                            }
                            Repeater {
                                model: fila.desplegado ? fila.c.hallazgos : fila.c.hallazgos.slice(0, dialogo.visibles)
                                QQC2.ItemDelegate {
                                    id: hallazgo
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Layout.leftMargin: Kirigami.Units.gridUnit - leftPadding
                                    enabled: !!modelData.ruta
                                    Accessible.name: modelData.archivo + ", línea " + modelData.linea + ": " + modelData.texto
                                    onClicked: dialogo.ir(modelData)
                                    contentItem: RowLayout {
                                        spacing: Kirigami.Units.largeSpacing
                                        QQC2.Label {
                                            Layout.alignment: Qt.AlignTop
                                            Layout.preferredWidth: Kirigami.Units.gridUnit * 11
                                            text: hallazgo.modelData.archivo.split("/").pop() + (hallazgo.modelData.linea > 0 ? ":" + hallazgo.modelData.linea : "")
                                            elide: Text.ElideMiddle
                                            font.family: Kirigami.Theme.fixedWidthFont.family
                                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                                            color: Kirigami.Theme.disabledTextColor
                                        }
                                        QQC2.Label {
                                            Layout.fillWidth: true
                                            text: hallazgo.modelData.texto
                                            wrapMode: Text.WordWrap
                                            maximumLineCount: 3
                                            elide: Text.ElideRight
                                            font: Kirigami.Theme.smallFont
                                        }
                                    }
                                }
                            }
                            QQC2.Label {
                                visible: fila.c.hallazgos.length > dialogo.visibles
                                Layout.leftMargin: Kirigami.Units.gridUnit
                                text: fila.desplegado ? "Ver menos" : "Ver los " + fila.c.hallazgos.length
                                font: Kirigami.Theme.smallFont
                                color: Kirigami.Theme.linkColor
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: fila.desplegado = !fila.desplegado }
                            }
                        }
                    }
                }
            }
        }
    }
}
