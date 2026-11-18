// DialogoPlantillas — «Insertar una plantilla…» (Ctrl+Alt+T; decisiones §1.24, contrato §15; mejora C13.4): las plantillas
// que el marco declara para lo que más se repite (una tabla de regresión del paquete, una figura con su nota, su fuente y
// su texto alternativo, un cuadro con booktabs…). A la izquierda, la lista; a la derecha, su formulario corto, la línea
// tenue «por qué · fuente» y el texto que el marco compone, que se ve antes de ponerlo en el cursor. Nada se escribe en
// el disco: «Insertar» lo pone en el editor y el autor guarda con Ctrl+S.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.Dialog {
    id: dialogo
    signal insertar(string texto)
    readonly property var pl: studio.plantillas
    property var elegida: null
    property var valores: ({})
    property var compuesta: null                 // {insertar, avisos} o {error}

    title: "Insertar una plantilla"
    preferredWidth: Kirigami.Units.gridUnit * 48
    preferredHeight: Kirigami.Units.gridUnit * 34
    standardButtons: Kirigami.Dialog.NoButton
    padding: Kirigami.Units.largeSpacing

    property string pendiente: ""                 // la plantilla que se elige en cuanto llegue la lista
    function abrir(clave) { elegida = null; compuesta = null; valores = ({}); pendiente = clave || ""; pl.listar(); open() }
    function elegir(p) {
        elegida = p
        const v = {}
        for (const c of p.campos || []) v[c.clave] = c.omision !== undefined && c.omision !== null ? String(c.omision) : ""
        valores = v
        componer()
    }
    function poner(clave, texto) { const v = Object.assign({}, valores); v[clave] = texto; valores = v; pausa.restart() }
    function componer() { if (elegida) pl.componer(elegida.clave, valores) }
    Timer { id: pausa; interval: 300; onTriggered: dialogo.componer() }
    Connections {
        target: dialogo.pl
        function onCompuesta(r) { dialogo.compuesta = r }
        function onListaCambiada() {
            const p = dialogo.pendiente ? dialogo.pl.lista.find(x => x.clave === dialogo.pendiente) : null
            dialogo.pendiente = ""
            if (p) dialogo.elegir(p)
        }
    }

    footer: QQC2.ToolBar {
        position: QQC2.ToolBar.Footer
        padding: Kirigami.Units.largeSpacing
        background: Item {}
        RowLayout {
            anchors.fill: parent
            QQC2.Label {
                Layout.fillWidth: true
                text: "Se pone en el cursor; nada se escribe hasta que guardes."
                font: Kirigami.Theme.smallFont
                color: Kirigami.Theme.disabledTextColor
            }
            Chip { text: "Cerrar"; onClicked: dialogo.close() }
            Chip {
                text: "Insertar"; icono: "insert-text"; destacado: true
                enabled: !!dialogo.compuesta && !!dialogo.compuesta.insertar && !dialogo.compuesta.error
                opacity: enabled ? 1 : 0.5
                onClicked: { dialogo.insertar(dialogo.compuesta.insertar); dialogo.close() }
            }
        }
    }

    RowLayout {
        spacing: Kirigami.Units.largeSpacing
        QQC2.ScrollView {
            Layout.preferredWidth: Kirigami.Units.gridUnit * 15
            Layout.fillHeight: true
            ListView {
                id: lista
                clip: true
                model: dialogo.pl.lista
                delegate: QQC2.ItemDelegate {
                    required property var modelData
                    width: lista.width
                    highlighted: dialogo.elegida && dialogo.elegida.clave === modelData.clave
                    onClicked: dialogo.elegir(modelData)
                    contentItem: ColumnLayout {
                        spacing: 0
                        QQC2.Label { Layout.fillWidth: true; text: parent.parent.modelData.nombre; elide: Text.ElideRight; font.weight: Font.Medium }
                        QQC2.Label {
                            Layout.fillWidth: true
                            text: parent.parent.modelData.descripcion || ""
                            elide: Text.ElideRight
                            font: Kirigami.Theme.smallFont
                            color: Kirigami.Theme.disabledTextColor
                        }
                    }
                }
                Kirigami.PlaceholderMessage {
                    anchors.centerIn: parent
                    width: parent.width - Kirigami.Units.gridUnit
                    visible: lista.count === 0
                    text: dialogo.pl.error || "Leyendo las plantillas…"
                }
            }
        }
        Kirigami.Separator { Layout.fillHeight: true }
        QQC2.ScrollView {
            id: derecha
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            ColumnLayout {
                width: derecha.availableWidth
                spacing: Kirigami.Units.smallSpacing
                Kirigami.PlaceholderMessage {
                    Layout.fillWidth: true
                    visible: !dialogo.elegida
                    icon.name: "insert-table"
                    text: "Elige una plantilla"
                }
                Kirigami.Heading { level: 3; visible: !!dialogo.elegida; text: dialogo.elegida ? dialogo.elegida.nombre : "" }
                QQC2.Label {
                    Layout.fillWidth: true
                    visible: !!dialogo.elegida
                    wrapMode: Text.WordWrap
                    font: Kirigami.Theme.smallFont
                    color: Kirigami.Theme.disabledTextColor
                    text: dialogo.elegida ? [(dialogo.elegida.porque || "").replace(/\.$/, ""), dialogo.elegida.fuente].filter(x => !!x).join(" · ") : ""
                }
                Repeater {
                    model: dialogo.elegida ? dialogo.elegida.campos || [] : []
                    ColumnLayout {
                        id: campo
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 0
                        QQC2.Label { text: campo.modelData.rotulo + (campo.modelData.obligatorio ? "" : " (opcional)") }
                        QQC2.TextField {
                            Layout.fillWidth: true
                            visible: campo.modelData.tipo !== "opcion" && campo.modelData.tipo !== "lineas"
                            text: dialogo.valores[campo.modelData.clave] || ""
                            placeholderText: campo.modelData.ayuda || ""
                            Accessible.name: campo.modelData.rotulo
                            onTextEdited: dialogo.poner(campo.modelData.clave, text)
                        }
                        QQC2.TextArea {
                            Layout.fillWidth: true
                            Layout.minimumHeight: Kirigami.Units.gridUnit * 3
                            visible: campo.modelData.tipo === "lineas"
                            wrapMode: TextEdit.Wrap
                            text: dialogo.valores[campo.modelData.clave] || ""
                            placeholderText: campo.modelData.ayuda || ""
                            Accessible.name: campo.modelData.rotulo
                            onTextChanged: if (activeFocus) dialogo.poner(campo.modelData.clave, text)
                        }
                        QQC2.ComboBox {
                            Layout.fillWidth: true
                            visible: campo.modelData.tipo === "opcion"
                            model: (campo.modelData.opciones || []).map(o => o.nombre || o.clave || o)
                            Accessible.name: campo.modelData.rotulo
                            Component.onCompleted: {
                                const ops = campo.modelData.opciones || []
                                const i = ops.findIndex(o => (o.clave || o) === dialogo.valores[campo.modelData.clave])
                                currentIndex = i >= 0 ? i : 0
                                if (visible && ops.length && i < 0) dialogo.poner(campo.modelData.clave, ops[0].clave || ops[0])
                            }
                            onActivated: i => { const o = campo.modelData.opciones[i]; dialogo.poner(campo.modelData.clave, o.clave || o) }
                        }
                    }
                }
                Repeater {
                    model: dialogo.compuesta ? (dialogo.compuesta.avisos || []) : []
                    Kirigami.InlineMessage { required property string modelData; Layout.fillWidth: true; visible: true; type: Kirigami.MessageType.Warning; text: modelData }
                }
                Kirigami.InlineMessage {
                    Layout.fillWidth: true
                    visible: !!dialogo.compuesta && !!dialogo.compuesta.error
                    type: Kirigami.MessageType.Error
                    text: dialogo.compuesta ? dialogo.compuesta.error || "" : ""
                }
                QQC2.TextArea {
                    Layout.fillWidth: true
                    Layout.minimumHeight: Kirigami.Units.gridUnit * 7
                    visible: !!dialogo.compuesta && !!dialogo.compuesta.insertar
                    readOnly: true
                    text: dialogo.compuesta ? dialogo.compuesta.insertar || "" : ""
                    font.family: Kirigami.Theme.fixedWidthFont.family
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    wrapMode: TextEdit.NoWrap
                    Accessible.name: "Lo que se insertará"
                }
            }
        }
    }
}
