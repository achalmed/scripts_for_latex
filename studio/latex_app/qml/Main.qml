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
    // del código al PDF (Ctrl+clic, Ctrl+Alt+J): en Okular si es el visor elegido; si no, en el integrado
    function alPdf(ruta, linea, columna) {
        if (studio.ajustes.visorOkular && studio.sistema.hayOkular && !espacio.mostrarPdf)
            studio.sistema.abrirEnOkular(p.hayAbierto ? p.abierto.pdf : "", ruta, linea)
        else
            studio.visor.desdeCodigo(ruta, linea, columna)
    }
    function insertar(texto) {
        const e = editor()
        if (!e) return
        e.area.insert(e.area.cursorPosition, texto)
        e.area.forceActiveFocus()
    }
    function mostrarPanel(indice) { ventana.mostrarInferior = true; panelInferior.mostrarExtra(indice) }
    function pedirInsertar(tipo) { if (ventana.editor()) dialogoInsertar.abrir(tipo) }
    // envuelve lo elegido (o deja el cursor dentro) con una orden: negrita, énfasis, nota al pie
    function envolver(antes, despues) {
        const e = editor()
        if (!e || e.soloLectura) return
        const a = e.area, i = a.selectionStart, f = a.selectionEnd, elegido = a.selectedText
        a.remove(i, f)
        a.insert(i, antes + elegido + despues)
        a.cursorPosition = elegido ? i + antes.length + elegido.length + despues.length : i + antes.length
        a.forceActiveFocus()
    }

    onClosing: close => {
        if (studio.editor.hayModificados && !permitirCierre) { close.accepted = false; dialogoSalir.open() }
    }

    // ------------------------------------------------------------------ lo que Python pide a la interfaz
    Connections {
        target: studio.interfaz
        function onPedir(nombre, datos) {
            const e = ventana.editor()
            switch (nombre) {
            case "nuevo_documento": dialogoNuevo.abrir(datos); break
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
            case "completar": if (e) e.abrirSugerencias(true); break
            case "comentar": if (e && !e.soloLectura) e.comentar(); break
            case "buscar_pdf": espacio.buscarEnPdf(); break
            case "alternar_pdf": espacio.mostrarPdf = !espacio.mostrarPdf; ventana.registro.marcar("ver.pdf", espacio.mostrarPdf); break
            case "compilar_marcados": studio.interfaz.fijarVista("proyectos"); paginaProyectos.compilarMarcados(); break
            case "synctex": if (e) ventana.alPdf(e.ruta, e.lineaActual, e.columnaActual); break
            case "ir_a_fuera": ventana.irA(datos.archivo, datos.linea || 0); ventana.raise(); ventana.requestActivate(); break
            case "configurar_okular": dialogoOkular.abrir(); break
            case "atajos": dialogoAtajos.open(); break
            case "configurar_documento": dialogoConfigurar.abrirPara(datos.ruta || ""); break
            case "ayuda_ia": dialogoAyuda.abrirPara(e, datos.pegado || ""); break
            case "nueva_ficha": dialogoFicha.nuevaPara(datos.libro || null, datos); break
            case "insertar": ventana.pedirInsertar(datos.tipo || "seccion"); break
            case "configurar_texstudio": dialogoTexstudio.abrir(); break
            case "texstudio":
                if (e) studio.sistema.abrirEnTexstudio(e.ruta, e.lineaActual, p.hayAbierto ? p.principal : "")
                else if (datos.ruta || p.hayAbierto) studio.sistema.abrirEnTexstudio(datos.ruta || p.principal, 1, datos.ruta || p.principal)
                break
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
    Connections {
        target: studio.visor
        // doble clic en el PDF (SyncTeX): al código aquí o, si se eligió en Ajustes, en TeXstudio
        function onIrACodigo(archivo, linea) {
            if (studio.ajustes.saltarATexstudio && studio.sistema.hayTexstudio) studio.sistema.abrirEnTexstudio(archivo, linea, p.hayAbierto ? p.principal : "")
            else ventana.irA(archivo, linea)
        }
    }
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
    // citar un libro de la biblioteca: en el cursor; si aún no es fuente del proyecto, el marco lo añade tras confirmar
    Connections {
        target: studio.biblioteca
        function onCitado(texto) { if (texto) ventana.insertar(texto) }
        function onPedirConfirmacion(id, titulo, clave) {
            ventana.confirmacion.pedir({ titulo: "Citar «" + titulo + "»",
                                         consecuencias: "Todavía no es fuente de este documento: se añade a sus fuentes (fuentes/fuentes.yml) con la clave " + clave
                                                        + " y se regenera su references.bib; luego se cita en el cursor. El texto no se toca.",
                                         operacionTexto: "escritura", textoAceptar: "Añadir y citar", icono: "format-text-blockquote" },
                                       () => studio.biblioteca.citarAplicando(id))
        }
    }

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

    // ------------------------------------------------------------------ la barra de arriba (rediseño del 2026-11-17, §1.17)
    // Ligera, como la de Datafw Studio: en Proyectos, «Tus documentos» y sus acciones; en Escritura, el documento, el
    // estado de su última compilación en una línea y tres acciones (Compilar, Configurar y, si el marco lo declara, el
    // programa de sus datos). Todo lo demás sigue en los menús, en ⋮ (todas las órdenes) y en la paleta (Ctrl+K).
    readonly property bool escribiendo: vista === "escritura" && p.hayAbierto
    readonly property var fichaAbierta: { p.tarjetas; studio.compilacion.enCurso; return p.hayAbierto ? p.datos(p.principal) : ({}) }
    readonly property bool compilando: studio.compilacion.enCurso && studio.compilacion.rutaEnCurso === p.principal
    header: ColumnLayout {
        spacing: 0
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: Kirigami.Units.smallSpacing
            Layout.leftMargin: Kirigami.Units.largeSpacing
            Layout.rightMargin: Kirigami.Units.largeSpacing
            spacing: Kirigami.Units.smallSpacing

            // --- Proyectos
            QQC2.Label { visible: !ventana.escribiendo; text: "Tus documentos"; font.weight: Font.Medium }
            QQC2.Label { visible: !ventana.escribiendo; text: ventana.resumen; color: Kirigami.Theme.disabledTextColor; font: Kirigami.Theme.smallFont }

            // --- Escritura
            QQC2.ToolButton {
                visible: ventana.escribiendo
                icon.name: "go-previous"
                display: QQC2.AbstractButton.IconOnly
                text: "Tus documentos (Ctrl+1)"
                Accessible.name: text
                onClicked: studio.interfaz.fijarVista("proyectos")
                QQC2.ToolTip.text: text
                QQC2.ToolTip.visible: hovered
            }
            ColumnLayout {
                visible: ventana.escribiendo
                spacing: 0
                Layout.maximumWidth: Kirigami.Units.gridUnit * 26
                QQC2.Label {
                    Layout.fillWidth: true
                    text: p.hayAbierto ? (p.abierto.titulo || p.nombreAbierto) : ""
                    font.weight: Font.Medium
                    elide: Text.ElideRight
                }
                QQC2.Label {
                    Layout.fillWidth: true
                    text: p.hayAbierto ? (ventana.fichaAbierta.tipo || p.abierto.clase || "") + " · " + p.abierto.texto_motor : ""
                    font: Kirigami.Theme.smallFont
                    color: Kirigami.Theme.disabledTextColor
                    elide: Text.ElideRight
                    QQC2.ToolTip.text: p.hayAbierto ? "Motor: " + p.abierto.motor_origen + " · compilador: " + p.abierto.compilador_texto : ""
                    QQC2.ToolTip.visible: zonaMotor.hovered
                    HoverHandler { id: zonaMotor }
                }
            }
            Item { Layout.fillWidth: true }

            // el estado de la última compilación, en una línea
            RowLayout {
                visible: ventana.escribiendo
                spacing: Kirigami.Units.smallSpacing
                Rectangle {
                    implicitWidth: Kirigami.Units.smallSpacing * 2; implicitHeight: implicitWidth; radius: width / 2
                    color: ventana.compilando ? Kirigami.Theme.activeTextColor
                         : ventana.fichaAbierta.nivel === "negativo" ? Kirigami.Theme.negativeTextColor
                         : ventana.fichaAbierta.nivel === "neutro" ? Kirigami.Theme.neutralTextColor
                         : ventana.fichaAbierta.nivel === "positivo" ? Kirigami.Theme.positiveTextColor : Kirigami.Theme.disabledTextColor
                }
                QQC2.Label {
                    text: ventana.compilando ? "Compilando…"
                          : (ventana.fichaAbierta.estado || "") + (ventana.fichaAbierta.hace && ventana.fichaAbierta.hace !== "nunca" ? " " + ventana.fichaAbierta.hace : "")
                            + (ventana.fichaAbierta.problemas && ventana.fichaAbierta.problemas !== "—" && ventana.fichaAbierta.problemas !== "ninguno" ? " · " + ventana.fichaAbierta.problemas : "")
                    font: Kirigami.Theme.smallFont
                    color: Kirigami.Theme.disabledTextColor
                }
                Item { implicitWidth: Kirigami.Units.smallSpacing }
            }
            QQC2.BusyIndicator { running: studio.tareas.activa; visible: running; implicitWidth: Kirigami.Units.iconSizes.smallMedium; implicitHeight: implicitWidth }

            Chip {
                visible: ventana.escribiendo
                text: ventana.compilando ? "Detener" : "Compilar"
                icono: ventana.compilando ? "process-stop" : "run-build"
                destacado: !ventana.compilando
                ayuda: ventana.compilando ? "Detener la compilación (Esc)" : "Compilar con su compilador y su motor (F5 o Ctrl+B)"
                onClicked: ventana.accion(ventana.compilando ? "compilar.cancelar" : "compilar.compilar").disparar()
            }
            Chip {
                visible: ventana.escribiendo
                text: "Configurar"
                icono: "document-properties"
                ayuda: "Título, autor, tema y opciones de la clase (Ctrl+Alt+D)"
                onClicked: studio.interfaz.pedir("configurar_documento", { ruta: p.principal })
            }
            Chip {
                visible: ventana.escribiendo && studio.datos.productor !== ""
                text: studio.datos.productor
                icono: "office-chart-bar"
                ayuda: "Hacer o rehacer las figuras y tablas de este documento"
                onClicked: studio.datos.abrirProductor()
            }
            Chip {
                visible: ventana.escribiendo
                text: "PDF"
                icono: "application-pdf"
                destacado: false
                ayuda: "Mostrar u ocultar el PDF al lado del código (F7)"
                onClicked: studio.interfaz.pedir("alternar_pdf", {})
            }

            Chip { visible: !ventana.escribiendo; text: "Nuevo documento"; icono: "document-new"; ayuda: "Un informe, una tesis, un artículo… con la estructura de su marco (Ctrl+N)"
                   onClicked: studio.interfaz.pedir("nuevo_documento", {}) }
            Chip { visible: !ventana.escribiendo; text: "Abrir un .tex"; icono: "document-open"; ayuda: "Ctrl+O"; onClicked: studio.interfaz.pedir("abrir_tex", {}) }
            Chip { visible: !ventana.escribiendo; text: "Compilar los marcados"; icono: "run-build"; ayuda: "Marca con Ctrl+clic; se compilan uno tras otro (Ctrl+Mayús+F5)"
                   onClicked: paginaProyectos.compilarMarcados() }
            Chip { visible: !ventana.escribiendo && p.hayAbierto; text: "Volver a " + (p.hayAbierto ? (p.abierto.titulo || p.nombreAbierto) : "")
                   icono: "go-next"; onClicked: studio.interfaz.fijarVista("escritura"); ayuda: "El documento abierto (Ctrl+2)" }

            BotonAccion { visible: ventana.existe("ventana.navegacion"); accion: ventana.existe("ventana.navegacion") ? ventana.acciones.accion("ventana.navegacion") : null; conTexto: false; flat: true }
            BotonAccion { visible: ventana.existe("ventana.inferior"); accion: ventana.existe("ventana.inferior") ? ventana.acciones.accion("ventana.inferior") : null; conTexto: false; flat: true }
            QQC2.ToolButton {
                icon.name: "overflow-menu"
                text: "Todas las órdenes"
                display: QQC2.AbstractButton.IconOnly
                Accessible.name: text
                QQC2.ToolTip.text: text + " (también Ctrl+K)"
                QQC2.ToolTip.visible: hovered
                onClicked: menuTodo.popup()
                MenuAcciones { id: menuTodo; acciones: ventana.acciones; conAtajos: true; elementos: ventana.acciones ? ventana.acciones.menus : [] }
            }
        }
        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Qt.alpha(Kirigami.Theme.textColor, 0.1) }
    }

    // ------------------------------------------------------------------ las ranuras
    navegacion: BarraLateral {
        onAbrirArchivo: (ruta, linea) => ventana.irA(ruta, linea)
        onCitar: clave => ventana.insertar("\\cite{" + clave + "}")
        onInsertarDatos: texto => ventana.insertar(texto)
        onActualizarDatos: ventana.confirmacion.pedir({ titulo: "Actualizar los datos del proyecto",
                                                        consecuencias: "Lleva el proyecto a la última versión de sus paquetes (su ficha) y vuelve a escribir sus figuras, tablas y cifras importadas. El texto del documento no se toca.",
                                                        operacionTexto: "actualización", textoAceptar: "Actualizar", icono: "view-refresh" },
                                                      () => studio.datos.actualizar())
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
    // los problemas de la compilación: ListaErrores de gui-comun 3.1, con los filtros por nivel de LaTeX en su cabecera
    Component {
        id: cProblemas
        ListaErrores {
            id: listaProblemas
            readonly property var c: studio.compilacion
            modelo: c.problemas
            Connections { target: listaProblemas.c; function onProblemasCambiados() { listaProblemas.actual = listaProblemas.c.problemaActual } }
            nombreAccesible: "Problemas"
            onElegido: (indice) => c.elegir(indice)
            iconoVacio: c.origenRegistro !== "" && c.nProblemas === 0 ? "data-success" : "data-information"
            mensajeVacio: !studio.proyectos.hayAbierto ? "Ningún proyecto abierto"
                          : c.origenRegistro === "" ? "Sin registro todavía" : c.nProblemas === 0 ? "Sin errores ni avisos" : "Todos los problemas están filtrados"
            explicacionVacia: studio.proyectos.hayAbierto && c.origenRegistro === "" ? "Compila (F5) para leer los errores y avisos con su archivo y su línea." : ""
            cabecera: [
                QQC2.ToolButton { checkable: true; checked: listaProblemas.c.mostrarErrores; onToggled: listaProblemas.c.mostrarErrores = checked; icon.name: "data-error"; text: listaProblemas.c.nErrores; Accessible.name: "Errores: " + listaProblemas.c.nErrores; QQC2.ToolTip.text: "Errores"; QQC2.ToolTip.visible: hovered },
                QQC2.ToolButton { checkable: true; checked: listaProblemas.c.mostrarAvisos; onToggled: listaProblemas.c.mostrarAvisos = checked; icon.name: "data-warning"; text: listaProblemas.c.nAvisos; Accessible.name: "Avisos: " + listaProblemas.c.nAvisos; QQC2.ToolTip.text: "Avisos"; QQC2.ToolTip.visible: hovered },
                QQC2.ToolButton { checkable: true; checked: listaProblemas.c.mostrarTipografia; onToggled: listaProblemas.c.mostrarTipografia = checked; icon.name: "format-justify-fill"; text: listaProblemas.c.nTipografia; Accessible.name: "Tipografía: " + listaProblemas.c.nTipografia; QQC2.ToolTip.text: "Avisos tipográficos (Overfull, Underfull)"; QQC2.ToolTip.visible: hovered },
                QQC2.Label { Layout.fillWidth: true; text: listaProblemas.c.origenRegistro ? "de " + listaProblemas.c.origenRegistro.split("/").pop() : ""; elide: Text.ElideMiddle; font: Kirigami.Theme.smallFont; color: Kirigami.Theme.disabledTextColor },
                QQC2.Button { text: "Revisar dependencias"; icon.name: "tools-check-spelling"; flat: true; enabled: studio.proyectos.hayAbierto; onClicked: listaProblemas.c.revisarDependencias("") }
            ]
        }
    }
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
    DialogoInsertar { id: dialogoInsertar; onInsertar: texto => ventana.insertar(texto) }
    DialogoConfigurarDocumento { id: dialogoConfigurar }
    DialogoFicha { id: dialogoFicha }                  // Citas › Fichas: nueva y editar (§1.19)
    DialogoAyudaIA { id: dialogoAyuda }                // la ayuda de la IA de la parte abierta (§1.19)
    DialogoNuevo { id: dialogoNuevo }                  // «Nuevo documento» (Ctrl+N): lo que el marco sabe crear (§1.20)
    DialogoTexstudio { id: dialogoTexstudio }
    DialogoTexstudio {
        id: dialogoOkular
        title: "Volver del PDF al código desde Okular"
        programa: "Okular"
        estadoDe: () => studio.sistema.estadoOkular()
        aplicarDe: () => studio.sistema.configurarOkular()
        deshacerDe: () => studio.sistema.deshacerOkular()
        explicacion: "Con esto, Mayús+clic sobre el PDF en Okular abre el código en esta ventana, en esa línea (SyncTeX), "
                   + "y Ctrl+clic en el editor lleva al punto del PDF en Okular. Se cambian solo estas claves (su editor externo) de "
        hecho: "Listo: Mayús+clic en Okular vuelve al código en LaTeX Studio."
        yaEsta: "Okular ya vuelve al código en esta ventana con Mayús+clic."
    }
    dialogoAjustes: DialogoAjustesStudio {}
}
