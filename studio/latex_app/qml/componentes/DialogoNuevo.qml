// DialogoNuevo — «Nuevo documento» (Ctrl+N; decisiones §1.20, contrato §11): crear un documento del marco con botones y
// un formulario, sin la terminal. Lo que se puede crear lo dice el marco (studio.nuevo.tipos: cada tipo con su línea,
// sus variantes y los campos del formulario); la ventana no sabe qué es una tesis. Con varios marcos que lo declaran, se
// elige el marco primero. «Revisar» simula (el marco crea en un temporal y dice la carpeta y los archivos); «Crear y
// abrir», la única acción rellena, crea lo revisado y abre el principal en el editor.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

Kirigami.Dialog {
    showCloseButton: false            // ya hay botones al pie: sin la × roja del encabezado
    id: dialogo
    readonly property var n: studio.nuevo
    property string tipo: ""
    property string variante: ""
    property var valores: ({})                  // {clave: texto}; se escribe en el sitio (no rehace los campos al teclear)
    property int cambios: 0                     // sube con cada cambio del formulario (lo que depende de los valores)
    property int version: 0                     // sube al cargar valores desde fuera: los campos se rehacen
    property bool revisarAlCargar: false
    readonly property var def: { n.tipos; return n.tipos.find(t => t.clave === tipo) || null }
    readonly property var revision: n.revision
    readonly property bool revisada: !!revision && !!revision.destino && !revision.error && !revision.aplicar
    // un campo de opciones obligatorio con su omisión (el proyecto de las láminas) ya está lleno sin tocarlo
    readonly property bool completo: {
        cambios
        if (!def) return false
        return def.campos.every(c => !c.obligatorio || String(valores[c.clave] !== undefined ? valores[c.clave] : (c.omision || "")).trim() !== "")
    }

    title: "Nuevo documento"
    preferredWidth: Kirigami.Units.gridUnit * 46
    preferredHeight: Kirigami.Units.gridUnit * 40
    standardButtons: Kirigami.Dialog.NoButton
    padding: Kirigami.Units.largeSpacing

    // `v` (opcional): {tipo, variante, valores, revisar} (las capturas; un tipo pedido desde fuera)
    function abrir(v) {
        v = v || {}
        n.recargar()
        n.olvidar()
        tipo = v.tipo || ""; variante = v.variante || ""
        valores = Object.assign({}, v.valores || {}); version++; cambios++
        if (tipo && def && !variante) variante = def.variante.omision
        revisarAlCargar = !!v.revisar
        open()
        if (revisarAlCargar && def) { revisarAlCargar = false; revisar() }
    }
    function elegirTipo(clave) {
        if (clave === tipo) return
        tipo = clave
        variante = def ? def.variante.omision : ""
        n.olvidar(); cambios++
    }
    function poner(clave, valor) { valores[clave] = valor; cambios++; n.olvidar() }
    function opcionesDe(c) {
        let lista = c.opciones || []
        if (c.segun_variante) {
            const admitidas = c.segun_variante[variante] || []
            lista = lista.filter(o => admitidas.includes(o.clave))
            if (lista.length === 0) return []
        }
        return c.obligatorio || (c.omision || "") !== "" ? lista : [{ clave: "", nombre: "Por omisión" }].concat(lista)
    }
    function campos() {
        const salida = { tipo: tipo, variante: variante }
        for (const c of def.campos) {
            const v = valores[c.clave]
            salida[c.clave] = v !== undefined ? v : (c.omision || "")
        }
        return salida
    }
    function revisar() { if (def) n.revisar(campos()) }

    Connections {
        target: dialogo.n
        function onCambiado() {
            if (dialogo.tipo && dialogo.def && !dialogo.variante) dialogo.variante = dialogo.def.variante.omision
            if (dialogo.revisarAlCargar && dialogo.def) { dialogo.revisarAlCargar = false; dialogo.revisar() }
        }
        function onCreado(principal) {
            const r = dialogo.revision
            dialogo.close()
            ventana.mensajes.mostrar("Documento creado: " + (r && r.carpeta ? r.carpeta : principal), "positivo")
            ventana.abrirProyecto(principal)
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
                elide: Text.ElideRight
                font: Kirigami.Theme.smallFont
                color: Kirigami.Theme.disabledTextColor
                text: dialogo.n.trabajando ? "Revisando…" : !dialogo.def ? "" : !dialogo.completo ? "Faltan datos obligatorios."
                      : dialogo.revisada ? "Revisado: nada se ha escrito todavía." : "«Revisar» muestra lo que se creará."
            }
            QQC2.Button { text: "Cancelar"; onClicked: dialogo.close() }
            QQC2.Button {
                text: "Revisar"; icon.name: "document-preview"
                enabled: dialogo.completo && !dialogo.n.trabajando
                opacity: enabled ? 1 : 0.5
                QQC2.ToolTip.text: "Simula: la carpeta y los archivos, sin escribir nada"
                onClicked: dialogo.revisar()
                QQC2.ToolTip.visible: hovered && QQC2.ToolTip.text !== ""
                QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
            }
            BotonPrincipal {
                text: "Crear y abrir"; icon.name: "document-new-symbolic";
                enabled: dialogo.revisada && !dialogo.n.trabajando
                opacity: enabled ? 1 : 0.5
                QQC2.ToolTip.text: "Crea lo revisado y lo abre en el editor"
                onClicked: dialogo.n.crear(dialogo.campos())
                QQC2.ToolTip.visible: hovered && QQC2.ToolTip.text !== ""
                QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
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

            // --- sin marco que lo declare
            Kirigami.PlaceholderMessage {
                Layout.fillWidth: true
                Layout.topMargin: Kirigami.Units.gridUnit * 4
                visible: dialogo.n.marcos.length === 0
                icon.name: "document-new-symbolic"
                text: "Ningún marco ofrece documentos nuevos"
                explanation: "Un marco lo declara en su latex-studio.yml (sección nuevo:). Añade su carpeta en Carpetas de trabajo (Ctrl+Mayús+O)."
            }

            // --- 0. el marco, si hay varios
            ColumnLayout {
                Layout.fillWidth: true
                visible: dialogo.n.marcos.length > 1
                spacing: 0
                QQC2.Label { text: "Marco"; font.weight: Font.Medium }
                Repeater {
                    model: dialogo.n.marcos
                    QQC2.ItemDelegate {
                        id: filaMarco
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true
                        background: Rectangle {             // elegido: un tinte, no un relleno (la acción rellena es «Crear y abrir»)
                            radius: Kirigami.Units.cornerRadius
                            color: dialogo.n.marco === filaMarco.index ? Qt.alpha(Kirigami.Theme.highlightColor, 0.1)
                                 : filaMarco.hovered ? Qt.alpha(Kirigami.Theme.textColor, 0.04) : "transparent"
                        }
                        onClicked: { dialogo.n.elegirMarco(index); dialogo.tipo = ""; dialogo.variante = "" }
                        contentItem: RowLayout {
                            spacing: Kirigami.Units.largeSpacing
                            QQC2.RadioButton { checked: dialogo.n.marco === index; focusPolicy: Qt.NoFocus; onClicked: parent.parent.clicked() }
                            QQC2.Label { text: modelData.nombre; font.weight: Font.Medium }
                            QQC2.Label { Layout.fillWidth: true; text: modelData.carpeta; elide: Text.ElideMiddle; font: Kirigami.Theme.smallFont; color: Kirigami.Theme.disabledTextColor }
                        }
                    }
                }
            }

            QQC2.BusyIndicator { Layout.alignment: Qt.AlignHCenter; visible: dialogo.n.cargando; running: visible }
            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: dialogo.n.error !== ""
                type: Kirigami.MessageType.Error
                text: dialogo.n.error
            }

            // --- 1. el tipo, en tarjetas
            QQC2.Label {
                visible: dialogo.n.tipos.length > 0
                text: dialogo.n.marcos.length > 1 ? "Qué crear en " + dialogo.n.nombreMarco : "Qué crear"
                font.weight: Font.Medium
            }
            GridLayout {
                id: rejilla
                Layout.fillWidth: true
                visible: dialogo.n.tipos.length > 0
                columns: Math.max(1, Math.min(3, Math.floor(width / (Kirigami.Units.gridUnit * 12))))
                columnSpacing: Kirigami.Units.smallSpacing
                rowSpacing: Kirigami.Units.smallSpacing
                Repeater {
                    model: dialogo.n.tipos
                    QQC2.AbstractButton {
                        id: tarjeta
                        required property var modelData
                        readonly property bool elegida: dialogo.tipo === modelData.clave
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: Kirigami.Units.gridUnit * 3.6
                        hoverEnabled: true
                        Accessible.name: modelData.nombre
                        Accessible.description: modelData.descripcion
                        onClicked: dialogo.elegirTipo(modelData.clave)
                        padding: Kirigami.Units.largeSpacing
                        background: Rectangle {
                            radius: Kirigami.Units.cornerRadius * 2
                            color: tarjeta.elegida ? Qt.alpha(Kirigami.Theme.highlightColor, 0.1)
                                 : tarjeta.hovered ? Qt.alpha(Kirigami.Theme.textColor, 0.04) : "transparent"
                            border.width: tarjeta.elegida ? 2 : 1
                            border.color: tarjeta.elegida ? Kirigami.Theme.highlightColor : Qt.alpha(Kirigami.Theme.textColor, tarjeta.hovered ? 0.3 : 0.15)
                        }
                        contentItem: ColumnLayout {
                            spacing: Kirigami.Units.smallSpacing / 2
                            QQC2.Label { Layout.fillWidth: true; text: tarjeta.modelData.nombre; font.weight: Font.Medium; elide: Text.ElideRight }
                            QQC2.Label {
                                Layout.fillWidth: true
                                text: tarjeta.modelData.descripcion
                                wrapMode: Text.WordWrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                                font: Kirigami.Theme.smallFont
                                color: Kirigami.Theme.disabledTextColor
                            }
                            Item { Layout.fillHeight: true }
                        }
                    }
                }
            }

            // --- 2. la variante, en lista
            ColumnLayout {
                Layout.fillWidth: true
                visible: !!dialogo.def && dialogo.def.variante.opciones.length > 1
                spacing: 0
                QQC2.Label { text: dialogo.def ? dialogo.def.variante.rotulo : ""; font.weight: Font.Medium; Layout.bottomMargin: Kirigami.Units.smallSpacing }
                Repeater {
                    model: dialogo.def ? dialogo.def.variante.opciones : []
                    QQC2.ItemDelegate {
                        id: opcion
                        required property var modelData
                        readonly property bool elegida: dialogo.variante === modelData.clave
                        Layout.fillWidth: true
                        background: Rectangle {
                            radius: Kirigami.Units.cornerRadius
                            color: opcion.elegida ? Qt.alpha(Kirigami.Theme.highlightColor, 0.1)
                                 : opcion.hovered ? Qt.alpha(Kirigami.Theme.textColor, 0.04) : "transparent"
                        }
                        onClicked: { dialogo.variante = modelData.clave; dialogo.n.olvidar(); dialogo.cambios++ }
                        Accessible.name: modelData.nombre
                        contentItem: RowLayout {
                            spacing: Kirigami.Units.largeSpacing
                            QQC2.RadioButton { checked: opcion.elegida; focusPolicy: Qt.NoFocus; onClicked: opcion.clicked() }
                            QQC2.Label { text: opcion.modelData.nombre; Layout.preferredWidth: Kirigami.Units.gridUnit * 11; elide: Text.ElideRight }
                            QQC2.Label { Layout.fillWidth: true; text: opcion.modelData.descripcion || ""; elide: Text.ElideRight; color: Kirigami.Theme.disabledTextColor }
                        }
                    }
                }
            }

            // --- 3. el formulario que describe el marco
            ColumnLayout {
                Layout.fillWidth: true
                visible: !!dialogo.def
                spacing: Kirigami.Units.smallSpacing
                QQC2.Label { text: "Datos"; font.weight: Font.Medium }
                Repeater {
                    model: dialogo.def && dialogo.version >= 0 ? dialogo.def.campos : []
                    RowLayout {
                        id: fila
                        required property var modelData
                        readonly property var opciones: { dialogo.variante; return modelData.tipo === "opcion" ? dialogo.opcionesDe(modelData) : [] }
                        Layout.fillWidth: true
                        visible: modelData.tipo !== "opcion" || opciones.length > 0
                        spacing: Kirigami.Units.largeSpacing
                        QQC2.Label {
                            Layout.preferredWidth: Kirigami.Units.gridUnit * 10
                            Layout.alignment: fila.modelData.tipo === "lineas" ? Qt.AlignTop : Qt.AlignVCenter
                            Layout.topMargin: fila.modelData.tipo === "lineas" ? Kirigami.Units.smallSpacing : 0
                            horizontalAlignment: Text.AlignRight
                            text: fila.modelData.rotulo
                            wrapMode: Text.WordWrap
                            color: fila.modelData.obligatorio ? Kirigami.Theme.textColor : Kirigami.Theme.disabledTextColor
                        }
                        Loader {
                            Layout.fillWidth: true
                            sourceComponent: fila.modelData.tipo === "lineas" ? cLineas : fila.modelData.tipo === "opcion" ? cOpcion : cTexto
                            Component {
                                id: cTexto
                                QQC2.TextField {
                                    text: dialogo.valores[fila.modelData.clave] || ""
                                    placeholderText: fila.modelData.obligatorio ? "obligatorio" : ""
                                    Accessible.name: fila.modelData.rotulo
                                    onTextEdited: dialogo.poner(fila.modelData.clave, text)
                                }
                            }
                            Component {
                                id: cLineas
                                QQC2.TextArea {
                                    text: dialogo.valores[fila.modelData.clave] || ""
                                    placeholderText: fila.modelData.obligatorio ? "obligatorio · uno por línea" : "uno por línea"
                                    wrapMode: TextEdit.Wrap
                                    implicitHeight: Math.max(Kirigami.Units.gridUnit * 3.5, contentHeight + topPadding + bottomPadding)
                                    Accessible.name: fila.modelData.rotulo
                                    onTextChanged: if (activeFocus) dialogo.poner(fila.modelData.clave, text)
                                }
                            }
                            Component {
                                id: cOpcion
                                QQC2.ComboBox {
                                    model: fila.opciones
                                    textRole: "nombre"
                                    valueRole: "clave"
                                    Accessible.name: fila.modelData.rotulo
                                    function sincronizar() {
                                        const v = dialogo.valores[fila.modelData.clave]
                                        const i = indexOfValue(v !== undefined ? v : (fila.modelData.omision || ""))
                                        currentIndex = Math.max(0, i)
                                    }
                                    Component.onCompleted: sincronizar()
                                    onModelChanged: sincronizar()
                                    onActivated: dialogo.poner(fila.modelData.clave, currentValue)
                                }
                            }
                        }
                    }
                }
            }

            // --- 4. la vista previa
            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: !!dialogo.revision && !!dialogo.revision.error
                type: Kirigami.MessageType.Error
                text: dialogo.revision && dialogo.revision.error ? dialogo.revision.error : ""
            }
            ColumnLayout {
                Layout.fillWidth: true
                visible: dialogo.revisada
                spacing: Kirigami.Units.smallSpacing
                Kirigami.Separator { Layout.fillWidth: true }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing
                    Kirigami.Icon { source: "folder-new"; implicitWidth: Kirigami.Units.iconSizes.small; implicitHeight: implicitWidth }
                    QQC2.Label { text: "Se creará"; font.weight: Font.Medium }
                    QQC2.Label {
                        Layout.fillWidth: true
                        text: dialogo.revisada ? dialogo.revision.destino : ""
                        font.family: Kirigami.Theme.fixedWidthFont.family
                        elide: Text.ElideMiddle
                        QQC2.ToolTip.text: text
                        QQC2.ToolTip.visible: zonaDestino.hovered
                        HoverHandler { id: zonaDestino }
                    }
                }
                QQC2.Label {
                    Layout.fillWidth: true
                    readonly property var r: dialogo.revisada ? dialogo.revision : ({})
                    text: dialogo.revisada ? (r.archivos || []).length + " archivo" + ((r.archivos || []).length === 1 ? "" : "s")
                          + " · se abre " + String(r.principal || "").split("/").pop() : ""
                    font: Kirigami.Theme.smallFont
                    color: Kirigami.Theme.disabledTextColor
                }
                ListView {
                    id: archivos
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(contentHeight, Kirigami.Units.gridUnit * 9)
                    clip: true
                    interactive: contentHeight > height
                    model: dialogo.revisada ? dialogo.revision.archivos : []
                    Accessible.name: "Archivos que se crearán"
                    QQC2.ScrollBar.vertical: QQC2.ScrollBar {}
                    delegate: QQC2.Label {
                        required property string modelData
                        width: archivos.width
                        text: modelData
                        elide: Text.ElideMiddle
                        font.family: Kirigami.Theme.fixedWidthFont.family
                        font.pointSize: Kirigami.Theme.smallFont.pointSize
                        font.weight: dialogo.revisada && String(dialogo.revision.principal).endsWith("/" + modelData) ? Font.DemiBold : Font.Normal
                        color: font.weight === Font.DemiBold ? Kirigami.Theme.textColor : Kirigami.Theme.disabledTextColor
                    }
                }
                Repeater {
                    model: dialogo.revisada ? (dialogo.revision.avisos || []) : []
                    QQC2.Label { required property string modelData; Layout.fillWidth: true; text: modelData; wrapMode: Text.WordWrap; font: Kirigami.Theme.smallFont; color: Kirigami.Theme.neutralTextColor }
                }
            }
        }
    }
}
