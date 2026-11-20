// BarraLateral — la columna izquierda, que cambia con la vista:
// · Proyectos: las categorías con proyectos (solo las que tienen información, R6), los recientes y las carpetas de
//   trabajo (las de omisión y las añadidas; «Añadir carpeta…» abre el diálogo de carpetas de KDE);
// · Escritura (el documento y su estado están en la barra de arriba): la versión que se compila, si el marco declara
//   varias, y cuatro pestañas: Archivos (principal, \input, .bib, configuración), Esquema (secciones, figuras, tablas,
//   etiquetas: un clic va a la línea), Citas (las entradas de los .bib: un clic va a la entrada; doble clic escribe
//   \cite{clave} en el cursor) y Datos (figuras con su miniatura, tablas y cifras de los paquetes del marco).
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

QQC2.Control {
    id: raiz

    readonly property var p: studio.proyectos
    property int anchoPreferido: Kirigami.Units.gridUnit * 18
    property int anchoMinimo: Kirigami.Units.gridUnit * 11
    property bool plegado: false
    implicitWidth: anchoPreferido
    padding: 0

    signal abrirArchivo(string ruta, int linea)
    signal citar(string clave)
    signal insertarDatos(string texto)                 // una figura, tabla o cifra del paquete en el cursor
    signal insertarFigura(var figura)                  // una figura con texto alternativo obligatorio (insertarAlt; §1.22, C8.3)
    signal actualizarDatos()                           // «Actualizar» de la pestaña Datos (la ventana confirma)

    Kirigami.Theme.colorSet: Kirigami.Theme.View
    Kirigami.Theme.inherit: false
    background: Rectangle { color: Kirigami.Theme.backgroundColor }

    contentItem: StackLayout {
        currentIndex: studio.interfaz.vista === "escritura" ? 1 : 0

        // ------------------------------------------------------------- Proyectos
        PanelNavegacion {
            id: navegacion
            actual: raiz.p.categoria
            secciones: [
                { titulo: "Proyectos", filas: raiz.p.categorias },
                { titulo: "Carpetas de trabajo", filas: studio.ajustes.carpetas.map(c => ({ nombre: "dir:" + c.ruta, texto: c.nombre + (c.existe ? "" : " (no existe)") + (c.activa ? "" : " (desactivada)"),
                                                                                              icono: c.existe ? "folder" : "folder-important", contador: "" }))
                                                      .concat([{ nombre: "accion:anadir", texto: "Añadir carpeta…", icono: "list-add", contador: "" }]) }
            ]
            onElegida: nombre => {
                if (nombre === "accion:anadir") studio.interfaz.pedir("anadir_carpeta", {})
                else if (nombre.startsWith("dir:")) studio.escritorio.mostrarEnDolphin(nombre.substring(4))
                else raiz.p.fijarCategoria(nombre)
                navegacion.actual = Qt.binding(() => raiz.p.categoria)
            }
        }

        // ------------------------------------------------------------- Escritura
        ColumnLayout {
            spacing: 0
            // la versión que se compila y se ve, si el marco produce varias de un mismo .tex (`versiones:` de su
            // latex-studio.yml): elegirla no escribe nada; la que compila F5 por omisión la fija «Configurar el documento»
            RowLayout {
                id: filaVersion
                readonly property var versiones: raiz.p.hayAbierto && raiz.p.abierto.versiones ? raiz.p.abierto.versiones : []
                Layout.fillWidth: true
                Layout.leftMargin: Kirigami.Units.smallSpacing
                Layout.rightMargin: Kirigami.Units.smallSpacing
                visible: versiones.length > 0
                QQC2.Label { text: "Versión"; font: Kirigami.Theme.smallFont }
                QQC2.ComboBox {
                    id: comboVersion
                    Layout.fillWidth: true
                    model: filaVersion.versiones
                    textRole: "nombre"
                    currentIndex: filaVersion.versiones.findIndex(v => v.clave === raiz.p.abierto.version)
                    Accessible.name: "Versión que se compila y se ve"
                    QQC2.ToolTip.text: "La que se compila (F5) y se ve. El documento declara: "
                                       + (filaVersion.versiones.find(v => v.clave === raiz.p.abierto.version_declarada) || {nombre: "—"}).nombre
                                       + ". Para cambiar la que declara (y la que compila TeXstudio): Configurar el documento › Versión."
                    QQC2.ToolTip.visible: hovered
                    QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                    onActivated: index => studio.proyectos.elegirVersion(filaVersion.versiones[index].clave)
                }
            }
            // las cuatro pestañas: el selector segmentado de la base (antes, una regleta de recuadros grises);
            // `currentIndex` lo conserva para quien la elige desde fuera (capturar.py)
            SelectorSegmentado {
                id: pestanas
                objectName: "pestanasLaterales"
                property int currentIndex: 0
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: Kirigami.Units.smallSpacing
                Layout.bottomMargin: Kirigami.Units.smallSpacing
                titulo: "Barra lateral"
                compacto: true
                opciones: [{ clave: "0", texto: "Archivos" }, { clave: "1", texto: "Esquema" }, { clave: "2", texto: "Citas" }, { clave: "3", texto: "Datos" }]
                actual: String(currentIndex)
                onElegida: clave => currentIndex = Number(clave)
            }
            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: pestanas.currentIndex

                // archivos del proyecto
                ListView {
                    id: archivos
                    clip: true
                    model: raiz.p.archivos
                    Accessible.name: "Archivos del proyecto"
                    QQC2.ScrollBar.vertical: QQC2.ScrollBar {}
                    section.property: "tipo"
                    section.delegate: Kirigami.ListSectionHeader { required property string section; width: archivos.width; text: section === "principal" ? "Documento principal" : section === "incluido" ? "Incluidos" : section === "bibliografía" ? "Bibliografía" : "Configuración" }
                    delegate: QQC2.ItemDelegate {
                        id: filaArchivo
                        required property var model
                        width: archivos.width
                        text: model.relativa
                        icon.name: model.icono
                        highlighted: studio.editor.actual === model.ruta
                        hoverEnabled: true
                        topInset: 1
                        bottomInset: 1
                        leftInset: Kirigami.Units.smallSpacing
                        rightInset: Kirigami.Units.smallSpacing
                        leftPadding: Kirigami.Units.largeSpacing + Kirigami.Units.smallSpacing
                        background: FondoSeleccion { elegida: filaArchivo.highlighted; sobre: filaArchivo.hovered; pulsada: filaArchivo.pressed; foco: filaArchivo.visualFocus }
                        contentItem: RowLayout {
                            spacing: Kirigami.Units.smallSpacing + Kirigami.Units.smallSpacing / 2
                            Kirigami.Icon { source: filaArchivo.icon.name; implicitWidth: Kirigami.Units.iconSizes.small; implicitHeight: implicitWidth; opacity: 0.85 }
                            QQC2.Label { text: filaArchivo.text; Layout.fillWidth: true; elide: Text.ElideMiddle; font.weight: filaArchivo.highlighted ? Font.DemiBold : Font.Normal }
                        }
                        enabled: model.existe
                        onClicked: raiz.abrirArchivo(model.ruta, 0)
                        QQC2.ToolTip.text: model.ruta
                        QQC2.ToolTip.visible: hovered
                        QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                    }
                }

                // estructura
                ColumnLayout {
                    spacing: 0
                    Kirigami.SearchField {
                        Layout.fillWidth: true
                        Layout.margins: Kirigami.Units.smallSpacing
                        placeholderText: "Filtrar la estructura"
                        onTextChanged: raiz.p.filtrarEstructura(text)
                    }
                    ListView {
                        id: esquema
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: raiz.p.esquema
                        Accessible.name: "Estructura del documento"
                        QQC2.ScrollBar.vertical: QQC2.ScrollBar {}
                        delegate: QQC2.ItemDelegate {
                            required property var model
                            width: esquema.width
                            leftPadding: Kirigami.Units.largeSpacing + Math.min(model.nivel, 5) * Kirigami.Units.gridUnit * 0.8
                            onClicked: raiz.abrirArchivo(model.archivo, model.linea)
                            contentItem: RowLayout {
                                spacing: Kirigami.Units.smallSpacing
                                Kirigami.Icon { visible: model.icono !== ""; source: model.icono; implicitWidth: Kirigami.Units.iconSizes.small; implicitHeight: implicitWidth; isMask: true; color: Kirigami.Theme.disabledTextColor }
                                QQC2.Label {
                                    Layout.fillWidth: true
                                    text: model.titulo
                                    elide: Text.ElideRight
                                    font.weight: model.tipo === "seccion" && model.nivel <= 1 ? Font.DemiBold : Font.Normal
                                    font.family: model.tipo === "etiqueta" ? Kirigami.Theme.fixedWidthFont.family : Kirigami.Theme.defaultFont.family
                                    color: model.tipo === "etiqueta" ? Kirigami.Theme.disabledTextColor : Kirigami.Theme.textColor
                                }
                            }
                            QQC2.ToolTip.text: model.archivo.split("/").pop() + ":" + model.linea + (model.etiqueta ? " · " + model.etiqueta : "")
                            QQC2.ToolTip.visible: hovered
                            QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                        }
                        Kirigami.PlaceholderMessage {
                            anchors.centerIn: parent
                            width: parent.width - Kirigami.Units.gridUnit * 2
                            visible: esquema.count === 0
                            text: raiz.p.hayAbierto ? "Sin secciones ni flotantes" : "Ningún proyecto"
                        }
                    }
                }

                // citas: las entradas de los .bib del proyecto; y, si el marco declara su biblioteca (contrato §9), toda la
                // biblioteca (con portada; citar un libro nuevo lo añade a las fuentes tras confirmar) y las fichas del
                // proyecto (doble clic inserta la cita textual con su página)
                ColumnLayout {
                    id: pestanaCitas
                    objectName: "pestanaCitas"
                    readonly property var b: studio.biblioteca
                    property int modo: 0                       // 0 del proyecto · 1 biblioteca · 2 fichas
                    property string filtroFichas: ""
                    spacing: 0
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.margins: Kirigami.Units.smallSpacing
                        visible: pestanaCitas.b.disponible
                        spacing: Kirigami.Units.smallSpacing
                        Repeater {
                            model: ["Del proyecto", pestanaCitas.b.nombre, "Fichas (" + pestanaCitas.b.fichas.length + ")"]
                            OpcionColor {
                                required property string modelData
                                required property int index
                                text: modelData
                                onClicked: { pestanaCitas.modo = index; if (index === 1 && pestanaCitas.b.resultados.length === 0) pestanaCitas.b.buscar("") }
                                elegida: pestanaCitas.modo === index
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: Kirigami.Units.smallSpacing
                        Layout.rightMargin: Kirigami.Units.smallSpacing
                        visible: pestanaCitas.modo === 2 && pestanaCitas.b.puedeFichar
                        QQC2.Button {
                            objectName: "nuevaFicha"
                            text: "Nueva ficha"
                            icon.name: "document-new"
                            QQC2.ToolTip.text: "Una ficha textual, de paráfrasis, de síntesis o de fuente, con la norma de fichas y su cotejo contra el PDF"
                            onClicked: dialogoFicha.nuevaPara(null)
                            QQC2.ToolTip.visible: hovered && QQC2.ToolTip.text !== ""
                            QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                        }
                        Item { Layout.fillWidth: true }
                    }
                    Kirigami.SearchField {
                        Layout.fillWidth: true
                        Layout.margins: Kirigami.Units.smallSpacing
                        placeholderText: pestanaCitas.modo === 0 ? "Filtrar " + raiz.p.nClaves + " entradas"
                                       : pestanaCitas.modo === 1 ? "Título, autor, año o clave" : "Filtrar las fichas"
                        onTextChanged: {
                            if (pestanaCitas.modo === 0) raiz.p.filtrarBibliografia(text)
                            else if (pestanaCitas.modo === 1) pausaBusqueda.restart()
                            else pestanaCitas.filtroFichas = text
                        }
                        Timer { id: pausaBusqueda; interval: 350; onTriggered: pestanaCitas.b.buscar(parent.text) }
                    }
                    StackLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        currentIndex: pestanaCitas.b.disponible ? pestanaCitas.modo : 0

                        ListView {
                            id: bib
                            clip: true
                            model: raiz.p.bibliografia
                            Accessible.name: "Bibliografía del proyecto"
                            QQC2.ScrollBar.vertical: QQC2.ScrollBar {}
                            delegate: QQC2.ItemDelegate {
                                required property var model
                                width: bib.width
                                onClicked: raiz.abrirArchivo(model.archivo, model.linea)
                                onDoubleClicked: raiz.citar(model.nombre)
                                contentItem: ColumnLayout {
                                    spacing: 0
                                    QQC2.Label { Layout.fillWidth: true; text: model.nombre; font.family: Kirigami.Theme.fixedWidthFont.family; elide: Text.ElideRight }
                                    QQC2.Label { Layout.fillWidth: true; text: [model.autor, model.anio, model.titulo].filter(x => x).join(" · "); elide: Text.ElideRight; font: Kirigami.Theme.smallFont; color: Kirigami.Theme.disabledTextColor }
                                }
                                QQC2.ToolTip.text: "Clic: ir a la entrada · doble clic: \\cite{" + model.nombre + "} en el cursor"
                                QQC2.ToolTip.visible: hovered
                                QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                            }
                            Kirigami.PlaceholderMessage {
                                anchors.centerIn: parent
                                width: parent.width - Kirigami.Units.gridUnit * 2
                                visible: bib.count === 0
                                text: raiz.p.hayAbierto ? "El proyecto no tiene .bib (o están vacíos)" : "Ningún proyecto"
                                explanation: pestanaCitas.b.disponible ? "Busca en «" + pestanaCitas.b.nombre + "» y cita cualquier libro." : ""
                            }
                        }

                        // toda la biblioteca
                        ListView {
                            id: libros
                            clip: true
                            model: pestanaCitas.b.resultados
                            Accessible.name: "Libros de la biblioteca"
                            QQC2.ScrollBar.vertical: QQC2.ScrollBar {}
                            delegate: QQC2.ItemDelegate {
                                id: filaLibro
                                required property var modelData
                                width: libros.width
                                onDoubleClicked: pestanaCitas.b.citar(modelData.calibre_id, modelData.titulo)
                                contentItem: RowLayout {
                                    spacing: Kirigami.Units.smallSpacing
                                    Image {
                                        Layout.preferredWidth: Kirigami.Units.gridUnit * 2
                                        Layout.preferredHeight: Kirigami.Units.gridUnit * 3
                                        fillMode: Image.PreserveAspectFit
                                        asynchronous: true
                                        sourceSize.height: Kirigami.Units.gridUnit * 6
                                        source: filaLibro.modelData.portada ? "file://" + filaLibro.modelData.portada : ""
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 0
                                        QQC2.Label { Layout.fillWidth: true; text: filaLibro.modelData.titulo; elide: Text.ElideRight; maximumLineCount: 2; wrapMode: Text.Wrap }
                                        QQC2.Label { Layout.fillWidth: true; text: (filaLibro.modelData.autores || []).join("; ") + (filaLibro.modelData.anio ? " · " + filaLibro.modelData.anio : "")
                                                     elide: Text.ElideRight; font: Kirigami.Theme.smallFont; color: Kirigami.Theme.disabledTextColor }
                                        QQC2.Label { Layout.fillWidth: true; text: filaLibro.modelData.clave || "sin clave de Zotero"; elide: Text.ElideRight
                                                     font: Qt.font({ family: Kirigami.Theme.fixedWidthFont.family, pointSize: Kirigami.Theme.smallFont.pointSize }); color: filaLibro.modelData.clave ? Kirigami.Theme.disabledTextColor : Kirigami.Theme.neutralTextColor }
                                    }
                                }
                                TapHandler { acceptedButtons: Qt.RightButton; onTapped: menuLibro.popup() }
                                QQC2.Menu {
                                    id: menuLibro
                                    QQC2.MenuItem { text: "Citar en el cursor"; icon.name: "format-text-blockquote"; onTriggered: pestanaCitas.b.citar(filaLibro.modelData.calibre_id, filaLibro.modelData.titulo) }
                                    QQC2.MenuItem { text: "Abrir el PDF"; icon.name: "application-pdf"; enabled: !!filaLibro.modelData.pdf; onTriggered: studio.escritorio.abrirConAplicacion(filaLibro.modelData.pdf) }
                                    QQC2.MenuItem { text: "Abrir en Biblioteca Studio"; icon.name: "bookcase"; onTriggered: pestanaCitas.b.abrirLibro(filaLibro.modelData.calibre_id) }
                                    QQC2.MenuItem { text: "Fichar este libro…"; icon.name: "document-new"; visible: pestanaCitas.b.puedeFichar; height: visible ? implicitHeight : 0
                                                    onTriggered: dialogoFicha.nuevaPara(filaLibro.modelData) }
                                }
                                QQC2.ToolTip.text: "Doble clic: citarlo en el cursor (si aún no es fuente del proyecto, se añade tras confirmar) · clic derecho: más"
                                QQC2.ToolTip.visible: hovered
                                QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay * 2
                            }
                            Kirigami.PlaceholderMessage {
                                anchors.centerIn: parent
                                width: parent.width - Kirigami.Units.gridUnit * 2
                                visible: libros.count === 0
                                text: pestanaCitas.b.buscando ? "Buscando…" : "Ningún libro coincide"
                            }
                        }

                        // las fichas del proyecto
                        ListView {
                            id: listaFichas
                            clip: true
                            model: pestanaCitas.b.fichas.filter(f => !pestanaCitas.filtroFichas || (f.nombre + " " + f.texto + " " + f.clave).toLowerCase().includes(pestanaCitas.filtroFichas.toLowerCase()))
                            Accessible.name: "Fichas del proyecto"
                            QQC2.ScrollBar.vertical: QQC2.ScrollBar {}
                            delegate: QQC2.ItemDelegate {
                                id: filaFicha
                                required property var modelData
                                width: listaFichas.width
                                onClicked: raiz.abrirArchivo(modelData.archivo, 0)
                                onDoubleClicked: if (modelData.insertar) raiz.insertarDatos(modelData.insertar)
                                contentItem: ColumnLayout {
                                    spacing: 0
                                    RowLayout {
                                        Layout.fillWidth: true
                                        QQC2.Label { text: filaFicha.modelData.tipo; font: Kirigami.Theme.smallFont; color: Kirigami.Theme.highlightColor }
                                        QQC2.Label { Layout.fillWidth: true; text: filaFicha.modelData.clave + (filaFicha.modelData.pagina ? ", p. " + filaFicha.modelData.pagina : "")
                                                     font: Kirigami.Theme.smallFont; color: Kirigami.Theme.disabledTextColor; elide: Text.ElideRight }
                                        Kirigami.Icon { visible: filaFicha.modelData.verificacion && filaFicha.modelData.verificacion !== "pendiente"; source: "checkmark"
                                                        implicitWidth: Kirigami.Units.iconSizes.small; implicitHeight: implicitWidth; color: Kirigami.Theme.positiveTextColor }
                                    }
                                    QQC2.Label { Layout.fillWidth: true; text: filaFicha.modelData.texto || filaFicha.modelData.nombre; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight }
                                }
                                TapHandler { acceptedButtons: Qt.RightButton; onTapped: menuFicha.popup() }
                                QQC2.Menu {
                                    id: menuFicha
                                    QQC2.MenuItem { text: "Insertar en el cursor"; icon.name: "format-text-blockquote"; enabled: !!filaFicha.modelData.insertar
                                                    onTriggered: raiz.insertarDatos(filaFicha.modelData.insertar) }
                                    QQC2.MenuItem { text: "Editar la ficha…"; icon.name: "document-edit"; enabled: pestanaCitas.b.puedeEditar
                                                    onTriggered: dialogoFicha.editar(filaFicha.modelData.archivo.split("/").pop()) }
                                    QQC2.MenuItem { text: "Abrir el archivo"; icon.name: "document-open"; onTriggered: raiz.abrirArchivo(filaFicha.modelData.archivo, 0) }
                                }
                                QQC2.ToolTip.text: "Clic: abrir la ficha · doble clic: " + (filaFicha.modelData.insertar || "—") + " en el cursor · clic derecho: editarla"
                                QQC2.ToolTip.visible: hovered
                                QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay * 2
                            }
                            Kirigami.PlaceholderMessage {
                                anchors.centerIn: parent
                                width: parent.width - Kirigami.Units.gridUnit * 2
                                visible: listaFichas.count === 0
                                text: "Sin fichas en fuentes/fichas/"
                                explanation: pestanaCitas.b.error
                            }
                        }
                    }
                }

                // datos del proyecto: lo que declara su marco (latex-studio.yml, sección datos; §8 del contrato)
                ColumnLayout {
                    id: pestanaDatos
                    readonly property var d: studio.datos
                    property string filtro: ""
                    readonly property var lista: d.elementos.filter(e => !filtro || (e.id + " " + e.titulo).toLowerCase().includes(filtro.toLowerCase()))
                    spacing: 0
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.margins: Kirigami.Units.smallSpacing
                        visible: pestanaDatos.d.disponible
                        spacing: Kirigami.Units.smallSpacing
                        Repeater {
                            model: pestanaDatos.d.paquetes
                            QQC2.Label {
                                required property var modelData
                                Layout.fillWidth: true
                                text: modelData.estudio + "@" + modelData.usada + (modelData.nueva ? "  ·  hay " + modelData.ultima : "  ·  al día")
                                color: modelData.nueva ? Kirigami.Theme.neutralTextColor : Kirigami.Theme.disabledTextColor
                                font: Kirigami.Theme.smallFont
                                elide: Text.ElideMiddle
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            QQC2.Button {
                                text: pestanaDatos.d.hayNueva ? "Traer la versión nueva" : "Actualizar"
                                icon.name: "view-refresh"
                                highlighted: pestanaDatos.d.hayNueva
                                enabled: !pestanaDatos.d.cargando && !studio.tareas.activa
                                onClicked: raiz.actualizarDatos()
                                QQC2.ToolTip.text: "Lleva el proyecto a la última versión de sus paquetes y vuelve a dibujar figuras, tablas y cifras"
                                QQC2.ToolTip.visible: hovered
                                QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                            }
                            QQC2.Button {
                                visible: pestanaDatos.d.productor !== ""
                                text: pestanaDatos.d.productor
                                icon.name: "office-chart-bar"
                                onClicked: pestanaDatos.d.abrirProductor()
                                QQC2.ToolTip.text: "Hacer o rehacer figuras y tablas para este proyecto en " + pestanaDatos.d.productor
                                QQC2.ToolTip.visible: hovered
                                QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                            }
                        }
                    }
                    Kirigami.SearchField {
                        Layout.fillWidth: true
                        Layout.margins: Kirigami.Units.smallSpacing
                        visible: pestanaDatos.d.disponible
                        placeholderText: "Filtrar " + pestanaDatos.d.elementos.length + " figuras, tablas y cifras"
                        onTextChanged: pestanaDatos.filtro = text
                    }
                    ListView {
                        id: listaDatos
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: pestanaDatos.lista
                        Accessible.name: "Figuras, tablas y cifras del proyecto"
                        QQC2.ScrollBar.vertical: QQC2.ScrollBar {}
                        delegate: QQC2.ItemDelegate {
                            id: filaDato
                            required property var modelData
                            required property int index
                            readonly property bool primera: index === 0 || pestanaDatos.lista[index - 1].tipo !== modelData.tipo
                            width: listaDatos.width
                            onDoubleClicked: modelData.insertarAlt ? raiz.insertarFigura(modelData) : raiz.insertarDatos(modelData.insertar)
                            contentItem: ColumnLayout {
                                spacing: 0
                                QQC2.Label {
                                    visible: filaDato.primera
                                    Layout.topMargin: filaDato.index === 0 ? 0 : Kirigami.Units.smallSpacing
                                    text: filaDato.modelData.tipo
                                    font.weight: Font.DemiBold
                                    color: Kirigami.Theme.disabledTextColor
                                }
                                Rectangle {
                                    visible: filaDato.modelData.tipo === "Figuras" && miniDato.status === Image.Ready
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: width * 0.55
                                    radius: Kirigami.Units.cornerRadius
                                    color: Qt.alpha(Kirigami.Theme.textColor, 0.04)
                                    border.width: 1
                                    border.color: Qt.alpha(Kirigami.Theme.textColor, 0.12)
                                    clip: true
                                    Image {
                                        id: miniDato
                                        anchors.fill: parent
                                        anchors.margins: 2
                                        fillMode: Image.PreserveAspectFit
                                        asynchronous: true
                                        cache: false
                                        source: { studio.miniaturas.version; return filaDato.modelData.existe && filaDato.modelData.archivo ? studio.miniaturas.url(filaDato.modelData.archivo) : "" }
                                    }
                                }
                                QQC2.Label {
                                    Layout.fillWidth: true
                                    text: filaDato.modelData.tipo === "Cifras" ? filaDato.modelData.id + "  =  " + filaDato.modelData.titulo
                                                                               : (filaDato.modelData.titulo || filaDato.modelData.id)
                                    font.family: filaDato.modelData.tipo === "Cifras" ? Kirigami.Theme.fixedWidthFont.family : Kirigami.Theme.defaultFont.family
                                    elide: Text.ElideRight
                                    color: Kirigami.Theme.textColor
                                }
                                QQC2.Label {
                                    visible: filaDato.modelData.tipo !== "Cifras"
                                    Layout.fillWidth: true
                                    text: filaDato.modelData.id + (filaDato.modelData.existe ? "" : "  ·  sin importar: Actualizar")
                                    font: Kirigami.Theme.smallFont
                                    color: Kirigami.Theme.disabledTextColor
                                    elide: Text.ElideRight
                                }
                            }
                            QQC2.ToolTip.text: "Doble clic: " + filaDato.modelData.insertar + " en el cursor"
                            QQC2.ToolTip.visible: hovered
                            QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                        }
                        Kirigami.PlaceholderMessage {
                            anchors.centerIn: parent
                            width: parent.width - Kirigami.Units.gridUnit * 2
                            visible: listaDatos.count === 0
                            text: !raiz.p.hayAbierto ? "Ningún proyecto"
                                  : !pestanaDatos.d.disponible ? "Este documento no tiene datos declarados"
                                  : pestanaDatos.d.cargando ? "Leyendo los paquetes…"
                                  : pestanaDatos.d.error ? "No se pudieron leer los datos" : "El proyecto no cita paquetes"
                            explanation: !pestanaDatos.d.disponible && raiz.p.hayAbierto
                                         ? "Su marco no declara una sección «datos» en su latex-studio.yml, o el proyecto no tiene la ficha que la activa."
                                         : pestanaDatos.d.error
                        }
                    }
                }
            }
        }
    }
}
