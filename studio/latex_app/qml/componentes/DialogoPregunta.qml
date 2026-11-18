// DialogoPregunta — «Asistente de pregunta» (decisiones §1.22, contrato §13 `guia` y `pregunta`): de un tema a una
// pregunta en cuatro pasos, como ventana: el tema, el rompecabezas o hecho estilizado, la pregunta delimitada (población,
// periodo, comparación) y la evidencia que la contestaría. Cada paso trae su pregunta, su ayuda, un ejemplo de economía
// peruana y la línea tenue «por qué · fuente», que da el marco. Al final, «Revisar» muestra los avisos del marco sin
// escribir y «Guardar en la matriz» la escribe (con copia). Lo ya guardado se carga para seguir.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.Dialog {
    id: dialogo
    readonly property var m: studio.matriz
    readonly property var pasos: (m.guia && m.guia.pasos) || []
    property int paso: 0
    property var valores: ({})
    property var revision: null                  // {ok, avisos} de `pregunta` sin --aplicar
    property bool esperando: false

    title: (m.guia && m.guia.titulo) || "Asistente de pregunta"
    preferredWidth: Kirigami.Units.gridUnit * 38
    preferredHeight: Kirigami.Units.gridUnit * 32
    standardButtons: Kirigami.Dialog.NoButton
    padding: Kirigami.Units.largeSpacing

    // `datos` (opcional): {valores, paso, revisar}, para retomar donde se quedó (y para las capturas)
    function abrir(datos) {
        datos = datos || {}
        paso = datos.paso || 0; revision = null; esperando = false
        const previa = datos.valores || (m.resultado && m.resultado.pregunta) || {}
        const v = {}
        for (const k in previa) v[k] = previa[k] || ""
        valores = v
        if (!m.resultado.existe && !m.leyendo) m.leer()
        if (!pasos.length) m.pedirGuia()
        if (datos.revisar) { esperando = true; m.pregunta(valores, false) }
        open()
    }
    function poner(clave, texto) { const v = Object.assign({}, valores); v[clave] = texto; valores = v; revision = null }
    function completo(p) { return (p.campos || []).every(c => !c.obligatorio || (valores[c.clave] || "").trim() !== "") }
    readonly property var actual: pasos.length ? pasos[paso] : null
    readonly property bool ultimo: paso === pasos.length - 1

    Connections {
        target: dialogo.m
        function onPreguntaRevisada(r) { dialogo.esperando = false; dialogo.revision = r }
        function onPreguntaGuardada(r) {
            dialogo.esperando = false
            if (r.escrito) { ventana.mensajes.mostrar("Pregunta guardada en " + (r.archivo || "la matriz") + ".", "positivo"); dialogo.close() }
            else dialogo.revision = r
        }
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
                text: dialogo.pasos.length ? "Paso " + (dialogo.paso + 1) + " de " + dialogo.pasos.length : ""
                color: Kirigami.Theme.disabledTextColor
                font: Kirigami.Theme.smallFont
            }
            Chip { text: "Cerrar"; onClicked: dialogo.close() }
            Chip { text: "Atrás"; icono: "go-previous"; visible: dialogo.paso > 0; onClicked: { dialogo.paso -= 1; dialogo.revision = null } }
            Chip {
                text: "Siguiente"; icono: "go-next"; destacado: true
                visible: !dialogo.ultimo && dialogo.pasos.length > 0
                enabled: !!dialogo.actual && dialogo.completo(dialogo.actual)
                opacity: enabled ? 1 : 0.5
                onClicked: dialogo.paso += 1
            }
            Chip {
                text: "Revisar"; icono: "tools-check-spelling"
                visible: dialogo.ultimo
                enabled: !dialogo.esperando
                ayuda: "Los avisos del marco sobre lo escrito; no escribe nada"
                onClicked: { dialogo.esperando = true; dialogo.m.pregunta(dialogo.valores, false) }
            }
            Chip {
                text: "Guardar en la matriz"; icono: "document-save"; destacado: true
                visible: dialogo.ultimo
                enabled: !dialogo.esperando && !!dialogo.revision && dialogo.revision.ok === true
                opacity: enabled ? 1 : 0.5
                ayuda: "Escribe la pregunta en matriz.yml (con copia .bak); revisa antes"
                onClicked: { dialogo.esperando = true; dialogo.m.pregunta(dialogo.valores, true) }
            }
        }
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing
        QQC2.BusyIndicator { Layout.alignment: Qt.AlignHCenter; visible: !dialogo.actual; running: visible }

        // --- los pasos, como una línea de texto (el actual, en negrita)
        QQC2.Label {
            Layout.fillWidth: true
            visible: dialogo.pasos.length > 0
            textFormat: Text.StyledText
            wrapMode: Text.WordWrap
            color: Kirigami.Theme.disabledTextColor
            text: dialogo.pasos.map((p, i) => i === dialogo.paso ? "<b>" + (i + 1) + ". " + p.titulo + "</b>" : (i + 1) + ". " + p.titulo).join("   ")
        }
        Kirigami.Heading { level: 2; text: dialogo.actual ? dialogo.actual.pregunta : ""; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        QQC2.Label {
            Layout.fillWidth: true
            text: dialogo.actual ? dialogo.actual.ayuda : ""
            wrapMode: Text.WordWrap
        }
        QQC2.Label {                                       // por qué · fuente
            Layout.fillWidth: true
            visible: !!dialogo.actual
            text: dialogo.actual ? [(dialogo.actual.porque || "").replace(/\.$/, ""), dialogo.actual.fuente].filter(x => !!x).join(" · ") : ""
            wrapMode: Text.WordWrap
            font: Kirigami.Theme.smallFont
            color: Kirigami.Theme.disabledTextColor
        }

        // --- los campos del paso
        Repeater {
            model: dialogo.actual ? dialogo.actual.campos : []
            ColumnLayout {
                id: campo
                required property var modelData
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing / 2
                QQC2.Label { text: campo.modelData.rotulo + (campo.modelData.obligatorio ? "" : " (opcional)"); font.weight: Font.Medium }
                QQC2.TextField {
                    Layout.fillWidth: true
                    visible: campo.modelData.tipo !== "lineas"
                    text: dialogo.valores[campo.modelData.clave] || ""
                    Accessible.name: campo.modelData.rotulo
                    onTextEdited: dialogo.poner(campo.modelData.clave, text)
                }
                QQC2.TextArea {
                    Layout.fillWidth: true
                    Layout.minimumHeight: Kirigami.Units.gridUnit * 4
                    visible: campo.modelData.tipo === "lineas"
                    wrapMode: TextEdit.Wrap
                    text: dialogo.valores[campo.modelData.clave] || ""
                    Accessible.name: campo.modelData.rotulo
                    onTextChanged: if (activeFocus) dialogo.poner(campo.modelData.clave, text)
                }
            }
        }
        QQC2.Label {                                       // el ejemplo, tenue
            Layout.fillWidth: true
            visible: !!dialogo.actual && (dialogo.actual.ejemplos || []).length > 0
            wrapMode: Text.WordWrap
            font.italic: true
            color: Kirigami.Theme.disabledTextColor
            text: dialogo.actual ? "Ejemplo: " + (dialogo.actual.ejemplos || []).join(" · ") : ""
        }

        // --- lo que dijo el marco al revisar
        Repeater {
            model: dialogo.revision ? dialogo.revision.avisos || [] : []
            Kirigami.InlineMessage {
                required property var modelData
                Layout.fillWidth: true
                visible: true
                type: modelData.estado === "falla" ? Kirigami.MessageType.Error : Kirigami.MessageType.Warning
                text: modelData.texto
            }
        }
        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: !!dialogo.revision && dialogo.revision.ok === true && (dialogo.revision.avisos || []).length === 0
            type: Kirigami.MessageType.Positive
            text: "La pregunta delimita lo que debe. Puedes guardarla en la matriz."
        }
        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: !!dialogo.revision && !!dialogo.revision.error
            type: Kirigami.MessageType.Error
            text: dialogo.revision ? dialogo.revision.error || "" : ""
        }
    }
}
