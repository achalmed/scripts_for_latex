// DialogoFicha — «Nueva ficha» y «Editar la ficha» de la pestaña Citas (decisiones §1.19, contrato §9). El formulario lo
// describe el marco (studio.biblioteca.formulario: los tipos con sus secciones, si llevan página y categoría, los once
// rótulos); la ventana no sabe nada de la norma de fichas. «Revisar» simula (el nombre del archivo, el cotejo contra el
// PDF, lo que la norma objeta); «Guardar la ficha» escribe lo revisado, que es la confirmación. Una ficha que cambió fuera
// desde que se abrió no se pisa: se recarga.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

Kirigami.Dialog {
    showCloseButton: false            // ya hay botones al pie: sin la × roja del encabezado
    id: dialogo
    readonly property var b: studio.biblioteca
    readonly property var tipos: (b.formulario && b.formulario.tipos) || []
    property string archivo: ""                 // vacío: ficha nueva
    property string huella: ""
    property string tipo: "textual"
    property var libro: null                    // {calibre_id, titulo, clave}
    property var textos: ({})                   // {sección: texto}
    property var revision: null                 // lo que devolvió la última revisión
    property bool esperando: false
    property int version: 0
    property string categoriaPedida: "Cita clave"                     // sube al cargar otra ficha: las áreas de texto se rehacen con su texto
    readonly property var def: tipos.find(t => t.clave === tipo) || ({ secciones: [], pagina: false, categoria: false, libro: false })
    readonly property bool nueva: archivo === ""
    readonly property bool revisada: !!revision && !revision.error && !revision.aplicar

    title: nueva ? "Nueva ficha" : "Editar la ficha"
    preferredWidth: Kirigami.Units.gridUnit * 40
    preferredHeight: Kirigami.Units.gridUnit * 38
    standardButtons: Kirigami.Dialog.Cancel

    // `v` (opcional): lo que ya se sabe de la ficha {tipo, pagina, tema, uso, categoria, textos, revisar}
    function nuevaPara(l, v) {
        v = v || {}
        archivo = ""; huella = ""; tipo = v.tipo || "textual"; libro = l || null; textos = v.textos || ({}); revision = null; version++
        pagina.text = v.pagina || ""; tema.text = v.tema || ""; uso.text = v.uso || ""
        categoriaPedida = v.categoria || "Cita clave"
        categoria.currentIndex = Math.max(0, categoria.model.indexOf(categoriaPedida))
        open()
        if (v.revisar) Qt.callLater(revisar, false)
    }
    function editar(nombreArchivo) {
        revision = null; esperando = true
        b.abrirFicha(nombreArchivo)
        open()
    }
    function campos() {
        const s = {}
        for (const k of def.secciones) s[k] = textos[k] || ""
        const c = { tipo: tipo, secciones: s, uso: uso.text }
        if (def.pagina) c.pagina = pagina.text
        if (def.categoria) c.categoria = categoria.currentText
        if (nueva) c.tema = tema.text
        if (nueva && libro) c.calibre_id = libro.calibre_id
        return c
    }
    function revisar(aplicar) { esperando = true; b.revisarFicha(campos(), archivo, huella, aplicar) }

    Connections {
        target: dialogo.b
        function onFichaAbierta(f) {
            dialogo.esperando = false
            if (f.error && !(f.secciones || []).length) { ventana.mensajes.mostrar(f.error, "error"); dialogo.close(); return }
            dialogo.archivo = f.archivo; dialogo.huella = f.huella; dialogo.tipo = f.tipo
            dialogo.libro = f.clave ? { calibre_id: f.calibre_id, titulo: f.clave, clave: f.clave } : null
            const t = {}
            for (const s of f.secciones) t[s.titulo] = s.texto
            dialogo.textos = t
            dialogo.version++
            pagina.text = f.pagina || ""; uso.text = f.uso || ""
            dialogo.categoriaPedida = f.categoria || "Cita clave"
            categoria.currentIndex = Math.max(0, categoria.model.indexOf(f.categoria))
        }
        function onFichaRevisada(r) {
            dialogo.esperando = false
            if (!dialogo.visible) return
            if (r.codigo === "ficha_cambiada") {
                ventana.mensajes.mostrar("La ficha cambió fuera desde que la abriste: se recargó tal como está ahora.", "aviso")
                dialogo.editar(dialogo.archivo)
                return
            }
            if (r.aplicar && r.escrito) {
                ventana.mensajes.mostrar("Ficha guardada: " + r.archivo, "positivo")
                dialogo.close()
                return
            }
            dialogo.revision = r
        }
    }

    customFooterActions: [
        Kirigami.Action {
            text: "Revisar"; icon.name: "document-preview"
            enabled: !dialogo.esperando && (!dialogo.def.libro || !!dialogo.libro)
            onTriggered: dialogo.revisar(false)
        },
        Kirigami.Action {
            text: "Guardar la ficha"; icon.name: "document-save"
            enabled: dialogo.revisada && !dialogo.esperando
            onTriggered: dialogo.revisar(true)
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

            // el tipo (solo en una nueva: una ficha no cambia de tipo aquí)
            RowLayout {
                visible: dialogo.nueva
                spacing: Kirigami.Units.smallSpacing
                Repeater {
                    model: dialogo.tipos
                    OpcionColor {
                        required property var modelData
                        text: modelData.nombre
                        onClicked: { dialogo.tipo = modelData.clave; dialogo.revision = null }
                        elegida: dialogo.tipo === modelData.clave
                    }
                }
            }

            // el libro
            QQC2.Label {
                Layout.fillWidth: true
                visible: dialogo.def.libro
                text: dialogo.libro ? "Libro: " + dialogo.libro.titulo + (dialogo.libro.clave ? " · " + dialogo.libro.clave : "") : "Elige el libro de la ficha:"
                font.weight: Font.Medium
                elide: Text.ElideRight
            }
            Kirigami.SearchField {
                id: buscaLibro
                Layout.fillWidth: true
                visible: dialogo.nueva && dialogo.def.libro
                placeholderText: dialogo.libro ? "Buscar otro libro" : "Buscar el libro en la biblioteca"
                onTextChanged: pausa.restart()
                Timer { id: pausa; interval: 350; onTriggered: dialogo.b.buscar(buscaLibro.text) }
            }
            ListView {
                id: libros
                Layout.fillWidth: true
                Layout.preferredHeight: Kirigami.Units.gridUnit * 6
                visible: dialogo.nueva && dialogo.def.libro && buscaLibro.text !== ""
                clip: true
                model: dialogo.b.resultados
                Accessible.name: "Libros para la ficha"
                delegate: QQC2.ItemDelegate {
                    id: filaLibroFicha
                    required property var modelData
                    width: libros.width
                    highlighted: !!dialogo.libro && dialogo.libro.calibre_id === modelData.calibre_id
                    text: modelData.titulo + ((modelData.autores || []).length ? " · " + modelData.autores.join("; ") : "")
                    hoverEnabled: true
                    topInset: 1
                    bottomInset: 1
                    leftInset: Kirigami.Units.smallSpacing
                    rightInset: Kirigami.Units.smallSpacing
                    leftPadding: Kirigami.Units.largeSpacing + Kirigami.Units.smallSpacing
                    background: FondoSeleccion { elegida: filaLibroFicha.highlighted; sobre: filaLibroFicha.hovered; pulsada: filaLibroFicha.pressed; foco: filaLibroFicha.visualFocus }
                    contentItem: QQC2.Label { text: filaLibroFicha.text; elide: Text.ElideRight; font.weight: filaLibroFicha.highlighted ? Font.DemiBold : Font.Normal }
                    onClicked: { dialogo.libro = modelData; dialogo.revision = null }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: Kirigami.Units.largeSpacing
                QQC2.Label { text: "Página o lugar"; visible: dialogo.def.pagina }
                QQC2.TextField { id: pagina; Layout.fillWidth: true; visible: dialogo.def.pagina; placeholderText: "12 · art. 5 · 3.2"; onTextChanged: dialogo.revision = null }
                QQC2.Label { text: "Categoría"; visible: dialogo.def.categoria }
                QQC2.ComboBox {
                    id: categoria
                    Layout.fillWidth: true
                    visible: dialogo.def.categoria
                    model: (dialogo.b.formulario && dialogo.b.formulario.categorias) || []
                    onModelChanged: currentIndex = Math.max(0, model.indexOf(dialogo.categoriaPedida))
                    onActivated: { dialogo.categoriaPedida = currentText; dialogo.revision = null }
                }
                QQC2.Label { text: "Tema"; visible: dialogo.nueva }
                QQC2.TextField { id: tema; Layout.fillWidth: true; visible: dialogo.nueva; placeholderText: "dos a cuatro palabras (si no, sale de la cita)" }
                QQC2.Label { text: "Uso" }
                QQC2.TextField { id: uso; Layout.fillWidth: true; placeholderText: "la parte del escrito que respalda" }
            }

            Repeater {
                model: dialogo.version >= 0 ? dialogo.def.secciones.slice() : []
                ColumnLayout {
                    required property string modelData
                    Layout.fillWidth: true
                    spacing: 0
                    QQC2.Label {
                        text: modelData + (modelData === dialogo.def.literal ? " (tal cual en la fuente, sin comillas)" : "")
                        font: Kirigami.Theme.smallFont
                        color: Kirigami.Theme.disabledTextColor
                    }
                    QQC2.TextArea {
                        Layout.fillWidth: true
                        Layout.minimumHeight: Kirigami.Units.gridUnit * (modelData === dialogo.def.literal ? 4 : 3)
                        wrapMode: TextEdit.Wrap
                        text: dialogo.textos[modelData] || ""
                        Accessible.name: modelData
                        onTextChanged: { if (activeFocus) { dialogo.textos[modelData] = text; dialogo.revision = null } }
                    }
                }
            }

            // lo revisado
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
                    readonly property string estado: dialogo.revisada ? dialogo.revision.verificacion.estado || "pendiente" : ""
                    Kirigami.Icon {
                        source: parent.estado.startsWith("verificada") ? "checkmark-symbolic" : parent.estado === "observada" ? "dialog-warning-symbolic" : "dialog-question-symbolic"
                        implicitWidth: Kirigami.Units.iconSizes.small; implicitHeight: implicitWidth
                        isMask: true
                        color: parent.estado.startsWith("verificada") ? Kirigami.Theme.positiveTextColor
                             : parent.estado === "observada" ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.neutralTextColor
                    }
                    QQC2.Label {
                        text: ({ verificada_script: "Cotejada en el PDF", verificada_autor: "Verificada por el autor",
                                 observada: "Observada", pendiente: "Sin cotejar" })[parent.estado] || ""
                        font.weight: Font.Medium
                    }
                    QQC2.Label {
                        Layout.fillWidth: true
                        text: dialogo.revisada ? dialogo.revision.archivo : ""
                        font.family: Kirigami.Theme.fixedWidthFont.family
                        elide: Text.ElideMiddle
                    }
                }
                QQC2.Label {
                    Layout.fillWidth: true
                    visible: text !== ""
                    wrapMode: Text.WordWrap
                    color: Kirigami.Theme.disabledTextColor
                    text: dialogo.revisada ? (dialogo.revision.detalle || "") : ""
                }
                QQC2.Label {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: !dialogo.revisada ? "" : "Al guardar se escribe fuentes/fichas/" + dialogo.revision.archivo
                          + (dialogo.revision.renombra ? " (antes " + dialogo.revision.antes + ", que se retira)" : "")
                          + (dialogo.revision.nueva_fuente ? "; el libro aún no es fuente del escrito: se añade a fuentes.yml y a references.bib" : "")
                          + ". El texto del documento no se toca."
                }
                Repeater {
                    model: dialogo.revisada ? dialogo.revision.problemas : []
                    QQC2.Label {
                        required property string modelData
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: "· " + modelData
                        color: modelData.startsWith("aviso") ? Kirigami.Theme.neutralTextColor : Kirigami.Theme.negativeTextColor
                    }
                }
            }
        }
    }
}
