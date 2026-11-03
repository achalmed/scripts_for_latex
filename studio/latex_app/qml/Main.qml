// Main.qml — LaTeX Studio (reingeniería del 2026-11-02, docs/reingenieria.md): un entorno de escritura científica,
// no una lista de archivos. Dos vistas sobre la misma ventana:
// · Proyectos (Ctrl+1): las categorías a la izquierda; los proyectos detectados con su estado y la ficha del actual;
// · Escritura (Ctrl+2): archivos, estructura y bibliografía del proyecto a la izquierda; el editor en el centro; el PDF
//   integrado a la derecha (F7); abajo, plegables (F4), Problemas explicados, el Registro, la Cola y la salida.
// La barra de arriba es la de compilación (F5/Ctrl+B compilar, Detener, F6 reconstruir, guardar, buscar, SyncTeX, PDF).
// Ninguna llamada al disco ni a un compilador aquí: lo hacen los controladores de Python (studio.*).
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun
import "componentes"

VentanaStudio {
    id: ventana

    readonly property var registro: studio.acciones
    readonly property var p: studio.proyectos
    readonly property string vista: studio.interfaz.vista
    property bool permitirCierre: false

    title: (vista === "escritura" && p.hayAbierto ? p.nombreAbierto : "Proyectos") + " — LaTeX Studio"
    acciones: registro
    tareas: studio.tareas
    consola: studio.consola
    descripcion: descripcionStudio
    autor: "Edison Achalma (@achalmed)"
    resumen: p.enDeteccion ? "buscando proyectos…" : p.total + " proyecto" + (p.total === 1 ? "" : "s")
    contexto: p.hayAbierto ? p.abierto.texto_motor + " · " + p.abierto.estado : ""
    claveAjustes: "ventana-3"
    mostrarDetalles: false

    function accion(nombre) { return registro.accion(nombre) }
    function editor() { return espacio.editorActual }
    function abrirProyecto(ruta) {
        if (!ruta) return
        const e = p.abrir(ruta)
        if (e) { ventana.mensajes.mostrar(e, "error"); return }
        studio.interfaz.fijarVista("escritura")
        espacio.abrir(p.principal, 0)
    }
    function irA(archivo, linea) {
        if (!archivo) return
        studio.interfaz.fijarVista("escritura")
        espacio.abrir(archivo, linea)
    }
    function insertar(texto) {
        const e = editor()
        if (!e) return
        e.area.insert(e.area.cursorPosition, texto)
        e.area.forceActiveFocus()
    }
    function mostrarPanel(indice) { ventana.mostrarInferior = true; panelInferior.mostrarExtra(indice) }

    onClosing: close => {
        if (studio.editor.hayModificados && !permitirCierre) { close.accepted = false; dialogoSalir.open() }
    }

    // ------------------------------------------------------------------ lo que Python pide a la interfaz
    Connections {
        target: studio.interfaz
        function onPedir(nombre, datos) {
            const e = ventana.editor()
            switch (nombre) {
            case "abrir_tex": selectorTex.abrir(p.hayAbierto ? p.abierto.carpeta : ""); break
            case "carpetas": if (ventana.dialogoAjustes) { ventana.dialogoAjustes.moduloActual = 0; ventana.dialogoAjustes.open() } break
            case "anadir_carpeta": selectorCarpeta.abrir(""); break
            case "abrir_proyecto": ventana.abrirProyecto(datos.ruta); break
            case "ir_a": ventana.irA(datos.archivo, datos.linea || 0); break
            case "seleccionar_proyecto": studio.interfaz.fijarVista("proyectos"); paginaProyectos.seleccionar(datos.fila); break
            case "guardar": espacio.guardar(e, false); break
            case "guardar_todo": espacio.guardarTodo(); break
            case "guardar_como": if (e) { guardarComo.editor = e; guardarComo.abrir(e.ruta.substring(0, e.ruta.lastIndexOf("/")), e.ruta.split("/").pop()) } break
            case "cerrar_archivo": espacio.cerrarActual(); break
            case "cerrar_proyecto": cerrarProyecto(); break
            case "editor_externo": if (e) studio.sistema.abrirEnEditorExterno(e.ruta, e.lineaActual); break
            case "buscar": if (e) espacio.buscar(false); break
            case "reemplazar": if (e) espacio.buscar(true); break
            case "ir_linea": if (e) { dialogoLinea.maximo = e.inicios.length; dialogoLinea.open() } break
            case "completar": if (e) e.completar(true); break
            case "comentar": if (e && !e.soloLectura) e.comentar(); break
            case "buscar_pdf": espacio.buscarEnPdf(); break
            case "alternar_pdf": espacio.mostrarPdf = !espacio.mostrarPdf; ventana.registro.marcar("ver.pdf", espacio.mostrarPdf); break
            case "compilar_marcados": studio.interfaz.fijarVista("proyectos"); paginaProyectos.compilarMarcados(); break
            case "synctex": if (e) studio.visor.desdeCodigo(e.ruta, e.lineaActual, e.columnaActual); break
            case "atajos": dialogoAtajos.open(); break
            case "salir": ventana.close(); break
            }
        }
    }
    function cerrarProyecto() {
        if (studio.editor.hayModificados) { ventana.mensajes.mostrar("Hay archivos con cambios sin guardar: guárdalos (Ctrl+Mayús+S) o ciérralos antes.", "aviso"); return }
        studio.editor.cerrarTodos()
        p.cerrar()
        studio.interfaz.fijarVista("proyectos")
    }

    Connections { target: studio.compilacion; function onIrA(archivo, linea) { ventana.irA(archivo, linea) } }
    Connections { target: studio.visor; function onIrACodigo(archivo, linea) { ventana.irA(archivo, linea) } }
    Connections {
        target: studio.compilacion
        function onTerminada(ruta, ok) { if (ruta === p.principal && !ok) ventana.mostrarPanel(0) }
        function onProblemasCambiados() { if (studio.compilacion.origenRegistro === "revisión de dependencias") ventana.mostrarPanel(0) }
    }
    Connections { target: p; function onAviso(texto, tipo) { ventana.mensajes.mostrar(texto, tipo) } }
    Connections { target: studio.editor; function onAviso(texto, tipo) { ventana.mensajes.mostrar(texto, tipo) } }
    Connections { target: studio.compilacion; function onAviso(texto, tipo) { ventana.mensajes.mostrar(texto, tipo) } }
    Connections { target: studio.visor; function onAviso(texto, tipo) { ventana.mensajes.mostrar(texto, tipo) } }
    Connections { target: studio.sistema; function onAviso(texto, tipo) { ventana.mensajes.mostrar(texto, tipo) } }

    Shortcut { sequence: "Ctrl+B"; onActivated: if (ventana.accion("compilar.compilar").habilitada) studio.compilacion.compilar() }

    // soltar un .tex en la ventana abre su proyecto
    DropArea {
        anchors.fill: parent
        keys: ["text/uri-list"]
        onDropped: drop => {
            const tex = drop.urls.map(u => u.toString()).filter(u => u.startsWith("file://") && u.toLowerCase().endsWith(".tex"))
            if (tex.length === 0) { ventana.mensajes.mostrar("Eso no es un .tex.", "aviso"); return }
            ventana.abrirProyecto(decodeURIComponent(tex[0].substring(7)))
            drop.acceptProposedAction()
        }
    }

    // ------------------------------------------------------------------ la barra de compilación: el proyecto abierto
    herramientasExtra: [
        RowLayout {
            spacing: Kirigami.Units.smallSpacing
            visible: p.hayAbierto
            Kirigami.Icon { source: p.hayAbierto && p.abierto.icono ? p.abierto.icono.estado : ""; implicitWidth: Kirigami.Units.iconSizes.small; implicitHeight: implicitWidth }
            QQC2.Label {
                text: p.hayAbierto ? p.nombreAbierto : ""
                elide: Text.ElideMiddle
                Layout.maximumWidth: Kirigami.Units.gridUnit * 18
            }
            QQC2.Label {
                text: p.hayAbierto ? p.abierto.texto_motor : ""
                color: Kirigami.Theme.disabledTextColor
                QQC2.ToolTip.text: p.hayAbierto ? "Motor: " + p.abierto.motor_origen + " · compilador: " + p.abierto.compilador_texto : ""
                QQC2.ToolTip.visible: zonaMotor.hovered
                HoverHandler { id: zonaMotor }
            }
        }
    ]

    // ------------------------------------------------------------------ las ranuras
    navegacion: BarraLateral {
        onAbrirArchivo: (ruta, linea) => ventana.irA(ruta, linea)
        onCitar: clave => ventana.insertar("\\cite{" + clave + "}")
    }

    centro: StackLayout {
        currentIndex: ventana.vista === "escritura" ? 1 : 0
        PaginaProyectos { id: paginaProyectos; onAbrir: ruta => ventana.abrirProyecto(ruta) }
        EspacioEscritura { id: espacio }
    }

    inferior: PanelInferior {
        id: panelInferior
        consola: studio.consola
        altoPreferido: Kirigami.Units.gridUnit * 11
        extras: [{ titulo: "Problemas", componente: cProblemas }, { titulo: "Registro de LaTeX", componente: cRegistro }, { titulo: "Cola", componente: cCola }, { titulo: "Historial", componente: cHistorial }]
    }
    Component { id: cProblemas; ListaProblemas {} }
    Component { id: cRegistro; RegistroCompilacion {} }
    Component { id: cCola; Cola {} }
    Component { id: cHistorial; HistorialCompilaciones {} }

    // ------------------------------------------------------------------ diálogos (archivos y carpetas: los de KDE, de gui-comun 3.0)
    ElegirArchivos {
        id: selectorTex
        titulo: "Abrir un .tex"
        filtros: ["Documentos LaTeX (*.tex)"]
        onElegido: ruta => ventana.abrirProyecto(ruta)
    }
    ElegirCarpeta {
        id: selectorCarpeta
        titulo: "Añadir una carpeta de trabajo"
        onElegida: ruta => { const e = studio.ajustes.anadirCarpeta(ruta); if (e) ventana.mensajes.mostrar(e, "error") }
    }
    GuardarComo {
        id: guardarComo
        property var editor: null
        titulo: "Guardar como"
        filtros: ["Documentos LaTeX (*.tex)", "Bibliografía (*.bib)"]
        conTodos: true
        onElegido: ruta => {
            const e = guardarComo.editor
            if (!e) return
            const r = studio.editor.guardarComo(e.ruta, ruta, e.area.text)
            if (r) ventana.mensajes.mostrar(r, "error"); else { e.original = e.area.text; e.modificado = false }
        }
    }
    Kirigami.PromptDialog {
        id: dialogoSalir
        title: "Cambios sin guardar"
        subtitle: "Hay archivos con cambios sin guardar: " + studio.editor.modificados.map(r => r.split("/").pop()).join(", ") + "."
        standardButtons: Kirigami.Dialog.Cancel
        customFooterActions: [
            Kirigami.Action { text: "Salir sin guardar"; icon.name: "application-exit"; onTriggered: { ventana.permitirCierre = true; dialogoSalir.close(); ventana.close() } },
            Kirigami.Action { text: "Guardar todo y salir"; icon.name: "document-save-all"; onTriggered: { espacio.guardarTodo(); dialogoSalir.close(); if (!studio.editor.hayModificados) { ventana.permitirCierre = true; ventana.close() } } }
        ]
    }
    Kirigami.Dialog {
        id: dialogoLinea
        property int maximo: 1
        title: "Ir a la línea"
        standardButtons: Kirigami.Dialog.Ok | Kirigami.Dialog.Cancel
        padding: Kirigami.Units.largeSpacing
        onOpened: { campoLinea.value = ventana.editor() ? ventana.editor().lineaActual : 1; campoLinea.contentItem.forceActiveFocus(); campoLinea.contentItem.selectAll() }
        onAccepted: { const e = ventana.editor(); if (e) e.irALinea(campoLinea.value, 0) }
        RowLayout {
            QQC2.Label { text: "Línea (1–" + dialogoLinea.maximo + "):" }
            QQC2.SpinBox { id: campoLinea; from: 1; to: dialogoLinea.maximo; editable: true; Accessible.name: "Línea"; Keys.onReturnPressed: dialogoLinea.accept() }
        }
    }
    Kirigami.Dialog {
        id: dialogoAtajos
        title: "Atajos de teclado"
        standardButtons: Kirigami.Dialog.Close
        preferredWidth: Kirigami.Units.gridUnit * 30
        preferredHeight: Kirigami.Units.gridUnit * 28
        ListView {
            id: listaAtajos
            clip: true
            model: studio.acciones
            section.property: "grupo"
            section.delegate: Kirigami.ListSectionHeader { required property string section; width: listaAtajos.width; text: section }
            delegate: QQC2.ItemDelegate {
                required property var model
                width: listaAtajos.width
                visible: model.atajo !== ""
                height: visible ? implicitHeight : 0
                contentItem: RowLayout {
                    QQC2.Label { text: model.texto.replace("&", ""); Layout.fillWidth: true; elide: Text.ElideRight }
                    QQC2.Label { text: model.objeto ? model.objeto.atajoTexto : model.atajo; font.family: Kirigami.Theme.fixedWidthFont.family; color: Kirigami.Theme.disabledTextColor }
                }
            }
            footer: QQC2.Label {
                width: listaAtajos.width
                padding: Kirigami.Units.largeSpacing
                wrapMode: Text.WordWrap
                color: Kirigami.Theme.disabledTextColor
                text: "Además: Ctrl+B compila (como F5); Ctrl+clic en el editor va al PDF (SyncTeX); doble clic en el PDF vuelve al código; Ctrl+rueda en el PDF cambia el zoom; Intro en la búsqueda va a la siguiente, Mayús+Intro a la anterior; Ctrl+K abre la paleta de órdenes."
            }
        }
    }
    dialogoAjustes: DialogoAjustesStudio {}
}
