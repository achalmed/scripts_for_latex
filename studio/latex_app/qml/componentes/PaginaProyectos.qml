// PaginaProyectos — la vista inicial (rediseño del 2026-11-17, decisiones §1.17): los documentos detectados en las
// carpetas de trabajo como tarjetas con la miniatura de su primera página, su tipo, cuándo se compilaron y su estado (la
// categoría, o su tipo y su grupo, se elige a la izquierda); «Lista» los muestra en la tabla de siempre (proyecto,
// estado, motor, última compilación, problemas, bibliografía, auxiliares, categoría, carpeta; columnas ordenables).
// Ctrl+clic marca varios para compilarlos en cola. A la derecha, la ficha del elegido: su miniatura, su estado, lo
// esencial y, plegado, lo técnico (motor y de dónde sale, compilador, la orden exacta), con Abrir, Compilar,
// Configurar, TeXstudio, el PDF y Dolphin.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import QtCore
import GuiComun

QQC2.SplitView {
    id: raiz

    readonly property var p: studio.proyectos
    property string actual: ""
    property bool enLista: false                          // «Tarjetas» o «Lista» (se recuerda)
    property var marcadas: []                             // las rutas marcadas con Ctrl+clic en las tarjetas
    readonly property var datos: { p.tarjetas; return actual !== "" ? p.datos(actual) : ({}) }
    readonly property var marcados: {
        if (!enLista) return marcadas.filter(r => p.filaDe(r) >= 0)
        tabla.seleccion.selectedIndexes.length          // dependencia
        const filas = []
        for (const i of tabla.seleccion.selectedIndexes) if (filas.indexOf(i.row) < 0) filas.push(i.row)
        return p.rutasDeFilas(filas)
    }
    Settings { category: "proyectos"; property alias enLista: raiz.enLista }
    signal abrir(string ruta)

    function filtrar(texto) { p.modelo.filtrar(texto) }
    function seleccionar(fila) { if (fila >= 0) { tabla.seleccionarFila(fila, true); raiz.actual = p.rutaDeFila(fila) } }
    function marcar(ruta) { marcadas = marcadas.includes(ruta) ? marcadas.filter(r => r !== ruta) : marcadas.concat([ruta]); actual = ruta }
    function enfocarFiltro() { filtro.forceActiveFocus(); filtro.selectAll() }
    function compilarMarcados() {
        const rutas = marcados.length > 0 ? marcados : (actual !== "" ? [actual] : [])
        if (rutas.length === 0) { ventana.mensajes.mostrar("Marca uno o más documentos con Ctrl+clic.", "aviso"); return }
        const n = studio.compilacion.encolar(rutas)
        ventana.mensajes.mostrar(n + " proyecto" + (n === 1 ? "" : "s") + " en la cola de compilación (panel inferior › Cola).", "informacion")
    }

    orientation: Qt.Horizontal
    Connections { target: raiz.p; function onCambiado() { if (raiz.actual !== "") raiz.actualChanged() } }

    ColumnLayout {
        QQC2.SplitView.fillWidth: true
        QQC2.SplitView.minimumWidth: Kirigami.Units.gridUnit * 24
        spacing: 0

        QQC2.ToolBar {
            Layout.fillWidth: true
            position: QQC2.ToolBar.Header
            RowLayout {
                anchors.fill: parent
                spacing: Kirigami.Units.smallSpacing
                Kirigami.Heading {
                    level: 3
                    text: raiz.p.categoria === "Todas" ? "Proyectos" : raiz.p.categoria
                    Layout.leftMargin: Kirigami.Units.smallSpacing
                }
                QQC2.Label {
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    color: Kirigami.Theme.disabledTextColor
                    text: raiz.p.enDeteccion ? "buscando proyectos…" : (raiz.p.modelo.filas + " de " + raiz.p.total
                          + (raiz.p.recuento.errores ? " · " + raiz.p.recuento.errores + " con errores" : "")
                          + (raiz.p.recuento.desactualizado ? " · " + raiz.p.recuento.desactualizado + " con el PDF anterior a las fuentes" : "")
                          + (raiz.marcados.length > 1 ? " · " + raiz.marcados.length + " marcados" : ""))
                }
                QQC2.ButtonGroup { id: grupoVista }
                QQC2.ToolButton { text: "Tarjetas"; icon.name: "view-list-icons"; checkable: true; checked: !raiz.enLista; QQC2.ButtonGroup.group: grupoVista
                                  onClicked: raiz.enLista = false; display: QQC2.AbstractButton.IconOnly; Accessible.name: text
                                  QQC2.ToolTip.text: "Ver como tarjetas, con la primera página"; QQC2.ToolTip.visible: hovered }
                QQC2.ToolButton { text: "Lista"; icon.name: "view-list-details"; checkable: true; checked: raiz.enLista; QQC2.ButtonGroup.group: grupoVista
                                  onClicked: raiz.enLista = true; display: QQC2.AbstractButton.IconOnly; Accessible.name: text
                                  QQC2.ToolTip.text: "Ver como lista, con todas las columnas"; QQC2.ToolTip.visible: hovered }
                Kirigami.SearchField {
                    id: filtro
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 12
                    placeholderText: "Filtrar proyectos"
                    onTextChanged: raiz.filtrar(text)
                    Keys.onDownPressed: raiz.enLista ? tabla.forceActiveFocus() : rejilla.forceActiveFocus()
                }
                QQC2.ToolButton {
                    icon.name: "view-refresh"
                    display: QQC2.AbstractButton.IconOnly
                    text: "Buscar proyectos de nuevo (Ctrl+Mayús+R)"
                    Accessible.name: text
                    enabled: !raiz.p.enDeteccion
                    onClicked: raiz.p.detectar()
                    QQC2.ToolTip.text: text
                    QQC2.ToolTip.visible: hovered
                }
            }
        }

        GridView {
            id: rejilla
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !raiz.enLista
            clip: true
            readonly property int columnas: Math.max(1, Math.floor((width - Kirigami.Units.largeSpacing) / (Kirigami.Units.gridUnit * 10)))
            cellWidth: (width - Kirigami.Units.largeSpacing) / columnas
            cellHeight: cellWidth * 0.62 + Kirigami.Units.gridUnit * 5.5
            leftMargin: Kirigami.Units.largeSpacing
            topMargin: Kirigami.Units.largeSpacing
            model: raiz.p.tarjetas
            keyNavigationEnabled: true
            Accessible.name: "Documentos"
            QQC2.ScrollBar.vertical: QQC2.ScrollBar {}
            delegate: Item {
                required property var modelData
                required property int index
                width: rejilla.cellWidth
                height: rejilla.cellHeight
                TarjetaProyecto {
                    anchors.fill: parent
                    anchors.rightMargin: Kirigami.Units.largeSpacing
                    anchors.bottomMargin: Kirigami.Units.largeSpacing
                    fila: parent.modelData
                    elegida: raiz.actual === parent.modelData.ruta
                    marcada: raiz.marcadas.includes(parent.modelData.ruta)
                    onElegir: marcar => { if (marcar) raiz.marcar(fila.ruta); else raiz.actual = fila.ruta }
                    onAbrir: raiz.abrir(fila.ruta)
                }
            }
            Keys.onReturnPressed: if (raiz.actual) raiz.abrir(raiz.actual)
            onCurrentIndexChanged: if (currentIndex >= 0 && currentIndex < raiz.p.tarjetas.length) raiz.actual = raiz.p.tarjetas[currentIndex].ruta
            Kirigami.PlaceholderMessage {
                anchors.centerIn: parent
                width: parent.width - Kirigami.Units.gridUnit * 4
                visible: rejilla.count === 0
                icon.name: raiz.p.enDeteccion ? "view-refresh" : "text-x-tex"
                text: raiz.p.enDeteccion ? "Buscando tus documentos…" : raiz.p.total === 0 ? "Empieza con un documento" : "Ningún documento coincide"
                explanation: raiz.p.total === 0 && !raiz.p.enDeteccion ? "Crea uno (Ctrl+N), añade una carpeta de trabajo (Ctrl+Mayús+O) o abre un .tex (Ctrl+O)." : ""
                helpfulAction: raiz.p.total === 0 && !raiz.p.enDeteccion ? accionNuevo : null
                Kirigami.Action { id: accionNuevo; text: "Nuevo documento"; icon.name: "document-new"; onTriggered: studio.interfaz.pedir("nuevo_documento", {}) }
            }
        }

        TablaDatos {
            id: tabla
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: raiz.enLista
            modelo: raiz.p.modelo
            claveAjustes: "proyectos"
            umbralEstrecho: Kirigami.Units.gridUnit * 34
            mensajeVacio: raiz.p.enDeteccion ? "Buscando proyectos en las carpetas de trabajo…"
                          : raiz.p.total === 0 ? "No hay proyectos LaTeX en las carpetas de trabajo: añade una (Ctrl+Mayús+O) o abre un .tex (Ctrl+O)"
                          : "Ningún proyecto coincide"
            iconoVacio: raiz.p.enDeteccion ? "view-refresh" : "text-x-tex"
            columnas: [
                { ancho: 0, minimo: 14, conIcono: true, lineas: 3, cortarTras: "/" },   // la ruta entera, en hasta tres líneas
                { ancho: 8, semantica: true, conIcono: true },
                { ancho: 10, secundaria: true },
                { ancho: 8, secundaria: true },
                { ancho: 8, secundaria: true },
                { ancho: 4, alinear: "derecha", secundaria: true, estrecho: true },
                { ancho: 4, alinear: "derecha", secundaria: true, estrecho: true },
                { ancho: 11, secundaria: true, estrecho: true },
                { ancho: 14, secundaria: true, estrecho: true, visible: false }
            ]
            onOrdenar: (columna, descendente) => raiz.p.modelo.ordenar(columna, descendente)
            onFilaActualCambiada: fila => raiz.actual = raiz.p.rutaDeFila(fila)
            onActivada: fila => raiz.abrir(raiz.p.rutaDeFila(fila))
            menuContextual: QQC2.Menu {
                QQC2.MenuItem { text: "Abrir"; icon.name: "document-open"; onTriggered: raiz.abrir(raiz.actual) }
                QQC2.MenuItem { text: raiz.marcados.length > 1 ? "Compilar los " + raiz.marcados.length + " marcados" : "Compilar"; icon.name: "run-build"; onTriggered: raiz.compilarMarcados() }
                QQC2.MenuSeparator {}
                QQC2.MenuItem { text: "Abrir el PDF con su aplicación"; icon.name: "application-pdf"; enabled: raiz.datos.pdf !== undefined && raiz.datos.pdf !== ""; onTriggered: studio.escritorio.abrirConAplicacion(raiz.datos.pdf) }
                QQC2.MenuItem { text: "Mostrar en Dolphin"; icon.name: "system-file-manager"; onTriggered: studio.escritorio.mostrarEnDolphin(raiz.actual) }
                QQC2.MenuItem { text: "Copiar la ruta"; icon.name: "edit-copy"; onTriggered: studio.sistema.copiarRuta(raiz.actual) }
            }
        }
    }

    // ------------------------------------------------------------------ la ficha del proyecto actual
    QQC2.ScrollView {
        id: ficha
        QQC2.SplitView.preferredWidth: Kirigami.Units.gridUnit * 24
        QQC2.SplitView.minimumWidth: Kirigami.Units.gridUnit * 16
        contentWidth: availableWidth
        QQC2.ScrollBar.horizontal.policy: QQC2.ScrollBar.AlwaysOff
        Kirigami.Theme.colorSet: Kirigami.Theme.View
        Kirigami.Theme.inherit: false
        background: Rectangle { color: Kirigami.Theme.backgroundColor }

        ColumnLayout {
            width: ficha.availableWidth - Kirigami.Units.largeSpacing * 2
            x: Kirigami.Units.largeSpacing
            y: Kirigami.Units.largeSpacing
            spacing: Kirigami.Units.largeSpacing

            Kirigami.PlaceholderMessage {
                Layout.fillWidth: true
                Layout.topMargin: Kirigami.Units.gridUnit * 4
                visible: raiz.actual === ""
                icon.name: "text-x-tex"
                text: "Elige un proyecto"
                explanation: "Intro o doble clic lo abre en el editor con su PDF. Un proyecto es un documento principal con sus \\input, sus .bib y su configuración."
            }
            Rectangle {
                visible: raiz.actual !== "" && miniaturaFicha.status === Image.Ready
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(width * 1.1, Kirigami.Units.gridUnit * 16)
                radius: Kirigami.Units.cornerRadius * 2
                color: Qt.alpha(Kirigami.Theme.textColor, 0.04)
                border.width: 1
                border.color: Qt.alpha(Kirigami.Theme.textColor, 0.12)
                clip: true
                Image {
                    id: miniaturaFicha
                    anchors.fill: parent
                    anchors.margins: Kirigami.Units.smallSpacing
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                    cache: false
                    source: { studio.miniaturas.version; return studio.miniaturas.url(raiz.datos.pdf || "") }
                }
            }
            ColumnLayout {
                visible: raiz.actual !== ""
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                Kirigami.Heading { level: 2; text: raiz.datos.titulo || raiz.datos.relativa || ""; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                QQC2.Label { text: raiz.datos.carpeta || ""; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true; font: Kirigami.Theme.smallFont; color: Kirigami.Theme.disabledTextColor }
                RowLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Kirigami.Chip { text: raiz.datos.estado || ""; checkable: false; closable: false; icon.name: raiz.datos.icono ? raiz.datos.icono.estado : "" }
                    Kirigami.Chip { text: raiz.datos.categoria || ""; checkable: false; closable: false; visible: !!raiz.datos.categoria }
                }
            }
            Flow {
                visible: raiz.actual !== ""
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                Chip { text: "Abrir"; icono: "document-edit"; destacado: true; onClicked: raiz.abrir(raiz.actual); ayuda: "Escribir con el PDF al lado (Intro o doble clic)" }
                Chip { text: "Compilar"; icono: "run-build"; onClicked: studio.compilacion.lanzar(raiz.actual, "compilar"); ayuda: "Con su compilador y su motor" }
                Chip { text: "Configurar"; icono: "document-properties"; onClicked: studio.interfaz.pedir("configurar_documento", { ruta: raiz.actual }); ayuda: "Título, autor, tema y opciones de su clase" }
                Chip { text: "Ver el PDF"; icono: "application-pdf"; visible: !!raiz.datos.pdf; onClicked: studio.escritorio.abrirConAplicacion(raiz.datos.pdf) }
                Chip { text: "TeXstudio"; icono: "texstudio"; visible: studio.sistema.hayTexstudio; onClicked: studio.sistema.abrirEnTexstudio(raiz.actual, 1, raiz.actual) }
                Chip { text: "Dolphin"; icono: "system-file-manager"; onClicked: studio.escritorio.mostrarEnDolphin(raiz.actual) }
            }
            Kirigami.FormLayout {
                visible: raiz.actual !== ""
                Layout.fillWidth: true
                QQC2.Label { Kirigami.FormData.label: "Última compilación:"; text: raiz.datos.hace ? raiz.datos.hace + (raiz.datos.ultima && raiz.datos.ultima !== "nunca" ? " (" + raiz.datos.ultima + ")" : "") : "" }
                QQC2.Label { Kirigami.FormData.label: "Problemas:"; text: raiz.datos.problemas || "" }
                QQC2.Label { Kirigami.FormData.label: "Archivos:"; text: (raiz.datos.n_archivos || 0) + " .tex" + (raiz.datos.no_encontrados && raiz.datos.no_encontrados.length ? " · faltan " + raiz.datos.no_encontrados.join(", ") : ""); Layout.fillWidth: true; wrapMode: Text.WordWrap }
                QQC2.Label { Kirigami.FormData.label: "Bibliografía:"; text: raiz.datos.bibs && raiz.datos.bibs.length ? raiz.datos.bibs.map(b => b.split("/").pop()).join(", ") : "ninguna"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            }
            QQC2.Switch {
                id: verTecnico
                visible: raiz.actual !== ""
                text: "Detalles técnicos"
                checked: false
            }
            Kirigami.FormLayout {
                visible: raiz.actual !== "" && verTecnico.checked
                Layout.fillWidth: true
                QQC2.Label { Kirigami.FormData.label: "Principal:"; text: raiz.datos.relativa || ""; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                QQC2.Label { Kirigami.FormData.label: "Clase:"; text: raiz.datos.clase || "—" }
                QQC2.Label { Kirigami.FormData.label: "Motor:"; text: (raiz.datos.texto_motor || "") + " (" + (raiz.datos.motor_origen || "") + ")"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                QQC2.Label { Kirigami.FormData.label: "Compilador:"; text: raiz.datos.compilador_texto || ""; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                QQC2.Label { Kirigami.FormData.label: "Categoría:"; text: (raiz.datos.categoria || "") + (raiz.datos.categoria_motivo ? " — por " + raiz.datos.categoria_motivo : " — sin información"); Layout.fillWidth: true; wrapMode: Text.WordWrap }
                QQC2.Label { Kirigami.FormData.label: "Auxiliares:"; text: (raiz.datos.aux || "—") + (raiz.datos.carpeta_aux ? " en " + raiz.datos.carpeta_aux + "/" : "") + (raiz.datos.synctex ? " · con SyncTeX" : "") }
                QQC2.Label { Kirigami.FormData.label: "Configuración:"; text: raiz.datos.configuracion && raiz.datos.configuracion.length ? raiz.datos.configuracion.map(c => c.split("/").pop()).join(", ") : "—"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            }
            ColumnLayout {
                visible: raiz.actual !== "" && verTecnico.checked
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                QQC2.Label { text: "Orden de compilación"; font.weight: Font.DemiBold }
                QQC2.TextArea {
                    Layout.fillWidth: true
                    readOnly: true
                    wrapMode: TextEdit.WrapAnywhere
                    text: raiz.datos.orden || ""
                    font.family: Kirigami.Theme.fixedWidthFont.family
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    Accessible.name: "Orden de compilación"
                }
            }
        }
    }
}
