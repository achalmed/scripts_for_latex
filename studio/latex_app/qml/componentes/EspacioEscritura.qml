// EspacioEscritura — la vista Escritura: a la izquierda (en el centro de la ventana) las pestañas de los archivos
// abiertos con el editor y la barra de búsqueda; a la derecha el PDF integrado (F7 lo oculta). Cada archivo abierto
// tiene su EditorTexto de gui-comun (su texto y su deshacer); el aviso de «cambió fuera» y la confirmación de sobrescribir viven
// aquí. Sin datos propios: studio.editor (abiertos), studio.visor, studio.proyectos.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

QQC2.SplitView {
    id: raiz

    property bool mostrarPdf: true
    readonly property var editorActual: editores.count > 0 && studio.editor.indiceActual >= 0 ? editores.itemAt(studio.editor.indiceActual) : null

    orientation: Qt.Horizontal

    function editorDe(ruta) {
        for (let i = 0; i < editores.count; i++) { const e = editores.itemAt(i); if (e && e.ruta === ruta) return e }
        return null
    }
    function abrir(ruta, linea) {
        const i = studio.editor.abrir(ruta)
        if (i < 0) return
        Qt.callLater(() => { const e = editorDe(ruta); if (e && linea > 0) e.irALinea(linea, 0); else if (e) e.area.forceActiveFocus() })
    }
    function guardar(e, forzar) {
        if (!e) return
        const r = e.guardar(forzar)
        if (r === "externo") { confirmarSobrescribir.editor = e; confirmarSobrescribir.open() }
        else if (r !== "") ventana.mensajes.mostrar(r, "error")
    }
    function guardarTodo() {
        for (let i = 0; i < editores.count; i++) { const e = editores.itemAt(i); if (e && e.modificado) guardar(e, false) }
    }
    function cerrarActual() {
        const e = editorActual
        if (!e) return
        if (e.modificado) { confirmarCerrar.editor = e; confirmarCerrar.open() }
        else studio.editor.cerrar(e.ruta)
    }

    Connections {
        target: studio.editor
        function onCambioExterno(ruta) {
            const e = raiz.editorDe(ruta)
            if (!e) return
            if (!e.modificado) { e.recargarDesdeDisco(); ventana.mensajes.mostrar(ruta.split("/").pop() + " cambió fuera de la ventana: recargado.", "informacion") }
            else { cambioFuera.ruta = ruta; cambioFuera.visible = true }
        }
    }

    ColumnLayout {
        QQC2.SplitView.fillWidth: true
        QQC2.SplitView.minimumWidth: Kirigami.Units.gridUnit * 20
        spacing: 0

        // la barra de pestañas solo existe con archivos abiertos (el estilo de KDE falla con una TabBar vacía)
        Loader {
            Layout.fillWidth: true
            active: studio.editor.abiertos.filas > 0
            visible: active
            sourceComponent: Component {
                QQC2.TabBar {
                    currentIndex: studio.editor.indiceActual
                    Accessible.name: "Archivos abiertos"
                    Repeater {
                        model: studio.editor.abiertos
                        delegate: QQC2.TabButton {
                            required property var model
                            required property int index
                            width: implicitWidth
                            text: (model.modificado ? "● " : "") + model.nombre
                            icon.name: model.solo_lectura ? "object-locked" : ""
                            onClicked: studio.editor.fijarActual(model.ruta)
                            QQC2.ToolTip.text: model.ruta
                            QQC2.ToolTip.visible: hovered
                            QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                            TapHandler { acceptedButtons: Qt.MiddleButton; onTapped: { studio.editor.fijarActual(model.ruta); raiz.cerrarActual() } }
                        }
                    }
                }
            }
        }

        Kirigami.InlineMessage {
            id: cambioFuera
            property string ruta: ""
            Layout.fillWidth: true
            type: Kirigami.MessageType.Warning
            text: ruta.split("/").pop() + " cambió en el disco y aquí tiene cambios sin guardar."
            visible: false
            actions: [
                Kirigami.Action { text: "Recargar del disco"; icon.name: "view-refresh"; onTriggered: { const e = raiz.editorDe(cambioFuera.ruta); if (e) e.recargarDesdeDisco(); cambioFuera.visible = false } },
                Kirigami.Action { text: "Mantener lo mío"; icon.name: "dialog-ok"; onTriggered: cambioFuera.visible = false }
            ]
        }

        StackLayout {
            id: pila
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: studio.editor.indiceActual
            Repeater {
                id: editores
                model: studio.editor.abiertos
                delegate: EditorTexto {
                    required property var model
                    controlador: studio.editor
                    ruta: model.ruta
                    definicion: model.definicion
                    soloLectura: model.solo_lectura
                    ajustarLineas: studio.ajustes.ajustarLineas
                    tamanoLetra: studio.ajustes.tamanoLetra
                    completar: raiz.completarLatex
                    disparaCompletado: raiz.disparaLatex
                    Component.onCompleted: cargar()
                    onCtrlClic: (linea, columna) => studio.visor.desdeCodigo(ruta, linea, columna)
                }
            }
        }

        Kirigami.PlaceholderMessage {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: studio.editor.abiertos.filas === 0
            icon.name: "document-edit"
            text: studio.proyectos.hayAbierto ? "Elige un archivo del proyecto" : "Ningún proyecto abierto"
            explanation: studio.proyectos.hayAbierto ? "Los archivos del proyecto (el principal, sus \\input y sus .bib) están a la izquierda; la estructura, en la pestaña de al lado."
                                                     : "Ctrl+1 muestra los proyectos detectados; Ctrl+O abre un .tex."
        }

        BarraBuscarReemplazar {
            id: busqueda
            Layout.fillWidth: true
            editor: raiz.editorActual
        }

        QQC2.ToolBar {
            Layout.fillWidth: true
            position: QQC2.ToolBar.Footer
            visible: raiz.editorActual !== null
            RowLayout {
                anchors.fill: parent
                spacing: Kirigami.Units.largeSpacing
                QQC2.Label {
                    text: raiz.editorActual ? "Línea " + raiz.editorActual.lineaActual + ", columna " + (raiz.editorActual.columnaActual + 1) : ""
                    font: Kirigami.Theme.smallFont
                }
                QQC2.Label {
                    Layout.fillWidth: true
                    text: raiz.editorActual ? raiz.editorActual.ruta : ""
                    elide: Text.ElideMiddle
                    font: Kirigami.Theme.smallFont
                    color: Kirigami.Theme.disabledTextColor
                }
                QQC2.Label {
                    text: raiz.editorActual ? (raiz.editorActual.definicion || "texto") + (raiz.editorActual.soloLectura ? " · solo lectura" : "") : ""
                    font: Kirigami.Theme.smallFont
                    color: Kirigami.Theme.disabledTextColor
                }
            }
        }
    }

    // el PDF: VistaPdf de gui-comun 3.2 (QtPdf o pdftoppm, zoom, miniaturas, selección, enlaces, búsqueda); lo de LaTeX
    // es SyncTeX: el doble clic y «Ir al código de este punto» vuelven al código, y la marca la pone studio.visor
    VistaPdf {
        id: visorPdf
        visible: raiz.mostrarPdf
        visor: studio.visor
        QQC2.SplitView.preferredWidth: Kirigami.Units.gridUnit * 30
        QQC2.SplitView.minimumWidth: Kirigami.Units.gridUnit * 14
        textoPunto: "Ir al código de este punto"
        puntoHabilitado: studio.visor.haySynctex
        onDobleClic: (pagina, x, y) => studio.visor.haciaCodigo(pagina, x, y)
        mensajeVacio: studio.proyectos.hayAbierto ? "Todavía no hay PDF" : "Ningún proyecto abierto"
        explicacionVacia: studio.proyectos.hayAbierto ? "Compila el proyecto (F5 o Ctrl+B): el PDF aparece aquí y se recarga en cada compilación."
                                                      : "Abre un proyecto en la página de proyectos (Ctrl+1)."
    }

    function buscar(reemplazar) { busqueda.abrir(reemplazar) }

    // el autocompletado de LaTeX en el EditorTexto de la base: lo calcula Python (órdenes con su firma, entornos, \ref de
    // las \label, \cite de los .bib, paquetes, clases y archivos del proyecto); una orden se ofrece desde dos letras
    function completarLatex(antes, forzado) {
        const r = studio.proyectos.completar(antes)
        return (!forzado && r.tipo === "orden" && r.prefijo.length < 2) ? null : r
    }
    // qué tecla lo abre: «\», «{», «,», «/» o una letra en un contexto que se completa; Intro y Tab también, para que
    // al aceptar \usepackage o \begin se ofrezca en el acto su argumento
    function disparaLatex(antes, tecla) {
        const aceptar = tecla === "\r" || tecla === "\t"           // tras aceptar una sugerencia: solo si sigue un argumento
        if (!(aceptar || tecla === "\\" || tecla === "{" || tecla === "," || tecla === "/" || /^[A-Za-z:]$/.test(tecla))) return false
        if (aceptar && !antes.endsWith("{")) return false           // un entorno o una clave recién puestos: nada más
        return (!aceptar && /\\[A-Za-z@]{2,}$/.test(antes)) || /\\(begin|end)\s*\{[^{}]*$/.test(antes)
            || /\\[A-Za-z]*(ref|cite|Cite)[A-Za-z]*\*?\s*(\[[^\]]*\]\s*){0,2}\{[^{}]*$/.test(antes)
            || /\\(usepackage|RequirePackage|documentclass|includegraphics|input|include|subfile|addbibresource|bibliography|bibliographystyle)\*?\s*(\[[^\]]*\]\s*)?\{[^{}]*$/.test(antes)
    }
    function buscarEnPdf() {
        if (!raiz.mostrarPdf) { raiz.mostrarPdf = true; ventana.registro.marcar("ver.pdf", true) }
        visorPdf.buscarEnPdf()
    }

    Kirigami.PromptDialog {
        id: confirmarSobrescribir
        property var editor: null
        title: "El archivo cambió en el disco"
        subtitle: (editor ? editor.ruta.split("/").pop() : "") + " se modificó fuera de la ventana desde que lo abriste. Si guardas, lo que hay en el disco se pierde."
        standardButtons: Kirigami.Dialog.Cancel
        customFooterActions: [
            Kirigami.Action { text: "Recargar del disco"; icon.name: "view-refresh"; onTriggered: { confirmarSobrescribir.editor.recargarDesdeDisco(); confirmarSobrescribir.close() } },
            Kirigami.Action { text: "Sobrescribir"; icon.name: "document-save"; onTriggered: { raiz.guardar(confirmarSobrescribir.editor, true); confirmarSobrescribir.close() } }
        ]
    }
    Kirigami.PromptDialog {
        id: confirmarCerrar
        property var editor: null
        title: "Cambios sin guardar"
        subtitle: (editor ? editor.ruta.split("/").pop() : "") + " tiene cambios sin guardar. ¿Guardarlos antes de cerrar?"
        standardButtons: Kirigami.Dialog.Cancel
        customFooterActions: [
            Kirigami.Action { text: "Descartar"; icon.name: "edit-delete"; onTriggered: { studio.editor.cerrar(confirmarCerrar.editor.ruta); confirmarCerrar.close() } },
            Kirigami.Action { text: "Guardar y cerrar"; icon.name: "document-save"; onTriggered: { const e = confirmarCerrar.editor; if (e.guardar(false) === "") studio.editor.cerrar(e.ruta); confirmarCerrar.close() } }
        ]
    }
}
