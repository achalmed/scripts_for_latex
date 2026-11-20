// EspacioEscritura — la vista Escritura: a la izquierda (en el centro de la ventana) las pestañas de los archivos
// abiertos, la barra de insertar (sección, figura, tabla, cita, ecuación, referencia, lista, negrita, cursiva, nota; el
// rediseño del 2026-11-17, §1.17), el editor, la franja del primer problema con su arreglo y su línea, y abajo dónde estás
// y cuántas palabras lleva el archivo; a la derecha el PDF integrado (F7 lo oculta). Cada archivo abierto
// tiene su EditorTexto de gui-comun (su texto y su deshacer); el aviso de «cambió fuera» y la confirmación de sobrescribir viven
// aquí. Sin datos propios: studio.editor (abiertos), studio.visor, studio.proyectos.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

QQC2.SplitView {
    id: raiz

    property bool mostrarPdf: !studio.ajustes.visorOkular       // a la derecha del código, salvo con Okular en su ventana (Ajustes); F7 lo alterna
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
    function cerrarActual() { if (editorActual) cerrar(editorActual.ruta) }
    // cerrar un archivo abierto: con cambios sin guardar pregunta antes (Guardar · Descartar · Cancelar); guardar que
    // falla o que pisaría un cambio externo deja el archivo abierto con su aviso
    function cerrar(ruta) {
        const e = editorDe(ruta)
        if (!e) { studio.editor.cerrar(ruta); return }
        if (!e.modificado) { studio.editor.cerrar(ruta); return }
        studio.editor.fijarActual(ruta)
        confirmarCerrar.pedir(ruta.split("/").pop(), () => {
            const r = e.guardar(false)
            if (r === "") studio.editor.cerrar(ruta)
            else if (r === "externo") { confirmarSobrescribir.editor = e; confirmarSobrescribir.open() }
            else ventana.mensajes.mostrar(r, "error")
        }, () => studio.editor.cerrar(ruta))
    }

    Connections {
        target: studio.editor
        function onCambioExterno(ruta) {
            const e = raiz.editorDe(ruta)
            if (!e) return
            if (!e.modificado) { e.recargarDesdeDisco(); ventana.mensajes.mostrar(ruta.split("/").pop() + " cambió fuera de la ventana: recargado.", "informacion") }
            // Con cambios sin guardar es una decisión: va a las notificaciones de KDE con sus dos botones, no a una franja en
            // la ventana (pedido del autor, 2026-11-19: ningún aviso dentro de la ventana en la familia de los studios)
            else ventana.mensajes.notificarConAcciones(ruta.split("/").pop() + " cambió en el disco y aquí tiene cambios sin guardar.", "aviso", [
                { texto: "Recargar del disco", icono: "view-refresh", ejecutar: () => { const x = raiz.editorDe(ruta); if (x) x.recargarDesdeDisco() } },
                { texto: "Mantener lo mío", icono: "dialog-ok", ejecutar: () => {} }])
        }
    }

    ColumnLayout {
        QQC2.SplitView.fillWidth: true
        QQC2.SplitView.minimumWidth: Kirigami.Units.gridUnit * 20
        spacing: 0

        // las pestañas de los archivos abiertos (PestanasArchivos de gui-comun 4.2): la × (al pasar el ratón y siempre en
        // la activa) y el clic central piden cerrar; Ctrl+W es la acción archivo.cerrar. Sin archivos no ocupa nada.
        PestanasArchivos {
            Layout.fillWidth: true
            controlador: studio.editor
            onCerrarPedido: ruta => raiz.cerrar(ruta)
        }

        // la barra de insertar: el LaTeX de memoria, en un formulario corto (DialogoInsertar en Main). Las opciones en
        // pozos (GrupoOpciones) por familia —estructura, objetos, referencias, formato— y como píldoras de la base
        // (OpcionColor) con iconos monocromos: antes, nueve botones con borde de iconos mezclados que partían la línea
        Flow {
            Layout.fillWidth: true
            Layout.margins: Kirigami.Units.smallSpacing
            visible: raiz.editorActual !== null && !raiz.editorActual.soloLectura
            spacing: Kirigami.Units.smallSpacing
            Repeater {
                model: [
                    [{ tipo: "seccion", texto: "Sección", icono: "view-list-tree-symbolic", ayuda: "Un capítulo, sección o subsección con su etiqueta" },
                     { tipo: "lista", texto: "Lista", icono: "format-list-unordered-symbolic", ayuda: "Con viñetas o numerada, un elemento por línea" }],
                    [{ tipo: "figura", texto: "Figura", icono: "insert-image-symbolic", ayuda: "Una imagen con su título, etiqueta, ancho y fuente" },
                     { tipo: "tabla", texto: "Tabla", icono: "insert-table-symbolic", ayuda: "Una tabla escrita celda por celda (booktabs)" },
                     { tipo: "ecuacion", texto: "Ecuación", icono: "formula-symbolic", ayuda: "Numerada o no, con su etiqueta" }],
                    [{ tipo: "cita", texto: "Cita", icono: "format-text-blockquote-symbolic", ayuda: "Una o varias entradas de los .bib del proyecto" },
                     { tipo: "referencia", texto: "Referencia", icono: "insert-link-symbolic", ayuda: "A una figura, tabla, sección o ecuación con \\label" }]
                ]
                delegate: GrupoOpciones {
                    id: grupoInsertar
                    required property var modelData
                    titulo: "Insertar"
                    Repeater {
                        model: grupoInsertar.modelData
                        delegate: OpcionColor {
                            required property var modelData
                            text: modelData.texto
                            icon.name: modelData.icono
                            compacta: true
                            descripcion: modelData.ayuda
                            onClicked: ventana.pedirInsertar(modelData.tipo)
                        }
                    }
                }
            }
            GrupoOpciones {
                titulo: "Formato"
                OpcionColor { icon.name: "format-text-bold-symbolic"; compacta: true; descripcion: "Negrita (\\textbf) sobre lo elegido"; Accessible.name: "Negrita"; onClicked: ventana.envolver("\\textbf{", "}") }
                OpcionColor { icon.name: "format-text-italic-symbolic"; compacta: true; descripcion: "Énfasis (\\emph) sobre lo elegido"; Accessible.name: "Énfasis"; onClicked: ventana.envolver("\\emph{", "}") }
                OpcionColor { icon.name: "format-text-superscript-symbolic"; compacta: true; descripcion: "Nota al pie (\\footnote) con lo elegido"; Accessible.name: "Nota al pie"; onClicked: ventana.envolver("\\footnote{", "}") }
            }
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
                    revisarOrtografia: studio.ajustes.revisarOrtografia
                    tamanoLetra: studio.ajustes.tamanoLetra
                    completar: raiz.completarLatex
                    disparaCompletado: raiz.disparaLatex
                    Component.onCompleted: cargar()
                    onCtrlClic: (linea, columna) => ventana.alPdf(ruta, linea, columna)
                }
            }
        }

        Kirigami.PlaceholderMessage {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: studio.editor.abiertos.filas === 0
            icon.name: "document-edit-symbolic"
            text: studio.proyectos.hayAbierto ? "Elige un archivo del proyecto" : "Ningún proyecto abierto"
            explanation: studio.proyectos.hayAbierto ? "Los archivos del proyecto (el principal, sus \\input y sus .bib) están a la izquierda; la estructura, en la pestaña de al lado."
                                                     : "Ctrl+1 muestra los proyectos detectados; Ctrl+O abre un .tex."
        }

        // el primer problema de la última compilación, con su causa, su arreglo y su línea (todos: el panel de abajo, F4)
        Rectangle {
            id: franja
            readonly property var c: studio.compilacion
            readonly property var primero: { c.nProblemas; c.mostrarErrores; c.mostrarAvisos; return c.nProblemas > 0 ? c.problema(0) : ({}) }
            readonly property bool esError: primero.nivel === "error"
            Layout.fillWidth: true
            Layout.margins: Kirigami.Units.smallSpacing
            visible: studio.proyectos.hayAbierto && c.nProblemas > 0 && !!primero.nivel
            implicitHeight: filaFranja.implicitHeight + Kirigami.Units.smallSpacing * 2
            radius: Kirigami.Units.cornerRadius
            color: Qt.alpha(esError ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.neutralTextColor, 0.12)
            border.width: 1
            border.color: Qt.alpha(esError ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.neutralTextColor, 0.35)
            RowLayout {
                id: filaFranja
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing
                anchors.leftMargin: Kirigami.Units.largeSpacing
                spacing: Kirigami.Units.smallSpacing
                QQC2.Label { text: "●"; color: franja.esError ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.neutralTextColor; Accessible.ignored: true }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    QQC2.Label { Layout.fillWidth: true; text: franja.primero.titulo || franja.primero.mensaje || ""; elide: Text.ElideRight; font.weight: Font.Medium }
                    QQC2.Label { Layout.fillWidth: true; visible: !!franja.primero.accion; text: franja.primero.accion || ""; elide: Text.ElideRight; font: Kirigami.Theme.smallFont
                                 color: Kirigami.Theme.disabledTextColor }
                }
                QQC2.Label { text: franja.c.nProblemas > 1 ? "1 de " + franja.c.nProblemas : ""; font: Kirigami.Theme.smallFont; color: Kirigami.Theme.disabledTextColor }
                QQC2.Button { text: "Ir a la línea"; visible: (franja.primero.linea || 0) > 0; onClicked: franja.c.elegir(0); QQC2.ToolTip.text: (franja.primero.relativa || "") + ":" + (franja.primero.linea || ""); QQC2.ToolTip.visible: hovered && QQC2.ToolTip.text !== ""; QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay }
                QQC2.Button { text: "Siguiente"; visible: franja.c.nProblemas > 1; onClicked: franja.c.siguiente(); QQC2.ToolTip.text: "F8"; QQC2.ToolTip.visible: hovered && QQC2.ToolTip.text !== ""; QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay }
                QQC2.Button { text: "Ver todos"; onClicked: ventana.mostrarPanel(0); QQC2.ToolTip.text: "El panel de problemas, con la causa y el registro (F4)"; QQC2.ToolTip.visible: hovered && QQC2.ToolTip.text !== ""; QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay }
            }
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
                    text: raiz.palabras > 0 ? raiz.palabras.toLocaleString(Qt.locale("es_PE"), "f", 0) + " palabras" : ""
                    font: Kirigami.Theme.smallFont
                    color: Kirigami.Theme.disabledTextColor
                    QQC2.ToolTip.text: "Palabras del archivo abierto, sin órdenes ni comentarios"
                    QQC2.ToolTip.visible: zonaPalabras.hovered
                    HoverHandler { id: zonaPalabras }
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

    // las palabras del archivo abierto, sin comentarios, órdenes ni sus opciones; se cuentan tras una pausa al escribir
    property int palabras: 0
    function contarPalabras() {
        const e = editorActual
        if (!e || !e.area) { palabras = 0; return }
        const limpio = e.area.text.replace(/(^|[^\\])%.*$/gm, "$1").replace(/\\[A-Za-z@]+\*?(\[[^\]]*\])?/g, " ").replace(/[{}$&_^~]/g, " ")
        const m = limpio.match(/[A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñÀ-ÿ][A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñÀ-ÿ'’-]*/g)   // V4 no conoce \p{L}
        palabras = m ? m.length : 0
    }
    Timer { id: pausaPalabras; interval: 700; onTriggered: raiz.contarPalabras() }
    onEditorActualChanged: pausaPalabras.restart()
    Connections { target: raiz.editorActual ? raiz.editorActual.area : null; ignoreUnknownSignals: true; function onTextChanged() { pausaPalabras.restart() } }

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
        showCloseButton: false            // ya hay botones al pie: sin la × roja del encabezado
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
    DialogoCambiosSinGuardar {
        id: confirmarCerrar
        explicacion: "Si lo cierras sin guardar, esos cambios se pierden."
    }
}
