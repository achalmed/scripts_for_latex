// DialogoMatriz — «Matriz de consistencia» (Ctrl+Alt+M; decisiones §1.22, contrato §13): la matriz viva del proyecto
// abierto, fila por fila (general y específicas): problema, objetivo e hipótesis; debajo, en una línea tenue, la evidencia
// que la refutaría y el supuesto que cuestiona; los indicadores y la sección donde se contrasta (un clic lleva a ella).
// Arriba, el veredicto: «Nada huérfano» o cuántos elementos huérfanos. Lo huérfano de cada fila, con su punto de color.
// Acciones: el asistente de pregunta, editar matriz.yml en el editor y generar el cuadro (lo escribe el marco). La
// ventana no sabe qué es una hipótesis: pinta lo que el marco devuelve.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.Dialog {
    id: dialogo
    readonly property var m: studio.matriz
    readonly property var r: m.resultado

    title: m.nombre
    preferredWidth: Kirigami.Units.gridUnit * 50
    preferredHeight: Kirigami.Units.gridUnit * 40
    standardButtons: Kirigami.Dialog.NoButton
    padding: Kirigami.Units.largeSpacing

    function abrir() { m.leer(); open() }
    function colorDe(estado) {
        return estado === "falla" ? Kirigami.Theme.negativeTextColor : estado === "aviso" ? Kirigami.Theme.neutralTextColor : Kirigami.Theme.positiveTextColor
    }
    function ir(ruta, linea) { if (!ruta) return; dialogo.close(); ventana.irA(ruta, linea) }
    function tenue(porque, fuente) { return [(porque || "").replace(/\.$/, ""), fuente].filter(x => !!x).join(" · ") }

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
                text: dialogo.m.leyendo ? "Leyendo…" : dialogo.tenue(dialogo.r.porque, dialogo.r.fuente)
            }
            Chip { text: "Cerrar"; onClicked: dialogo.close() }
            Chip {
                text: "Asistente de pregunta"; icono: "help-hint"
                visible: !!dialogo.m.puede.pregunta
                ayuda: "De un tema a una pregunta en cuatro pasos; se guarda en la matriz"
                onClicked: { dialogo.close(); dialogoPregunta.abrir() }
            }
            Chip {
                text: "Editar matriz.yml"; icono: "document-edit"
                visible: dialogo.r.existe
                onClicked: dialogo.ir(dialogo.r.ruta, 1)
            }
            Chip {
                text: "Crear la matriz"; icono: "document-new"; destacado: true
                visible: !dialogo.r.existe && !!dialogo.m.puede.nueva && !dialogo.m.leyendo
                ayuda: "Un matriz.yml con su forma, para llenarlo en el editor o con el asistente"
                onClicked: dialogo.m.crear()
            }
            Chip {
                text: dialogo.r.cuadro && dialogo.r.cuadro.al_dia ? "Cuadro al día" : "Generar el cuadro"; icono: "insert-table"; destacado: true
                visible: dialogo.r.existe && !!dialogo.m.puede.cuadro
                enabled: !(dialogo.r.cuadro && dialogo.r.cuadro.al_dia) && !dialogo.m.leyendo
                opacity: enabled ? 1 : 0.5
                ayuda: "Escribe " + (dialogo.r.cuadro ? dialogo.r.cuadro.archivo || "el cuadro" : "el cuadro") + " desde la matriz (no pisa uno escrito a mano)"
                onClicked: dialogo.m.generarCuadro()
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
                visible: dialogo.r.existe
                spacing: Kirigami.Units.largeSpacing
                Rectangle {
                    implicitWidth: Kirigami.Units.gridUnit * 0.9
                    implicitHeight: implicitWidth
                    radius: width / 2
                    color: dialogo.colorDe(dialogo.r.fallas ? "falla" : dialogo.r.avisos ? "aviso" : "ok")
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    Kirigami.Heading {
                        level: 2
                        text: dialogo.r.no_aplica ? "No aplica" : dialogo.r.fallas ? (dialogo.r.fallas === 1 ? "1 elemento huérfano" : dialogo.r.fallas + " elementos huérfanos") : "Nada huérfano"
                    }
                    QQC2.Label {
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                        color: Kirigami.Theme.disabledTextColor
                        text: dialogo.r.no_aplica || ((dialogo.r.filas || []).length + ((dialogo.r.filas || []).length === 1 ? " fila" : " filas")
                              + (dialogo.r.avisos ? " · " + dialogo.r.avisos + (dialogo.r.avisos === 1 ? " aviso" : " avisos") : "")
                              + (dialogo.r.pregunta && dialogo.r.pregunta.texto ? " · " + dialogo.r.pregunta.texto : ""))
                    }
                }
            }
            Kirigami.PlaceholderMessage {
                Layout.fillWidth: true
                visible: !dialogo.r.existe && !dialogo.m.leyendo && !dialogo.r.error
                icon.name: "view-list-details"
                text: "El proyecto no tiene matriz de consistencia"
                explanation: "Créala o empieza por el asistente de pregunta: cada hipótesis tendrá su indicador y su sección, y lo huérfano se verá aquí y en «Antes de entregar»."
            }
            QQC2.BusyIndicator { Layout.alignment: Qt.AlignHCenter; visible: dialogo.m.leyendo && !dialogo.r.existe; running: visible }
            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: !!dialogo.r.error
                type: Kirigami.MessageType.Error
                text: dialogo.r.error || ""
            }

            // --- las filas
            Repeater {
                model: dialogo.r.filas || []
                ColumnLayout {
                    id: fila
                    required property var modelData
                    readonly property var f: modelData
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Kirigami.Separator { Layout.fillWidth: true }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing
                        Rectangle {
                            implicitWidth: Kirigami.Units.gridUnit * 0.55
                            implicitHeight: implicitWidth
                            radius: width / 2
                            color: dialogo.colorDe(fila.f.estado)
                        }
                        Kirigami.Heading {
                            Layout.fillWidth: true
                            level: 4
                            text: (fila.f.nivel === "general" ? "General" : "Específica") + " · " + fila.f.id
                        }
                        QQC2.ToolButton {
                            icon.name: "document-edit"; display: QQC2.AbstractButton.IconOnly
                            text: "Editar la fila en matriz.yml"
                            QQC2.ToolTip.text: text; QQC2.ToolTip.visible: hovered
                            onClicked: dialogo.ir(dialogo.r.ruta, fila.f.linea || 1)
                        }
                    }
                    GridLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: Kirigami.Units.gridUnit
                        columns: 2
                        columnSpacing: Kirigami.Units.largeSpacing
                        rowSpacing: Kirigami.Units.smallSpacing
                        Repeater {
                            model: [["Problema", fila.f.problema], ["Objetivo", fila.f.objetivo], ["Hipótesis", fila.f.hipotesis]]
                            delegate: Item {
                                required property var modelData
                                Layout.columnSpan: 2
                                Layout.fillWidth: true
                                implicitHeight: par.implicitHeight
                                RowLayout {
                                    id: par
                                    width: parent.width
                                    spacing: Kirigami.Units.largeSpacing
                                    QQC2.Label {
                                        Layout.preferredWidth: Kirigami.Units.gridUnit * 6
                                        Layout.alignment: Qt.AlignTop
                                        text: modelData[0]
                                        color: Kirigami.Theme.disabledTextColor
                                    }
                                    QQC2.Label {
                                        Layout.fillWidth: true
                                        text: modelData[1] || "Sin escribir"
                                        wrapMode: Text.WordWrap
                                        color: modelData[1] ? Kirigami.Theme.textColor : Kirigami.Theme.disabledTextColor
                                        font.italic: !modelData[1]
                                    }
                                }
                            }
                        }
                    }
                    QQC2.Label {                               // C1.3: lo que la refutaría y el supuesto que cuestiona
                        Layout.fillWidth: true
                        Layout.leftMargin: Kirigami.Units.gridUnit
                        visible: fila.f.hipotesis !== ""
                        wrapMode: Text.WordWrap
                        font: Kirigami.Theme.smallFont
                        color: Kirigami.Theme.disabledTextColor
                        text: "Se refutaría si: " + (fila.f.refutaria || "sin escribir") + " · Supuesto que cuestiona: " + (fila.f.supuesto || "sin escribir")
                    }
                    ColumnLayout {                             // indicadores y secciones, uno por línea
                        Layout.fillWidth: true
                        Layout.leftMargin: Kirigami.Units.gridUnit
                        spacing: 0
                        Repeater {
                            model: fila.f.indicadores
                            QQC2.Label {
                                required property var modelData
                                text: "Indicador: " + (modelData.nombre || modelData.ref)
                                font: Kirigami.Theme.smallFont
                                color: modelData.existe === false ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.textColor
                                QQC2.ToolTip.text: modelData.ref + (modelData.detalle ? ": " + modelData.detalle : "")
                                QQC2.ToolTip.visible: hoverIndicador.hovered
                                HoverHandler { id: hoverIndicador }
                            }
                        }
                        Repeater {
                            model: fila.f.secciones
                            QQC2.Label {
                                required property var modelData
                                text: "Sección: " + modelData.ref + (modelData.existe ? "" : " (no existe)")
                                font: Kirigami.Theme.smallFont
                                color: modelData.existe ? Kirigami.Theme.linkColor : Kirigami.Theme.negativeTextColor
                                MouseArea {
                                    anchors.fill: parent
                                    enabled: !!parent.modelData.ruta
                                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                    onClicked: dialogo.ir(parent.modelData.ruta, parent.modelData.linea)
                                }
                            }
                        }
                    }
                    Repeater {                                 // lo huérfano de la fila
                        model: fila.f.problemas
                        RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.leftMargin: Kirigami.Units.gridUnit
                            spacing: Kirigami.Units.smallSpacing
                            Rectangle {
                                Layout.alignment: Qt.AlignVCenter
                                implicitWidth: Kirigami.Units.gridUnit * 0.4
                                implicitHeight: implicitWidth
                                radius: width / 2
                                color: dialogo.colorDe(modelData.estado)
                            }
                            QQC2.Label {
                                Layout.fillWidth: true
                                text: modelData.texto.replace(fila.f.id + ": ", "")
                                wrapMode: Text.WordWrap
                                font: Kirigami.Theme.smallFont
                            }
                        }
                    }
                }
            }
            QQC2.Label {                                       // por qué · fuente de las columnas nuevas (C1.3)
                Layout.fillWidth: true
                visible: (dialogo.r.filas || []).length > 0
                wrapMode: Text.WordWrap
                font: Kirigami.Theme.smallFont
                color: Kirigami.Theme.disabledTextColor
                text: (dialogo.r.columnas || []).filter(c => c.clave === "refutaria" || c.clave === "supuesto")
                      .map(c => c.nombre + ": " + dialogo.tenue(c.porque, c.fuente)).join("  ·  ")
            }
        }
    }
}
