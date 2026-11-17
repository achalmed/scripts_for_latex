// BarraLateral — la columna izquierda, que cambia con la vista:
// · Proyectos: las categorías con proyectos (solo las que tienen información, R6), los recientes y las carpetas de
//   trabajo (las de omisión y las añadidas; «Añadir carpeta…» abre el diálogo de carpetas de KDE);
// · Escritura: el proyecto abierto (motor, compilador, estado) y tres pestañas: Archivos (principal, \input, .bib,
//   configuración), Estructura (secciones, figuras, tablas, etiquetas: un clic va a la línea) y Bibliografía (las
//   entradas de los .bib: un clic va a la entrada; doble clic escribe \cite{clave} en el cursor).
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

QQC2.Control {
    id: raiz

    readonly property var p: studio.proyectos
    property int anchoPreferido: Kirigami.Units.gridUnit * 16
    property int anchoMinimo: Kirigami.Units.gridUnit * 11
    property bool plegado: false
    implicitWidth: anchoPreferido
    padding: 0

    signal abrirArchivo(string ruta, int linea)
    signal citar(string clave)
    signal insertarDatos(string texto)                 // una figura, tabla o cifra del paquete en el cursor
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
            RowLayout {
                Layout.fillWidth: true
                Layout.margins: Kirigami.Units.smallSpacing
                spacing: Kirigami.Units.smallSpacing
                QQC2.ToolButton {
                    icon.name: "go-previous"
                    display: QQC2.AbstractButton.IconOnly
                    text: "Volver a los proyectos (Ctrl+1)"
                    Accessible.name: text
                    QQC2.ToolTip.text: text
                    QQC2.ToolTip.visible: hovered
                    onClicked: studio.interfaz.fijarVista("proyectos")
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    Kirigami.Heading { level: 4; text: raiz.p.hayAbierto ? raiz.p.abierto.nombre : "Ningún proyecto"; elide: Text.ElideRight; Layout.fillWidth: true }
                    QQC2.Label {
                        Layout.fillWidth: true
                        visible: raiz.p.hayAbierto
                        text: raiz.p.hayAbierto ? raiz.p.abierto.texto_motor + " · " + raiz.p.abierto.compilador_texto : ""
                        elide: Text.ElideRight
                        font: Kirigami.Theme.smallFont
                        color: Kirigami.Theme.disabledTextColor
                    }
                }
            }
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
            QQC2.TabBar {
                id: pestanas
                objectName: "pestanasLaterales"
                Layout.fillWidth: true
                // las cuatro a lo ancho (con cuatro, la barra se desplazaba y «Archivos» quedaba fuera de la vista)
                QQC2.TabButton { text: "Archivos"; width: pestanas.width / 4 }
                QQC2.TabButton { text: "Estructura"; width: pestanas.width / 4 }
                QQC2.TabButton { text: "Bibliografía"; width: pestanas.width / 4 }
                QQC2.TabButton { text: "Datos"; width: pestanas.width / 4 }
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
                        required property var model
                        width: archivos.width
                        text: model.relativa
                        icon.name: model.icono
                        highlighted: studio.editor.actual === model.ruta
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
                                Kirigami.Icon { source: model.icono; implicitWidth: Kirigami.Units.iconSizes.small; implicitHeight: implicitWidth }
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

                // bibliografía
                ColumnLayout {
                    spacing: 0
                    Kirigami.SearchField {
                        Layout.fillWidth: true
                        Layout.margins: Kirigami.Units.smallSpacing
                        placeholderText: "Filtrar " + raiz.p.nClaves + " entradas"
                        onTextChanged: raiz.p.filtrarBibliografia(text)
                    }
                    ListView {
                        id: bib
                        Layout.fillWidth: true
                        Layout.fillHeight: true
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
                            onDoubleClicked: raiz.insertarDatos(modelData.insertar)
                            contentItem: ColumnLayout {
                                spacing: 0
                                QQC2.Label {
                                    visible: filaDato.primera
                                    Layout.topMargin: filaDato.index === 0 ? 0 : Kirigami.Units.smallSpacing
                                    text: filaDato.modelData.tipo
                                    font.weight: Font.DemiBold
                                    color: Kirigami.Theme.disabledTextColor
                                }
                                QQC2.Label {
                                    Layout.fillWidth: true
                                    text: filaDato.modelData.tipo === "Cifras" ? filaDato.modelData.id + "  =  " + filaDato.modelData.titulo
                                                                               : (filaDato.modelData.titulo || filaDato.modelData.id)
                                    font.family: filaDato.modelData.tipo === "Cifras" ? Kirigami.Theme.fixedWidthFont.family : Kirigami.Theme.defaultFont.family
                                    elide: Text.ElideRight
                                    color: filaDato.modelData.existe ? Kirigami.Theme.textColor : Kirigami.Theme.neutralTextColor
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
