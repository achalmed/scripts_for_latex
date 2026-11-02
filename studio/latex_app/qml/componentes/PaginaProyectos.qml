// PaginaProyectos — la vista inicial, al estilo de la página de proyectos de Overleaf: los proyectos detectados en las
// carpetas de trabajo (la categoría se elige a la izquierda) con proyecto, estado, motor, última compilación,
// problemas, bibliografía, auxiliares, categoría y carpeta; selección múltiple para compilar en cola; y la ficha del
// proyecto actual a la derecha (carpeta, principal, motor y de dónde sale, compilador, categoría y su motivo, archivos,
// configuración, la orden exacta) con Abrir, Compilar, Mostrar en Dolphin y Abrir el PDF.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

QQC2.SplitView {
    id: raiz

    readonly property var p: studio.proyectos
    property string actual: ""
    readonly property var datos: actual !== "" ? p.datos(actual) : ({})
    readonly property var marcados: {
        tabla.seleccion.selectedIndexes.length          // dependencia
        const filas = []
        for (const i of tabla.seleccion.selectedIndexes) if (filas.indexOf(i.row) < 0) filas.push(i.row)
        return p.rutasDeFilas(filas)
    }
    signal abrir(string ruta)

    function filtrar(texto) { p.modelo.filtrar(texto) }
    function seleccionar(fila) { if (fila >= 0) { tabla.seleccionarFila(fila, true); raiz.actual = p.rutaDeFila(fila) } }
    function enfocarFiltro() { filtro.forceActiveFocus(); filtro.selectAll() }
    function compilarMarcados() {
        const rutas = marcados.length > 0 ? marcados : (actual !== "" ? [actual] : [])
        if (rutas.length === 0) { ventana.mensajes.mostrar("Marca uno o más proyectos en la tabla (Mayús o Ctrl+clic).", "aviso"); return }
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
                Kirigami.SearchField {
                    id: filtro
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 12
                    placeholderText: "Filtrar proyectos"
                    onTextChanged: raiz.filtrar(text)
                    Keys.onDownPressed: tabla.forceActiveFocus()
                }
                QQC2.Button {
                    text: raiz.marcados.length > 1 ? "Compilar " + raiz.marcados.length : "Compilar"
                    icon.name: "run-build-configure"
                    enabled: raiz.marcados.length > 0 || raiz.actual !== ""
                    onClicked: raiz.compilarMarcados()
                    QQC2.ToolTip.text: "Compila los proyectos marcados uno tras otro, cada uno con su compilador (Ctrl+Mayús+F5)"
                    QQC2.ToolTip.visible: hovered
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

        TablaDatos {
            id: tabla
            Layout.fillWidth: true
            Layout.fillHeight: true
            modelo: raiz.p.modelo
            claveAjustes: "proyectos"
            umbralEstrecho: Kirigami.Units.gridUnit * 34
            mensajeVacio: raiz.p.enDeteccion ? "Buscando proyectos en las carpetas de trabajo…"
                          : raiz.p.total === 0 ? "No hay proyectos LaTeX en las carpetas de trabajo: añade una (Ctrl+Mayús+O) o abre un .tex (Ctrl+O)"
                          : "Ningún proyecto coincide"
            iconoVacio: raiz.p.enDeteccion ? "view-refresh" : "text-x-tex"
            columnas: [
                { ancho: 0, minimo: 14, conIcono: true },
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
            ColumnLayout {
                visible: raiz.actual !== ""
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                Kirigami.Heading { level: 2; text: raiz.datos.titulo || raiz.datos.nombre || ""; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                QQC2.Label { text: raiz.datos.carpeta || ""; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true; font: Kirigami.Theme.smallFont; color: Kirigami.Theme.disabledTextColor }
                RowLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Kirigami.Chip { text: raiz.datos.estado || ""; checkable: false; closable: false; icon.name: raiz.datos.icono ? raiz.datos.icono.estado : "" }
                    Kirigami.Chip { text: raiz.datos.categoria || ""; checkable: false; closable: false; visible: !!raiz.datos.categoria }
                }
            }
            Kirigami.FormLayout {
                visible: raiz.actual !== ""
                Layout.fillWidth: true
                QQC2.Label { Kirigami.FormData.label: "Principal:"; text: raiz.datos.nombre || ""; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                QQC2.Label { Kirigami.FormData.label: "Clase:"; text: raiz.datos.clase || "—" }
                QQC2.Label { Kirigami.FormData.label: "Motor:"; text: (raiz.datos.texto_motor || "") + " (" + (raiz.datos.motor_origen || "") + ")"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                QQC2.Label { Kirigami.FormData.label: "Compilador:"; text: raiz.datos.compilador_texto || ""; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                QQC2.Label { Kirigami.FormData.label: "Categoría:"; text: (raiz.datos.categoria || "") + (raiz.datos.categoria_motivo ? " — por " + raiz.datos.categoria_motivo : " — sin información"); Layout.fillWidth: true; wrapMode: Text.WordWrap }
                QQC2.Label { Kirigami.FormData.label: "Última compilación:"; text: raiz.datos.ultima || "" }
                QQC2.Label { Kirigami.FormData.label: "Problemas:"; text: raiz.datos.problemas || "" }
                QQC2.Label { Kirigami.FormData.label: "Archivos:"; text: (raiz.datos.n_archivos || 0) + " .tex" + (raiz.datos.no_encontrados && raiz.datos.no_encontrados.length ? " · faltan " + raiz.datos.no_encontrados.join(", ") : ""); Layout.fillWidth: true; wrapMode: Text.WordWrap }
                QQC2.Label { Kirigami.FormData.label: "Bibliografía:"; text: raiz.datos.bibs && raiz.datos.bibs.length ? raiz.datos.bibs.map(b => b.split("/").pop()).join(", ") : "ninguna"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                QQC2.Label { Kirigami.FormData.label: "Auxiliares:"; text: (raiz.datos.aux || "—") + (raiz.datos.carpeta_aux ? " en " + raiz.datos.carpeta_aux + "/" : "") + (raiz.datos.synctex ? " · con SyncTeX" : "") }
                QQC2.Label { Kirigami.FormData.label: "Configuración:"; text: raiz.datos.configuracion && raiz.datos.configuracion.length ? raiz.datos.configuracion.map(c => c.split("/").pop()).join(", ") : "—"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            }
            ColumnLayout {
                visible: raiz.actual !== ""
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
            Flow {
                visible: raiz.actual !== ""
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                QQC2.Button { text: "Abrir"; icon.name: "document-open"; highlighted: true; onClicked: raiz.abrir(raiz.actual) }
                QQC2.Button { text: "Compilar"; icon.name: "run-build"; onClicked: studio.compilacion.lanzar(raiz.actual, "compilar") }
                QQC2.Button { text: "PDF"; icon.name: "application-pdf"; enabled: !!raiz.datos.pdf; onClicked: studio.escritorio.abrirConAplicacion(raiz.datos.pdf) }
                QQC2.Button { text: "Dolphin"; icon.name: "system-file-manager"; onClicked: studio.escritorio.mostrarEnDolphin(raiz.actual) }
            }
        }
    }
}
