// DialogoAyudaIA — «Ayuda de la IA para esta parte…» (Ctrl+Alt+I; decisiones §1.19, contrato §10). Dos pasos, como en
// Yachay: copiar el prompt que el marco arma para la parte abierta (el del ecosistema, con su entrada rellena con el
// escrito) y pegar lo que respondió el chat; la ventana no llama a ningún modelo. Lo pegado se comprueba sin IA y se
// muestra como cambio sugerido; «Poner en el editor» reemplaza el tramo de la parte en el editor (deshacer con Ctrl+Z) y
// el archivo se escribe solo con Ctrl+S. Si el marco declara `entrega:` (§12), aceptar registra el uso (`registrar_ia`).
// Antes de copiar, si el marco declara `revisar_prompt` (C12.3, decisiones §1.22), la ventana pregunta si el prompt lleva
// datos de estudiantes o del despacho: si los lleva, lo dice con su porqué y su fuente, y copiar queda a decisión del autor.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.Dialog {
    id: dialogo
    readonly property var a: studio.ayuda
    property var editor: null                   // el EditorTexto de la parte abierta
    property string componente: ""
    property var prompt: null                   // {prompt, componente, titulo, componentes, fuente, aviso, largo} o {error}
    property var pegado: null                   // {ok, errores, avisos, antes, despues, diff} o {error}
    property bool esperando: false
    property string pendiente: ""               // lo pegado que llegó con el pedido: se comprueba cuando esté el prompt
    property var revision: null                 // lo que dijo `revisar_prompt` antes de copiar: {sensible, nivel, hallazgos, porque, fuente}
    property bool revisandoPrompt: false

    function copiar() { studio.sistema.copiarTexto(dialogo.prompt.prompt); ventana.mensajes.mostrar("Prompt copiado: pégalo en tu chat.", "positivo") }

    title: "Ayuda de la IA" + (prompt && prompt.titulo ? " — " + prompt.titulo : "")
    preferredWidth: Kirigami.Units.gridUnit * 44
    preferredHeight: Kirigami.Units.gridUnit * 38
    standardButtons: Kirigami.Dialog.Close

    function abrirPara(e, texto) {
        if (!e) { ventana.mensajes.mostrar("Abre la parte del escrito que quieres trabajar.", "aviso"); return }
        editor = e; componente = ""; prompt = null; pegado = null; revision = null; respuesta.text = texto || ""; pendiente = texto || ""
        esperando = true
        a.pedirPrompt(e.ruta, "")
        open()
    }

    Connections {
        target: dialogo.a
        function onPromptListo(p) {
            dialogo.esperando = false
            dialogo.prompt = p
            if (p.componente) dialogo.componente = p.componente
            if (dialogo.pendiente && !p.error) {
                dialogo.esperando = true
                dialogo.a.comprobar(dialogo.editor.ruta, dialogo.componente, dialogo.pendiente, dialogo.editor.area.text)
                dialogo.pendiente = ""
            }
        }
        function onPegadoListo(r) { dialogo.esperando = false; dialogo.pegado = r }
        function onPromptRevisado(r) {
            dialogo.revisandoPrompt = false
            dialogo.revision = r
            if (!r.sensible) dialogo.copiar()
        }
    }

    customFooterActions: [
        Kirigami.Action {
            text: "Copiar el prompt"; icon.name: "edit-copy"
            enabled: !!dialogo.prompt && !!dialogo.prompt.prompt && !dialogo.revisandoPrompt
            onTriggered: { dialogo.revisandoPrompt = true; dialogo.revision = null; dialogo.a.revisarPrompt(dialogo.prompt.prompt) }
        },
        Kirigami.Action {
            text: "Comprobar lo pegado"; icon.name: "dialog-ok"
            enabled: respuesta.text.trim() !== "" && !dialogo.esperando && !!dialogo.editor
            onTriggered: { dialogo.esperando = true; dialogo.a.comprobar(dialogo.editor.ruta, dialogo.componente, respuesta.text, dialogo.editor.area.text) }
        },
        Kirigami.Action {
            text: "Poner en el editor"; icon.name: "document-edit"
            enabled: !!dialogo.pegado && dialogo.pegado.ok === true && !!dialogo.editor && !dialogo.editor.soloLectura
            onTriggered: {
                const area = dialogo.editor.area
                const antes = dialogo.pegado.antes
                const i = area.text.indexOf(antes)
                if (i < 0) { ventana.mensajes.mostrar("La parte cambió en el editor desde que lo comprobaste: vuelve a comprobarlo.", "aviso"); return }
                area.remove(i, i + antes.length)
                area.insert(i, dialogo.pegado.despues)
                dialogo.editor.seleccionar(i, i + dialogo.pegado.despues.length)
                // el cambio aceptado queda en el registro de usos de la IA del marco (contrato §12, decisiones §1.21)
                const f = dialogo.prompt && dialogo.prompt.fuente ? dialogo.prompt.fuente : {}
                const registra = studio.entrega.disponible
                if (registra)
                    studio.entrega.registrarIa({ ruta: dialogo.editor.ruta, parte: (dialogo.prompt && dialogo.prompt.titulo) || dialogo.componente,
                                                 prompt: { titulo: f.titulo || "", ruta: f.ruta || "", version: f.version || "",
                                                           componente: dialogo.componente, texto: dialogo.prompt ? dialogo.prompt.prompt || "" : "" },
                                                 antes: antes, despues: dialogo.pegado.despues })
                ventana.mensajes.mostrar("Cambio puesto en el editor" + (registra ? " y su uso, registrado" : "")
                                         + ": revísalo y guarda con Ctrl+S (Ctrl+Z lo deshace).", "positivo")
                dialogo.close()
            }
        }
    ]

    QQC2.ScrollView {
        id: vista
        contentWidth: availableWidth
        QQC2.ScrollBar.horizontal.policy: QQC2.ScrollBar.AlwaysOff
        ColumnLayout {
            x: Kirigami.Units.largeSpacing
            width: vista.availableWidth - Kirigami.Units.largeSpacing * 2
            spacing: Kirigami.Units.smallSpacing

            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: !!dialogo.prompt && !!dialogo.prompt.error
                type: Kirigami.MessageType.Warning
                text: dialogo.prompt && dialogo.prompt.error ? dialogo.prompt.error : ""
            }
            QQC2.Label {
                Layout.fillWidth: true
                visible: dialogo.esperando && !dialogo.prompt
                text: "Preparando el prompt de la parte…"
                color: Kirigami.Theme.disabledTextColor
            }

            // 1. el prompt
            Kirigami.Heading { level: 4; text: "1. Copia el prompt"; visible: !!dialogo.prompt && !dialogo.prompt.error }
            RowLayout {
                visible: !!dialogo.prompt && (dialogo.prompt.componentes || []).length > 1
                spacing: Kirigami.Units.smallSpacing
                Repeater {
                    model: dialogo.prompt ? dialogo.prompt.componentes || [] : []
                    Chip {
                        required property var modelData
                        text: modelData.titulo
                        destacado: dialogo.componente === modelData.clave
                        onClicked: { dialogo.componente = modelData.clave; dialogo.pegado = null; dialogo.esperando = true; dialogo.a.pedirPrompt(dialogo.editor.ruta, modelData.clave) }
                    }
                }
            }
            QQC2.Label {
                Layout.fillWidth: true
                visible: !!dialogo.prompt && !dialogo.prompt.error
                wrapMode: Text.WordWrap
                text: dialogo.prompt && dialogo.prompt.fuente ? "«" + dialogo.prompt.fuente.titulo + "»" + (dialogo.prompt.fuente.version ? ", versión " + dialogo.prompt.fuente.version : "")
                      + " · " + dialogo.prompt.contexto.fichas + " fichas · " + dialogo.prompt.contexto.obras + " obras para citar" : ""
                color: Kirigami.Theme.disabledTextColor
            }
            QQC2.Label {
                Layout.fillWidth: true
                visible: text !== ""
                wrapMode: Text.WordWrap
                text: dialogo.prompt ? (dialogo.prompt.aviso || "") + (dialogo.prompt.largo ? " El prompt es largo para un chat externo." : "") : ""
                color: Kirigami.Theme.neutralTextColor
            }

            // el aviso antes de copiar (C12.3): datos de estudiantes o del despacho en el prompt
            Kirigami.InlineMessage {
                id: avisoSensible
                Layout.fillWidth: true
                visible: !!dialogo.revision && dialogo.revision.sensible === true
                type: dialogo.revision && dialogo.revision.nivel === "alto" ? Kirigami.MessageType.Error : Kirigami.MessageType.Warning
                text: !dialogo.revision ? "" : dialogo.revision.error ? "No se pudo revisar el prompt (" + dialogo.revision.error + "). ¿Lo copias igual?"
                      : "El prompt parece llevar datos que no deben salir de la máquina: "
                        + (dialogo.revision.hallazgos || []).slice(0, 4).map(h => h.tipo + (h.linea > 0 ? " (línea " + h.linea + ")" : "")).join(", ")
                        + ((dialogo.revision.total || 0) > 4 ? " y " + (dialogo.revision.total - 4) + " más" : "") + ". Quítalos antes de pegarlo en un chat externo."
                actions: [
                    Kirigami.Action { text: "Copiar de todos modos"; icon.name: "edit-copy"; onTriggered: { dialogo.revision = null; dialogo.copiar() } },
                    Kirigami.Action { text: "No copiar"; icon.name: "dialog-cancel"; onTriggered: dialogo.revision = null }
                ]
            }
            QQC2.Label {                                   // por qué · fuente del aviso
                Layout.fillWidth: true
                visible: avisoSensible.visible && text !== ""
                text: dialogo.revision ? [(dialogo.revision.porque || "").replace(/\.$/, ""), dialogo.revision.fuente].filter(x => !!x).join(" · ") : ""
                wrapMode: Text.WordWrap
                font: Kirigami.Theme.smallFont
                color: Kirigami.Theme.disabledTextColor
            }

            // 2. lo pegado
            Kirigami.Heading { level: 4; text: "2. Pega aquí la respuesta del chat"; visible: !!dialogo.prompt && !dialogo.prompt.error }
            QQC2.TextArea {
                id: respuesta
                Layout.fillWidth: true
                Layout.minimumHeight: Kirigami.Units.gridUnit * 7
                visible: !!dialogo.prompt && !dialogo.prompt.error
                wrapMode: TextEdit.Wrap
                placeholderText: "El bloque ```latex que devolvió el chat"
                font.family: Kirigami.Theme.fixedWidthFont.family
                Accessible.name: "Respuesta del chat"
                onTextChanged: dialogo.pegado = null
            }

            // 3. el cambio sugerido
            Repeater {
                model: dialogo.pegado ? (dialogo.pegado.errores || (dialogo.pegado.error ? [dialogo.pegado.error] : [])) : []
                Kirigami.InlineMessage { required property string modelData; Layout.fillWidth: true; visible: true; type: Kirigami.MessageType.Error; text: modelData }
            }
            Repeater {
                model: dialogo.pegado ? dialogo.pegado.avisos || [] : []
                Kirigami.InlineMessage { required property string modelData; Layout.fillWidth: true; visible: true; type: Kirigami.MessageType.Warning; text: modelData }
            }
            Kirigami.Heading { level: 4; text: "3. El cambio sugerido"; visible: !!dialogo.pegado && dialogo.pegado.ok === true }
            QQC2.TextArea {
                Layout.fillWidth: true
                Layout.minimumHeight: Kirigami.Units.gridUnit * 8
                visible: !!dialogo.pegado && dialogo.pegado.ok === true
                readOnly: true
                text: dialogo.pegado ? dialogo.pegado.diff || "" : ""
                font.family: Kirigami.Theme.fixedWidthFont.family
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                wrapMode: TextEdit.NoWrap
                Accessible.name: "Cambio sugerido"
            }
        }
    }
}
