// RevisionEditor — la pestaña «Revisión» del panel inferior (decisiones §1.23, contrato §14): el estilo de la redacción y el
// LaTeX del archivo abierto, según las reglas que declara el marco. Cada hallazgo: su línea, la regla, lo hallado, qué
// considerar y la línea tenue «por qué · fuente»; un clic lleva a la línea. Se pone al día al guardar y con «Revisar»
// (Ctrl+Alt+R). Sugiere y nunca reescribe: nada de aquí cambia el texto.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

ColumnLayout {
    id: raiz
    readonly property var r: studio.revisor.resultado
    property string clase: ""                      // "" todas · estilo · latex
    readonly property var visibles: (r.hallazgos || []).filter(h => raiz.clase === "" || h.clase === raiz.clase)
    spacing: 0

    function revisar() {
        const e = ventana.editor()
        if (e) studio.revisor.revisar(e.ruta, e.area.text)
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.margins: Kirigami.Units.smallSpacing
        spacing: Kirigami.Units.smallSpacing
        // la clase de hallazgos: una entre tres, el selector segmentado de la base
        SelectorSegmentado {
            titulo: "Clase de hallazgos"
            compacto: true
            opciones: [{ clave: "todo", texto: "Todo", contador: (raiz.r.hallazgos || []).length },
                       { clave: "estilo", texto: "Estilo", contador: raiz.r.estilo || 0 },
                       { clave: "latex", texto: "LaTeX", contador: raiz.r.latex || 0 }]
            actual: raiz.clase === "" ? "todo" : raiz.clase
            onElegida: clave => raiz.clase = clave === "todo" ? "" : clave
        }
        QQC2.Label {
            Layout.fillWidth: true
            elide: Text.ElideMiddle
            font: Kirigami.Theme.smallFont
            color: Kirigami.Theme.disabledTextColor
            text: studio.revisor.revisando ? "Revisando…"
                  : studio.revisor.ruta ? studio.revisor.ruta.split("/").pop() + (raiz.r.perfil && raiz.r.perfil.nombre ? " · lector: " + raiz.r.perfil.nombre : "") + " · sugiere, no cambia nada"
                  : ""
        }
        QQC2.Button {
            text: "Revisar"; icon.name: "tools-check-spelling"; flat: true
            enabled: studio.revisor.disponible && !!ventana.editor() && !studio.revisor.revisando
            QQC2.ToolTip.text: "El archivo abierto, con lo que aún no guardaste (Ctrl+Alt+R)"
            QQC2.ToolTip.visible: hovered
            onClicked: raiz.revisar()
        }
    }
    Kirigami.InlineMessage {
        Layout.fillWidth: true
        visible: !!raiz.r.error
        type: Kirigami.MessageType.Warning
        text: raiz.r.error || ""
    }
    QQC2.ScrollView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        ListView {
            id: lista
            clip: true
            model: raiz.visibles
            Kirigami.PlaceholderMessage {
                anchors.centerIn: parent
                width: parent.width - Kirigami.Units.gridUnit * 4
                visible: lista.count === 0
                icon.name: studio.revisor.ruta && !raiz.r.error ? "checkmark-symbolic" : "dialog-information-symbolic"
                text: !studio.revisor.disponible ? "El marco del proyecto no declara un revisor"
                      : !studio.revisor.ruta ? "Sin revisar todavía" : "Nada que sugerir"
                explanation: studio.revisor.disponible && !studio.revisor.ruta ? "Guarda el archivo o pulsa «Revisar» (Ctrl+Alt+R)." : ""
            }
            delegate: QQC2.ItemDelegate {
                id: fila
                required property var modelData
                width: lista.width
                Accessible.name: "Línea " + modelData.linea + ", " + modelData.nombre + ": " + modelData.texto
                onClicked: ventana.irA(studio.revisor.ruta, modelData.linea)
                contentItem: RowLayout {
                    spacing: Kirigami.Units.largeSpacing
                    QQC2.Label {
                        Layout.alignment: Qt.AlignTop
                        Layout.preferredWidth: Kirigami.Units.gridUnit * 3
                        text: fila.modelData.linea > 0 ? ":" + fila.modelData.linea : ""
                        font.family: Kirigami.Theme.fixedWidthFont.family
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        color: Kirigami.Theme.disabledTextColor
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        QQC2.Label {
                            Layout.fillWidth: true
                            text: fila.modelData.nombre + (fila.modelData.texto ? ": «" + fila.modelData.texto + "»" : "")
                            elide: Text.ElideRight
                            font.weight: Font.Medium
                        }
                        QQC2.Label {
                            Layout.fillWidth: true
                            visible: text !== ""
                            text: fila.modelData.sugerencia
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                            font: Kirigami.Theme.smallFont
                        }
                        QQC2.Label {                       // por qué · fuente
                            Layout.fillWidth: true
                            visible: text !== ""
                            text: [(fila.modelData.porque || "").replace(/\.$/, ""), fila.modelData.fuente].filter(x => !!x).join(" · ")
                            wrapMode: Text.WordWrap
                            font: Kirigami.Theme.smallFont
                            color: Kirigami.Theme.disabledTextColor
                        }
                    }
                }
            }
        }
    }
}
