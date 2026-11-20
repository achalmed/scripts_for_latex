// DialogoEntrega — «Antes de entregar» (Ctrl+Alt+E; decisiones §1.21, contrato §12): los controles que el marco revisa
// antes de entregar el documento abierto (studio.entrega.resultado). Arriba, el veredicto: «Listo para entregar» o
// «Faltan N» (las fallas más los puntos manuales sin marcar; los avisos no bloquean). Cada control, en su grupo, con su
// punto de color, su línea tenue «por qué · fuente» y sus hallazgos: un clic lleva al archivo y la línea en el editor.
// Los puntos manuales tienen casilla y nota: sin casilla y con nota quedan justificados. La única acción rellena es
// «Revisar de nuevo»; la ventana no sabe qué es cada control: lo dice el marco. Un control con `accion` (autoevaluar,
// matriz) trae el botón que abre su ventana (la autoevaluación con la rúbrica, la matriz de consistencia; §1.22).
// La medición (§1.21, C14.1): «Revisar de nuevo» mide (anota la corrida en el registro del marco), cada control dice lo
// medido en una línea tenue y lo que marcó puede declararse «falso positivo» con su motivo; «Tiempo por etapa» empieza y
// termina la etapa del flujo en curso. El candado (§1.21): «Entregar el PDF…» con «Faltan N» pide «Entregar de todos
// modos» con un motivo escrito, que el marco anota con la entrega.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

Kirigami.Dialog {
    showCloseButton: false            // ya hay botones al pie: sin la × roja del encabezado
    id: dialogo
    readonly property var e: studio.entrega
    readonly property var r: e.resultado
    readonly property int visibles: 5             // los hallazgos de un control que se ven sin desplegarlo

    title: "Antes de entregar"
    preferredWidth: Kirigami.Units.gridUnit * 46
    preferredHeight: Kirigami.Units.gridUnit * 40
    standardButtons: Kirigami.Dialog.NoButton
    padding: Kirigami.Units.largeSpacing

    property bool preparandoFrio: false
    property string motivoEntrega: ""               // el motivo escrito para entregar con «Faltan N»
    function abrir() { e.revisar(); e.leerTiempos(); open() }
    // «Entregar el PDF…»: listo, se elige el destino; con «Faltan N», primero el motivo (el marco vuelve a revisar y,
    // si algo cambió, responde `bloqueado` y el motivo se pide otra vez)
    function entregar() {
        motivoEntrega = ""
        if (r.listo) elegirDestino()
        else dialogoMotivo.open()
    }
    function elegirDestino() {
        // el nombre sugerido no es el del PDF del proyecto (el marco no copia un archivo sobre sí mismo)
        const hoy = new Date().toISOString().slice(0, 10)
        destinoEntrega.abrir(r.carpeta || "", (r.maestro || "documento").split("/").pop().replace(/\.tex$/, "") + "-entrega-" + hoy + ".pdf")
    }
    function medido(c) {                            // «Medido: 12 corridas · atrapó 3 · 1 falso · molesta»
        const m = c.medicion
        if (!m || !m.corridas) return ""
        const partes = [m.corridas + (m.corridas === 1 ? " corrida" : " corridas"), "atrapó " + m.atrapo]
        if (m.falsos) partes.push(m.falsos + (m.falsos === 1 ? " falso positivo" : " falsos positivos"))
        if (m.marca) partes.push(m.marca)
        return "Medido: " + partes.join(" · ")
    }
    GuardarComo {
        id: destinoEntrega
        titulo: "Entregar el PDF"
        filtros: ["PDF (*.pdf)"]
        sufijo: "pdf"
        onElegido: ruta => dialogo.e.entregar(ruta, dialogo.motivoEntrega)
    }
    Kirigami.Dialog {
        showCloseButton: false            // ya hay botones al pie: sin la × roja del encabezado
        id: dialogoMotivo
        title: "Faltan " + (dialogo.r.faltan || 0)
        preferredWidth: Kirigami.Units.gridUnit * 28
        standardButtons: Kirigami.Dialog.Cancel
        padding: Kirigami.Units.largeSpacing
        onOpened: { motivo.text = dialogo.motivoEntrega; motivo.forceActiveFocus() }
        customFooterActions: [
            Kirigami.Action {
                text: "Entregar de todos modos"; icon.name: "document-send"
                enabled: motivo.text.trim() !== ""
                onTriggered: { dialogo.motivoEntrega = motivo.text.trim(); dialogoMotivo.close(); dialogo.elegirDestino() }
            }
        ]
        ColumnLayout {
            spacing: Kirigami.Units.smallSpacing
            QQC2.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "El documento no está listo para entregar (" + dialogo.resumen() + "). Puedes entregarlo de todos modos: "
                      + "escribe por qué y quedará con la entrega en el registro del proyecto."
            }
            QQC2.TextArea {
                id: motivo
                Layout.fillWidth: true
                Layout.preferredHeight: Kirigami.Units.gridUnit * 5
                wrapMode: TextEdit.Wrap
                placeholderText: "Motivo (por ejemplo: el jurado pidió esta versión hoy; la falla de Biber es de una entrada ajena)"
                Accessible.name: "Motivo para entregar con puntos pendientes"
            }
        }
    }
    Connections {
        target: dialogo.e
        function onFalsoDeclarado(d) {
            if (d.error) ventana.mensajes.mostrar("Falso positivo: " + d.error, "aviso")
            else ventana.mensajes.mostrar("Falso positivo anotado con su motivo.", "positivo")
        }
        function onEtapaMarcada(d) {
            if (d.error) ventana.mensajes.mostrar("Tiempo por etapa: " + d.error, "aviso")
        }
        function onEntregado(d) {
            if (d.error) ventana.mensajes.mostrar("Entregar: " + d.error, "aviso")
            else if (d.bloqueado) { dialogo.motivoEntrega = ""; ventana.mensajes.mostrar(d.mensaje || ("Faltan " + d.faltan + "."), "aviso"); dialogoMotivo.open() }
            else if (d.escrito) ventana.mensajes.mostrar("PDF entregado" + ((d.entrega || {}).motivo ? " con «Faltan " + d.faltan + "»" : "")
                                                         + "; queda en el registro del proyecto.", "positivo")
        }
        function onLectorFrioListo(d) {
            dialogo.preparandoFrio = false
            if (d.error) ventana.mensajes.mostrar("Lector frío: " + d.error, "aviso")
            else if (d.pdf) {
                ventana.mensajes.mostrar("Versión sin nombres lista" + (d.hoja ? ", con la hoja del revisor junto al PDF" : "")
                                         + ((d.pendientes || []).length ? ": revisa " + d.pendientes.length + " nombres en el texto" : "") + ".", "positivo")
                studio.sistema.abrirEnOkular(d.pdf, "", 0)
            }
        }
    }
    function colorDe(c) {
        if (c.estado === "falla") return Kirigami.Theme.negativeTextColor
        if (c.estado === "aviso") return Kirigami.Theme.neutralTextColor
        if (c.estado === "ok" || c.marcado) return Kirigami.Theme.positiveTextColor
        return Kirigami.Theme.disabledTextColor                         // manual sin marcar
    }
    function delGrupo(clave) { return (r.controles || []).filter(c => c.grupo === clave) }
    function resumen() {
        const partes = []
        if (r.fallas) partes.push(r.fallas + (r.fallas === 1 ? " falla" : " fallas"))
        if (r.pendientes) partes.push(r.pendientes + (r.pendientes === 1 ? " punto sin marcar" : " puntos sin marcar"))
        if (r.avisos) partes.push(r.avisos + (r.avisos === 1 ? " aviso" : " avisos"))
        if (r.lista && r.lista.nombre) partes.push("lista: " + r.lista.nombre)
        return partes.join(" · ")
    }
    function ir(h) {
        if (!h.ruta) return
        dialogo.close()
        ventana.irA(h.ruta, h.linea)
    }

    footer: QQC2.ToolBar {
        position: QQC2.ToolBar.Footer
        padding: Kirigami.Units.largeSpacing
        background: Item {}
        RowLayout {
            anchors.fill: parent
            spacing: Kirigami.Units.smallSpacing
            QQC2.Label {
                Layout.fillWidth: true
                Layout.preferredWidth: Kirigami.Units.gridUnit * 8     // el pie no ensancha el diálogo: el texto se corta
                elide: Text.ElideRight
                font: Kirigami.Theme.smallFont
                color: Kirigami.Theme.disabledTextColor
                text: dialogo.e.revisando ? "Revisando…"
                      : dialogo.e.puedeMedir ? "Un clic en un hallazgo lo abre en el editor. «Revisar de nuevo» anota la corrida para medir cada control."
                      : "Un clic en un hallazgo lo abre en el editor. Revisar no escribe nada."
            }
            QQC2.Button { text: "Cerrar"; onClicked: dialogo.close() }
            QQC2.Button {
                text: "Versión para lector frío"; icon.name: "im-invisible-user"
                visible: dialogo.e.puedeLectorFrio
                enabled: !dialogo.e.revisando && !dialogo.preparandoFrio
                opacity: enabled ? 1 : 0.5
                QQC2.ToolTip.text: "Un PDF sin nombres para un revisor externo (el marco lo compila aparte; el documento no cambia)"
                onClicked: { dialogo.preparandoFrio = true; dialogo.e.lectorFrio() }
                QQC2.ToolTip.visible: hovered && QQC2.ToolTip.text !== ""
                QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
            }
            QQC2.Button {
                text: "Entregar el PDF…"; icon.name: "document-send"
                visible: dialogo.e.puedeEntregar
                enabled: !dialogo.e.revisando && (dialogo.r.controles || []).length > 0
                opacity: enabled ? 1 : 0.5
                QQC2.ToolTip.text: dialogo.r.listo ? "Copia el PDF adonde elijas y deja constancia de la entrega"
                                       : "Con «Faltan " + (dialogo.r.faltan || 0) + "» pide el motivo antes de entregar"
                onClicked: dialogo.entregar()
                QQC2.ToolTip.visible: hovered && QQC2.ToolTip.text !== ""
                QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
            }
            BotonPrincipal {
                text: "Revisar de nuevo"; icon.name: "view-refresh-symbolic";
                enabled: !dialogo.e.revisando
                opacity: enabled ? 1 : 0.5
                QQC2.ToolTip.text: dialogo.e.puedeMedir ? "Vuelve a correr los controles del marco sobre lo guardado y anota la corrida (mide cada control)"
                                            : "Vuelve a correr los controles del marco sobre lo guardado"
                onClicked: dialogo.e.revisarMidiendo()
                QQC2.ToolTip.visible: hovered && QQC2.ToolTip.text !== ""
                QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
            }
        }
    }

    QQC2.ScrollView {
        id: vista
        contentWidth: availableWidth
        QQC2.ScrollBar.horizontal.policy: QQC2.ScrollBar.AlwaysOff
        ColumnLayout {
            width: vista.availableWidth
            spacing: Kirigami.Units.largeSpacing

            // --- el veredicto
            RowLayout {
                Layout.fillWidth: true
                visible: (dialogo.r.controles || []).length > 0
                spacing: Kirigami.Units.largeSpacing
                Rectangle {
                    implicitWidth: Kirigami.Units.gridUnit * 0.9
                    implicitHeight: implicitWidth
                    radius: width / 2
                    color: dialogo.r.listo ? Kirigami.Theme.positiveTextColor : dialogo.r.fallas ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.neutralTextColor
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    Kirigami.Heading {
                        level: 2
                        text: dialogo.r.listo ? "Listo para entregar" : "Faltan " + dialogo.r.faltan
                        Accessible.name: text
                    }
                    QQC2.Label {
                        Layout.fillWidth: true
                        text: dialogo.resumen()
                        elide: Text.ElideRight
                        color: Kirigami.Theme.disabledTextColor
                    }
                }
            }
            QQC2.BusyIndicator {
                Layout.alignment: Qt.AlignHCenter
                visible: dialogo.e.revisando && (dialogo.r.controles || []).length === 0
                running: visible
            }
            // --- el tiempo por etapa del flujo (C14.1): la etapa en curso y los minutos; empezar otra cierra la que corre
            RowLayout {
                id: tiempo
                readonly property var t: dialogo.e.tiempos
                readonly property var opciones: t.opciones || []
                readonly property string elegida: opciones.length ? opciones[Math.max(0, etapa.currentIndex)].clave : ""
                readonly property bool enCurso: !!t.abierta && t.abierta.etapa === elegida
                Layout.fillWidth: true
                visible: dialogo.e.puedeTiempo && opciones.length > 0
                spacing: Kirigami.Units.smallSpacing
                QQC2.Label { text: "Tiempo por etapa"; font.weight: Font.Medium }
                QQC2.ComboBox {
                    id: etapa
                    model: tiempo.opciones
                    textRole: "nombre"
                    Accessible.name: "Etapa del flujo"
                    Component.onCompleted: currentIndex = 0
                    Connections {
                        target: dialogo.e
                        function onTiemposCambiados() {
                            const a = dialogo.e.tiempos.abierta
                            if (a) etapa.currentIndex = Math.max(0, tiempo.opciones.findIndex(o => o.clave === a.etapa))
                        }
                    }
                }
                QQC2.Button {
                    text: tiempo.enCurso ? "Terminar" : "Empezar"
                    icon.name: tiempo.enCurso ? "media-playback-stop" : "media-playback-start"
                    QQC2.ToolTip.text: tiempo.enCurso ? "Cierra la etapa y anota sus minutos"
                           : (tiempo.t.abierta ? "Empieza esta etapa y cierra «" + tiempo.t.abierta.nombre + "»" : "Empieza a contar esta etapa")
                    onClicked: dialogo.e.marcarEtapa(tiempo.elegida, tiempo.enCurso ? "terminar" : "empezar")
                    QQC2.ToolTip.visible: hovered && QQC2.ToolTip.text !== ""
                    QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                }
                QQC2.Label {
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    color: Kirigami.Theme.disabledTextColor
                    text: (tiempo.t.abierta ? "En curso: " + tiempo.t.abierta.nombre + ", " + dialogo.e.duracion(tiempo.t.abierta.minutos)
                                            : "Ninguna etapa en curso")
                          + (tiempo.t.total ? " · en total " + dialogo.e.duracion(tiempo.t.total) : "")
                }
            }
            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: !!dialogo.r.error
                type: Kirigami.MessageType.Error
                text: dialogo.r.error || ""
            }

            // --- los grupos, con sus controles
            Repeater {
                model: dialogo.r.grupos || []
                ColumnLayout {
                    id: grupo
                    required property var modelData
                    readonly property var controles: dialogo.delGrupo(modelData.clave)
                    Layout.fillWidth: true
                    visible: controles.length > 0
                    spacing: Kirigami.Units.smallSpacing
                    Kirigami.Heading { level: 4; text: grupo.modelData.nombre; Layout.topMargin: Kirigami.Units.smallSpacing }

                    Repeater {
                        model: grupo.controles
                        ColumnLayout {
                            id: fila
                            required property var modelData
                            readonly property var c: modelData
                            readonly property bool manual: c.estado === "manual"
                            readonly property bool atrapo: c.estado === "falla" || c.estado === "aviso"
                            property bool desplegado: false
                            property bool declarando: false
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing / 2

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Kirigami.Units.smallSpacing
                                Rectangle {                        // el punto de color: hueco si es manual sin marcar
                                    Layout.alignment: Qt.AlignVCenter
                                    implicitWidth: Kirigami.Units.gridUnit * 0.55
                                    implicitHeight: implicitWidth
                                    radius: width / 2
                                    color: fila.manual && !fila.c.marcado ? "transparent" : dialogo.colorDe(fila.c)
                                    border.width: fila.manual && !fila.c.marcado ? 1.5 : 0
                                    border.color: dialogo.colorDe(fila.c)
                                }
                                QQC2.CheckBox {
                                    id: casilla
                                    visible: fila.manual
                                    checked: fila.c.marcado === "hecho"
                                    enabled: dialogo.e.puedeMarcar
                                    text: fila.c.nombre
                                    Layout.fillWidth: true
                                    onToggled: dialogo.e.marcar(fila.c.id, checked, nota.text)
                                }
                                QQC2.Label {
                                    visible: !fila.manual
                                    Layout.fillWidth: true
                                    text: fila.c.nombre
                                    font.weight: Font.Medium
                                    wrapMode: Text.WordWrap
                                }
                                QQC2.Label {
                                    text: fila.c.detalle || ""
                                    visible: text !== ""
                                    Layout.maximumWidth: Kirigami.Units.gridUnit * 18
                                    elide: Text.ElideRight
                                    color: Kirigami.Theme.disabledTextColor
                                }
                                QQC2.Button {                         // lo que marcó no era un defecto: con su motivo (§1.21)
                                    visible: fila.atrapo && dialogo.e.puedeFalso && !fila.declarando
                                    text: "Falso positivo…"
                                    QQC2.ToolTip.text: "Declara que lo que marcó este control no era un error; el motivo queda en la medición"
                                    onClicked: { fila.declarando = true; motivoFalso.forceActiveFocus() }
                                    QQC2.ToolTip.visible: hovered && QQC2.ToolTip.text !== ""
                                    QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                                }
                                QQC2.Button {                         // el control que se resuelve en otra ventana (decisiones §1.22)
                                    visible: (fila.c.accion === "autoevaluar" && dialogo.e.puedeAutoevaluar)
                                             || (fila.c.accion === "matriz" && studio.matriz.disponible)
                                    text: fila.c.accion === "autoevaluar" ? "Autoevaluar…" : "Abrir la matriz…"
                                    onClicked: { dialogo.close(); if (fila.c.accion === "autoevaluar") dialogoRubrica.abrir(); else dialogoMatriz.abrir() }
                                }
                            }
                            QQC2.Label {                               // por qué · fuente
                                Layout.fillWidth: true
                                Layout.leftMargin: Kirigami.Units.gridUnit
                                visible: text !== ""
                                text: [(fila.c.porque || "").replace(/\.$/, ""), fila.c.fuente].filter(x => !!x).join(" · ")
                                wrapMode: Text.WordWrap
                                font: Kirigami.Theme.smallFont
                                color: Kirigami.Theme.disabledTextColor
                            }
                            QQC2.Label {                               // lo medido (C14.1)
                                Layout.fillWidth: true
                                Layout.leftMargin: Kirigami.Units.gridUnit
                                visible: text !== ""
                                text: dialogo.medido(fila.c)
                                font: Kirigami.Theme.smallFont
                                color: fila.c.medicion && fila.c.medicion.marca ? Kirigami.Theme.neutralTextColor : Kirigami.Theme.disabledTextColor
                            }
                            RowLayout {                                // el falso positivo, con su motivo
                                Layout.fillWidth: true
                                Layout.leftMargin: Kirigami.Units.gridUnit
                                visible: fila.declarando
                                spacing: Kirigami.Units.smallSpacing
                                QQC2.TextField {
                                    id: motivoFalso
                                    Layout.fillWidth: true
                                    placeholderText: "Por qué no era un error (queda en la medición del control)"
                                    Accessible.name: "Motivo del falso positivo de «" + fila.c.nombre + "»"
                                    onAccepted: if (text.trim() !== "") { dialogo.e.declararFalso(fila.c.id, text); fila.declarando = false; text = "" }
                                }
                                QQC2.Button {
                                    text: "Declarar"
                                    enabled: motivoFalso.text.trim() !== ""
                                    opacity: enabled ? 1 : 0.5
                                    onClicked: { dialogo.e.declararFalso(fila.c.id, motivoFalso.text); fila.declarando = false; motivoFalso.text = "" }
                                }
                                QQC2.Button { text: "Cancelar"; onClicked: { fila.declarando = false; motivoFalso.text = "" } }
                            }
                            QQC2.TextField {
                                id: nota
                                visible: fila.manual
                                enabled: dialogo.e.puedeMarcar
                                Layout.fillWidth: true
                                Layout.leftMargin: Kirigami.Units.gridUnit
                                text: fila.c.nota || ""
                                placeholderText: "Nota, o por qué no aplica (sin casilla, queda justificado)"
                                Accessible.name: "Nota de «" + fila.c.nombre + "»"
                                onEditingFinished: if (text.trim() !== (fila.c.nota || "")) dialogo.e.marcar(fila.c.id, casilla.checked, text)
                            }
                            Repeater {
                                model: fila.desplegado ? fila.c.hallazgos : fila.c.hallazgos.slice(0, dialogo.visibles)
                                QQC2.ItemDelegate {
                                    id: hallazgo
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Layout.leftMargin: Kirigami.Units.gridUnit - leftPadding
                                    enabled: !!modelData.ruta
                                    Accessible.name: modelData.archivo + ", línea " + modelData.linea + ": " + modelData.texto
                                    onClicked: dialogo.ir(modelData)
                                    contentItem: RowLayout {
                                        spacing: Kirigami.Units.largeSpacing
                                        QQC2.Label {
                                            Layout.alignment: Qt.AlignTop
                                            Layout.preferredWidth: Kirigami.Units.gridUnit * 11
                                            text: hallazgo.modelData.archivo.split("/").pop() + (hallazgo.modelData.linea > 0 ? ":" + hallazgo.modelData.linea : "")
                                            elide: Text.ElideMiddle
                                            font.family: Kirigami.Theme.fixedWidthFont.family
                                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                                            color: Kirigami.Theme.disabledTextColor
                                        }
                                        QQC2.Label {
                                            Layout.fillWidth: true
                                            text: hallazgo.modelData.texto
                                            wrapMode: Text.WordWrap
                                            maximumLineCount: 3
                                            elide: Text.ElideRight
                                            font: Kirigami.Theme.smallFont
                                        }
                                    }
                                }
                            }
                            QQC2.Label {
                                visible: fila.c.hallazgos.length > dialogo.visibles
                                Layout.leftMargin: Kirigami.Units.gridUnit
                                text: fila.desplegado ? "Ver menos" : "Ver los " + fila.c.hallazgos.length
                                font: Kirigami.Theme.smallFont
                                color: Kirigami.Theme.linkColor
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: fila.desplegado = !fila.desplegado }
                            }
                        }
                    }
                }
            }
        }
    }
}
