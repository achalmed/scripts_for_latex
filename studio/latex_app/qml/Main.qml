// Main.qml — LaTeX Studio: los documentos .tex de una carpeta, su estado y su compilación en un espacio de trabajo al
// estilo Dolphin/Kate sobre GuiComun.VentanaStudio. Navegación (Carpeta de trabajo · Recientes · Compilaciones · las
// carpetas recientes) · centro (la tabla de documentos o la del historial) · detalles del documento actual (Resumen ·
// Opciones · Problemas · Registro · Salidas) · panel inferior (la salida de main.sh; Registro) · barra de estado. Ninguna
// llamada al disco ni a main.sh aquí: todo lo hacen los controladores de Python (studio.*).
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import QtQuick.Dialogs
import org.kde.kirigami as Kirigami
import GuiComun
import "componentes"

VentanaStudio {
    id: ventana

    readonly property var espacio: studio.espacio
    readonly property var registro: studio.acciones
    readonly property var docs: studio.documentos
    readonly property string vista: espacio.vista
    readonly property int indice: espacio.indiceVista

    title: espacio.nombreCarpeta + " — LaTeX Studio"
    acciones: registro
    tareas: studio.tareas
    consola: studio.consola
    descripcion: descripcionStudio
    autor: "Edison Achalma (@achalmed)"
    resumen: espacio.resumen
    contexto: espacio.contexto
    claveAjustes: "ventana"

    function accion(nombre) { return registro.accion(nombre) }
    function tablaActual() { return centro.children[ventana.indice] }
    function irAPestana(i) { ventana.mostrarDetalles = true; detalles.pestanaActual = i }
    function religarNavegacion() { navegacion.actual = Qt.binding(() => ventana.vista) }
    function seleccionarDocumento(ruta) {
        const fila = docs.filaDe(ruta)
        if (fila >= 0 && ventana.vista === "carpeta") tablaCarpeta.seleccionarFila(fila, true)
    }

    // ------------------------------------------------------------------ lo que Python pide a la interfaz
    Connections {
        target: studio.interfaz
        function onPedir(nombre, datos) {
            switch (nombre) {
            case "abrir_tex": selectorTex.currentFolder = "file://" + espacio.carpeta; selectorTex.open(); break
            case "carpeta": selectorCarpeta.currentFolder = "file://" + espacio.carpeta; selectorCarpeta.open(); break
            case "filtrar": filtro.forceActiveFocus(); filtro.selectAll(); break
            case "seleccionar_todo": { const t = tablaActual(); if (t && t.seleccionarTodo) t.seleccionarTodo(); break }
            case "seleccionar_fila": if (datos.fila >= 0) tablaCarpeta.seleccionarFila(datos.fila, true); break
            case "limpiar": dialogoLimpiar.abrir(); break
            case "ir_a_linea": docs.irA(paginaProblemas.filaActual); break
            case "historial_quitar": studio.historial.quitar(tablaHistorial.filaActual); break
            case "historial_vaciar": dialogoVaciar.open(); break
            case "pestana": irAPestana(datos.indice); break
            case "paleta": ventana.paleta.abrir(datos.texto || ""); break
            }
        }
    }
    Connections { target: espacio; function onAviso(texto, tipo) { ventana.mensajes.mostrar(texto, tipo) } }
    Connections { target: docs; function onAviso(texto, tipo) { ventana.mensajes.mostrar(texto, tipo) } }
    Connections {
        target: studio.corrida
        function onAviso(texto, tipo) { ventana.mensajes.mostrar(texto, tipo) }
        function onTerminada(ruta, ok) {
            if (studio.corrida.que === "simular") return
            seleccionarDocumento(ruta)
            if (docs.actual === ruta) irAPestana(docs.nProblemas > 0 ? 2 : 0)
        }
    }
    Connections { target: espacio; function onVistaCambiada() { filtro.text = ""; religarNavegacion() } function onCarpetaCambiada() { religarNavegacion() } }
    Connections { target: docs; function onActualCambiado() { if (docs.hayActual) seleccionarDocumento(docs.actual) } }

    // soltar un .tex en la ventana lo abre (como Ctrl+O)
    DropArea {
        anchors.fill: parent
        keys: ["text/uri-list"]
        onDropped: drop => {
            const tex = drop.urls.map(u => u.toString()).filter(u => u.startsWith("file://") && u.toLowerCase().endsWith(".tex"))
            if (tex.length === 0) { ventana.mensajes.mostrar("Eso no es un .tex: LaTeX Studio compila archivos .tex.", "aviso"); return }
            const e = docs.abrir(decodeURIComponent(tex[0].substring(7)))
            if (e) ventana.mensajes.mostrar(e, "error"); else drop.acceptProposedAction()
        }
    }

    // ------------------------------------------------------------------ barra: la carpeta de trabajo y el filtro
    herramientasExtra: [
        CampoRuta {
            id: campoCarpeta
            Layout.preferredWidth: Kirigami.Units.gridUnit * 20
            texto: espacio.carpeta
            titulo: "Carpeta de trabajo"
            nombreAccesible: "Carpeta de trabajo"
            onAceptada: t => { const e = espacio.fijarCarpeta(t); if (e) ventana.mensajes.mostrar(e, "error"); else campoTexto.text = espacio.carpeta }
            Connections { target: espacio; function onCarpetaCambiada() { campoCarpeta.texto = espacio.carpeta } }
        },
        BotonAccion { accion: ventana.accion("archivo.subir"); conTexto: false },
        Kirigami.SearchField {
            id: filtro
            Layout.preferredWidth: Kirigami.Units.gridUnit * 10
            placeholderText: "Filtrar (Ctrl+F)"
            onTextChanged: { const t = tablaActual(); if (t && t.modelo && t.modelo.filtrar) t.modelo.filtrar(text) }
            Keys.onEscapePressed: { text = ""; const t = tablaActual(); if (t) t.forceActiveFocus() }
            Accessible.name: "Filtrar"
        }
    ]

    // ------------------------------------------------------------------ navegación
    navegacion: PanelNavegacion {
        id: navegacion
        actual: ventana.vista
        secciones: [
            { titulo: "Documentos", filas: docs.filasNavegacion },
            { titulo: "Historial", filas: [{ nombre: "historial", texto: "Compilaciones", icono: "view-history", contador: studio.historial.total }] },
            { titulo: "Carpetas", filas: espacio.filasCarpetas }
        ]
        onElegida: nombre => {
            if (nombre.startsWith("dir:")) { const e = espacio.fijarCarpeta(nombre.substring(4)); if (e) ventana.mensajes.mostrar(e, "error"); espacio.fijarVista("carpeta") }
            else espacio.fijarVista(nombre)
            religarNavegacion()
        }
    }

    // ------------------------------------------------------------------ centro: documentos o historial
    centro: StackLayout {
        id: centro
        currentIndex: ventana.indice

        component MenuDocumento: MenuAcciones {
            acciones: ventana.registro
            conAtajos: false
            elementos: [
                { tipo: "accion", nombre: "doc.compilar" }, { tipo: "accion", nombre: "doc.compilar_biber" }, { tipo: "accion", nombre: "doc.simular" },
                { tipo: "separador" },
                { tipo: "accion", nombre: "doc.pdf" }, { tipo: "accion", nombre: "doc.editor" }, { tipo: "accion", nombre: "doc.limpiar" },
                { tipo: "separador" },
                { tipo: "accion", nombre: "archivo.dolphin" }, { tipo: "accion", nombre: "archivo.terminal" }, { tipo: "accion", nombre: "archivo.copiar" }
            ]
        }
        readonly property var columnasDocumentos: [
            { ancho: 0, minimo: 12, conIcono: true },
            { ancho: 9, semantica: true, conIcono: true },
            { ancho: 9, secundaria: true, estrecho: true },
            { ancho: 8, secundaria: true },
            { ancho: 8, secundaria: true, estrecho: true },
            { ancho: 14, secundaria: true, estrecho: true, visible: false }
        ]

        TablaDatos {                                              // 0 · Carpeta de trabajo
            id: tablaCarpeta
            modelo: docs.modelo
            claveAjustes: "documentos"
            umbralEstrecho: Kirigami.Units.gridUnit * 32
            mensajeVacio: docs.total === 0 ? "No hay ningún .tex en " + espacio.nombreCarpeta + ": elige otra carpeta de trabajo (Ctrl+Mayús+O) o abre un documento (Ctrl+O)"
                                           : "Ningún documento coincide con el filtro"
            iconoVacio: "text-x-tex"
            columnas: centro.columnasDocumentos
            onOrdenar: (columna, descendente) => docs.modelo.ordenar(columna, descendente)
            onFilaActualCambiada: fila => docs.fijarFila(fila)
            onActivada: fila => { docs.fijarFila(fila); studio.corrida.compilar() }
            menuContextual: MenuDocumento {}
        }
        TablaDatos {                                              // 1 · Recientes
            id: tablaRecientes
            modelo: docs.modeloRecientes
            claveAjustes: "recientes"
            umbralEstrecho: Kirigami.Units.gridUnit * 32
            mensajeVacio: "Todavía no abriste ni compilaste ningún documento aquí"
            iconoVacio: "document-open-recent"
            columnas: [
                { ancho: 0, minimo: 12, conIcono: true },
                { ancho: 9, semantica: true, conIcono: true },
                { ancho: 9, secundaria: true, estrecho: true },
                { ancho: 8, secundaria: true },
                { ancho: 8, secundaria: true, estrecho: true },
                { ancho: 16, secundaria: true }
            ]
            onOrdenar: (columna, descendente) => docs.modeloRecientes.ordenar(columna, descendente)
            onFilaActualCambiada: fila => docs.fijarFilaReciente(fila)
            onActivada: fila => { docs.fijarFilaReciente(fila); studio.corrida.compilar() }
            menuContextual: MenuDocumento {}
        }
        TablaDatos {                                              // 2 · Historial
            id: tablaHistorial
            modelo: studio.historial.modelo
            claveAjustes: "historial"
            umbralEstrecho: Kirigami.Units.gridUnit * 32
            mensajeVacio: "Sin compilaciones todavía: cada una queda aquí con su resultado y su duración"
            iconoVacio: "view-history"
            columnas: [
                { ancho: 9, secundaria: true },
                { ancho: 0, minimo: 10, conIcono: true },
                { ancho: 6, semantica: true, conIcono: true },
                { ancho: 5, alinear: "derecha", mono: true },
                { ancho: 12, secundaria: true, estrecho: true },
                { ancho: 14, secundaria: true, estrecho: true }
            ]
            onOrdenar: (columna, descendente) => studio.historial.modelo.ordenar(columna, descendente)
            onFilaActualCambiada: fila => studio.historial.fijarFila(fila)
            onActivada: fila => { studio.historial.fijarFila(fila); espacio.fijarVista("carpeta") }
            onSuprimir: studio.historial.quitar(filaActual)
            menuContextual: MenuAcciones {
                acciones: ventana.registro
                conAtajos: false
                elementos: [{ tipo: "accion", nombre: "doc.compilar" }, { tipo: "accion", nombre: "doc.pdf" }, { tipo: "accion", nombre: "doc.editor" },
                            { tipo: "separador" }, { tipo: "accion", nombre: "historial.quitar" }, { tipo: "accion", nombre: "historial.vaciar" }]
            }
        }
    }

    // ------------------------------------------------------------------ detalles del documento actual
    detalles: PanelDetalles {
        id: detalles
        anchoPreferido: Kirigami.Units.gridUnit * 26
        anchoMinimo: Kirigami.Units.gridUnit * 18
        titulo: docs.hayActual ? docs.nombre : ""
        subtitulo: docs.hayActual ? docs.carpetaActual : ""
        icono: "text-x-tex"
        mensajeVacio: "Elige un documento en la tabla o ábrelo con Ctrl+O"
        iconoVacio: "text-x-tex"
        accionesCabecera: [ventana.accion("doc.pdf"), ventana.accion("doc.editor"), ventana.accion("archivo.dolphin")]
        pestanas: [{ titulo: "Resumen" }, { titulo: "Opciones" }, { titulo: "Problemas", contador: docs.nProblemas }, { titulo: "Registro" }, { titulo: "Salidas", contador: docs.salidas.filas }]
        Resumen {}
        OpcionesCompilacion {}
        Problemas { id: paginaProblemas }
        Registro {}
        Salidas {}
    }

    // ------------------------------------------------------------------ panel inferior
    inferior: PanelInferior { consola: studio.consola }

    // ------------------------------------------------------------------ diálogos
    FileDialog {
        id: selectorTex
        title: "Abrir un .tex"
        nameFilters: ["LaTeX (*.tex)", "Todos (*)"]
        onAccepted: { const e = docs.abrir(decodeURIComponent(selectedFile.toString().replace("file://", ""))); if (e) ventana.mensajes.mostrar(e, "error") }
    }
    FolderDialog {
        id: selectorCarpeta
        title: "Carpeta de trabajo"
        onAccepted: { const e = espacio.fijarCarpeta(decodeURIComponent(selectedFolder.toString().replace("file://", ""))); if (e) ventana.mensajes.mostrar(e, "error"); else espacio.fijarVista("carpeta") }
    }
    Kirigami.PromptDialog {
        id: dialogoLimpiar
        property var lista: []
        standardButtons: Kirigami.Dialog.Cancel
        customFooterActions: [Kirigami.Action { text: "Borrar"; icon.name: "run-build-clean"; enabled: dialogoLimpiar.lista.length > 0; onTriggered: { studio.corrida.limpiar(); dialogoLimpiar.close() } }]
        function abrir() {
            if (!docs.hayActual) { ventana.mensajes.mostrar(studio.corrida.motivo, "aviso"); return }
            lista = studio.corrida.auxiliaresParaLimpiar()
            title = "Limpiar auxiliares de " + docs.nombre
            subtitle = lista.length === 0 ? "No hay ningún auxiliar que borrar en " + docs.carpetaActual + "."
                                          : "main.sh -c borraría " + lista.length + " archivo" + (lista.length === 1 ? "" : "s") + " de " + docs.carpetaActual + ":\n\n" + lista.join("\n")
                                            + "\n\nEl .tex y el PDF no se tocan."
            open()
        }
    }
    Kirigami.PromptDialog {
        id: dialogoVaciar
        title: "Vaciar el historial"
        subtitle: "¿Quitar las " + studio.historial.total + " compilaciones del historial? Los documentos no se tocan."
        standardButtons: Kirigami.Dialog.Cancel
        customFooterActions: [Kirigami.Action { text: "Vaciar"; icon.name: "edit-clear-history"; onTriggered: { studio.historial.vaciar(); dialogoVaciar.close() } }]
    }
    dialogoAjustes: DialogoAjustesStudio {}
}
