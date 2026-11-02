// EditorArchivo — un archivo abierto: TextArea con resaltado de KSyntaxHighlighting, números de línea, el
// autocompletado (órdenes, entornos, \ref de las \label y \cite de los .bib: lo calcula Python) y Ctrl+clic para
// ir al PDF (SyncTeX). Cada archivo tiene su TextArea y con él su historial de deshacer. Nunca escribe en disco: lo
// hace Ctrl+S (editor.guardar). Sin colores propios: Kirigami.Theme.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Item {
    id: raiz

    property string ruta: ""
    property string definicion: "LaTeX"
    property bool soloLectura: false
    property bool cargado: false
    property bool modificado: false
    property var inicios: [0]                        // la posición de inicio de cada línea lógica
    property var lineasVisibles: []
    readonly property alias area: area
    readonly property int lineaActual: lineaDe(area.cursorPosition)
    readonly property int columnaActual: area.cursorPosition - (inicios[lineaActual - 1] || 0)
    readonly property bool oscuro: (Kirigami.Theme.backgroundColor.r * 0.299 + Kirigami.Theme.backgroundColor.g * 0.587
                                    + Kirigami.Theme.backgroundColor.b * 0.114) < 0.5

    signal synctex(int linea, int columna)

    // ------------------------------------------------------------------ carga y estado
    function cargar() {
        area.text = studio.editor.leer(ruta)
        area.cursorPosition = 0
        cargado = true
        modificado = false
        recalcular()
    }
    function recargarDesdeDisco() {
        const pos = area.cursorPosition
        cargar()
        area.cursorPosition = Math.min(pos, area.length)
        studio.editor.aceptarDisco(ruta)
        studio.editor.marcarModificado(ruta, false)
    }
    function guardar(forzar) {
        const r = studio.editor.guardar(ruta, area.text, forzar === true)
        if (r === "") { modificado = false }
        return r
    }
    onModificadoChanged: if (cargado) studio.editor.marcarModificado(ruta, modificado)

    // ------------------------------------------------------------------ líneas
    function recalcular() {
        const t = area.text
        const lista = [0]
        let i = t.indexOf("\n")
        while (i >= 0) { lista.push(i + 1); i = t.indexOf("\n", i + 1) }
        inicios = lista
        visibles()
    }
    function lineaDe(pos) {
        let lo = 0, hi = inicios.length - 1
        while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (inicios[mid] <= pos) lo = mid; else hi = mid - 1 }
        return lo + 1
    }
    function visibles() {
        const flick = desplazamiento.contentItem
        const arriba = flick.contentY, abajo = arriba + desplazamiento.height
        let lo = 0, hi = inicios.length - 1
        while (lo < hi) {
            const mid = (lo + hi) >> 1
            const r = area.positionToRectangle(inicios[mid])
            if (r.y + r.height < arriba) lo = mid + 1; else hi = mid
        }
        const salida = []
        for (let k = lo; k < inicios.length; k++) {
            const r = area.positionToRectangle(inicios[k])
            if (r.y > abajo) break
            salida.push({ n: k + 1, y: r.y - arriba, alto: r.height })
        }
        lineasVisibles = salida
    }
    function irALinea(linea, columna) {
        const n = Math.max(1, Math.min(linea, inicios.length))
        area.cursorPosition = Math.min(area.length, (inicios[n - 1] || 0) + Math.max(0, columna || 0))
        area.forceActiveFocus()
        centrarCursor()
    }
    function centrarCursor() {
        const flick = desplazamiento.contentItem
        const r = area.cursorRectangle
        if (r.y < flick.contentY || r.y + r.height > flick.contentY + desplazamiento.height)
            flick.contentY = Math.max(0, Math.min(flick.contentHeight - desplazamiento.height, r.y - desplazamiento.height / 3))
    }
    function seleccionar(inicio, fin) {
        area.select(inicio, fin)
        centrarCursor()
    }

    // ------------------------------------------------------------------ comentar (Ctrl+T)
    function comentar() {
        const a = lineaDe(area.selectionStart), b = lineaDe(Math.max(area.selectionStart, area.selectionEnd - (area.selectionEnd > area.selectionStart ? 1 : 0)))
        let todas = true
        for (let n = a; n <= b; n++) {
            const ini = inicios[n - 1], fin = n < inicios.length ? inicios[n] - 1 : area.length
            if (!/^\s*%/.test(area.getText(ini, fin)) && area.getText(ini, fin).trim() !== "") todas = false
        }
        for (let n = b; n >= a; n--) {
            const ini = inicios[n - 1], fin = n < inicios.length ? inicios[n] - 1 : area.length
            const linea = area.getText(ini, fin)
            if (todas) {
                const m = linea.match(/^(\s*)% ?/)
                if (m) area.remove(ini + m[1].length, ini + m[0].length)
            } else if (linea.trim() !== "") {
                area.insert(ini, "% ")
            }
        }
    }

    // ------------------------------------------------------------------ autocompletado
    function textoAntes() {
        const ini = inicios[lineaDe(area.cursorPosition) - 1] || 0
        return area.getText(ini, area.cursorPosition)
    }
    function completar(forzado) {
        const r = studio.proyectos.completar(textoAntes())
        if (!r.tipo || r.elementos.length === 0 || (!forzado && r.tipo === "orden" && r.prefijo.length < 2)) { sugerencias.close(); return }
        sugerencias.prefijo = r.prefijo
        sugerencias.tipo = r.tipo
        listaSugerencias.model = r.elementos
        listaSugerencias.currentIndex = 0
        const c = area.cursorRectangle
        sugerencias.x = Math.min(raiz.width - sugerencias.width, area.mapToItem(raiz, c.x, c.y).x)
        sugerencias.y = area.mapToItem(raiz, c.x, c.y + c.height).y
        sugerencias.open()
    }
    function aceptarSugerencia() {
        const e = listaSugerencias.model[listaSugerencias.currentIndex]
        if (!e) return
        const p = area.cursorPosition
        area.remove(p - sugerencias.prefijo.length, p)
        area.insert(area.cursorPosition, e.insertar)
        if (sugerencias.tipo === "entorno") {
            const resto = area.getText(area.cursorPosition, Math.min(area.length, area.cursorPosition + 1))
            if (resto !== "}") area.insert(area.cursorPosition, "}")
        }
        sugerencias.close()
    }

    // ------------------------------------------------------------------ la vista
    RowLayout {
        anchors.fill: parent
        spacing: 0

        // números de línea
        Item {
            id: margen
            Layout.fillHeight: true
            Layout.preferredWidth: metricas.advanceWidth("0") * Math.max(3, String(raiz.inicios.length).length) + Kirigami.Units.largeSpacing * 2
            clip: true
            Accessible.ignored: true
            Rectangle { anchors.fill: parent; color: Kirigami.Theme.alternateBackgroundColor }
            Repeater {
                model: raiz.lineasVisibles
                delegate: QQC2.Label {
                    required property var modelData
                    x: 0
                    y: modelData.y
                    width: margen.width - Kirigami.Units.smallSpacing * 2
                    height: modelData.alto
                    horizontalAlignment: Text.AlignRight
                    verticalAlignment: Text.AlignVCenter
                    text: modelData.n
                    font: area.font
                    color: modelData.n === raiz.lineaActual ? Kirigami.Theme.textColor : Kirigami.Theme.disabledTextColor
                }
            }
        }
        Kirigami.Separator { Layout.fillHeight: true }

        QQC2.ScrollView {
            id: desplazamiento
            Layout.fillWidth: true
            Layout.fillHeight: true
            QQC2.ScrollBar.horizontal.policy: studio.ajustes.ajustarLineas ? QQC2.ScrollBar.AlwaysOff : QQC2.ScrollBar.AsNeeded

            QQC2.TextArea {
                id: area
                readOnly: raiz.soloLectura
                textFormat: TextEdit.PlainText
                wrapMode: studio.ajustes.ajustarLineas ? TextEdit.Wrap : TextEdit.NoWrap
                font.family: Kirigami.Theme.fixedWidthFont.family
                font.pointSize: studio.ajustes.tamanoLetra > 0 ? studio.ajustes.tamanoLetra : Kirigami.Theme.fixedWidthFont.pointSize
                selectByMouse: true
                persistentSelection: true
                tabStopDistance: metricas.advanceWidth(" ") * 2
                Accessible.name: "Editor de " + raiz.ruta.split("/").pop()
                background: Rectangle { color: Kirigami.Theme.backgroundColor }

                onTextChanged: { if (raiz.cargado) raiz.modificado = true; temporizador.restart() }
                onWidthChanged: temporizador.restart()
                onCursorPositionChanged: if (sugerencias.opened && area.cursorPosition < sugerencias.inicio) sugerencias.close()

                Keys.onPressed: event => {
                    if (sugerencias.opened) {
                        if (event.key === Qt.Key_Down) { listaSugerencias.incrementCurrentIndex(); event.accepted = true; return }
                        if (event.key === Qt.Key_Up) { listaSugerencias.decrementCurrentIndex(); event.accepted = true; return }
                        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Tab) { raiz.aceptarSugerencia(); event.accepted = true; return }
                        if (event.key === Qt.Key_Escape) { sugerencias.close(); event.accepted = true; return }
                    }
                }
                Keys.onReleased: event => {
                    if (event.text === "\\" || event.text === "{" || event.text === "," || /^[A-Za-z:]$/.test(event.text)) {
                        const antes = raiz.textoAntes()
                        if (/\\[A-Za-z@]{2,}$/.test(antes) || /\\(begin|end)\s*\{[^{}]*$/.test(antes)
                            || /\\[A-Za-z]*(ref|cite|Cite)[A-Za-z]*\*?\s*(\[[^\]]*\]\s*){0,2}\{[^{}]*$/.test(antes)) raiz.completar(false)
                        else if (sugerencias.opened) sugerencias.close()
                    } else if (event.key === Qt.Key_Backspace && sugerencias.opened) {
                        raiz.completar(false)
                    }
                }

                // Ctrl+clic: del código al PDF (SyncTeX)
                TapHandler {
                    acceptedModifiers: Qt.ControlModifier
                    onTapped: (punto) => {
                        const pos = area.positionAt(punto.position.x, punto.position.y)
                        area.cursorPosition = pos
                        raiz.synctex(raiz.lineaDe(pos), pos - raiz.inicios[raiz.lineaDe(pos) - 1])
                    }
                }
            }
        }
    }

    Connections {
        target: desplazamiento.contentItem
        function onContentYChanged() { raiz.visibles() }
        function onHeightChanged() { raiz.visibles() }
    }
    Timer { id: temporizador; interval: 60; onTriggered: raiz.recalcular() }
    FontMetrics { id: metricas; font: area.font }

    Loader {
        active: raiz.definicion !== ""
        source: "ResaltadoEditor.qml"
        onLoaded: { item.nombreDefinicion = raiz.definicion; item.oscuro = Qt.binding(() => raiz.oscuro); item.textEdit = area }
    }

    // la lista de sugerencias, en el cursor
    QQC2.Popup {
        id: sugerencias
        property string prefijo: ""
        property string tipo: ""
        property int inicio: area.cursorPosition - prefijo.length
        width: Kirigami.Units.gridUnit * 24
        height: Math.min(Kirigami.Units.gridUnit * 12, listaSugerencias.contentHeight + topPadding + bottomPadding)
        padding: 1
        focus: false
        closePolicy: QQC2.Popup.CloseOnPressOutside
        contentItem: ListView {
            id: listaSugerencias
            clip: true
            keyNavigationEnabled: false
            Accessible.name: "Sugerencias"
            delegate: QQC2.ItemDelegate {
                required property var modelData
                required property int index
                width: listaSugerencias.width
                highlighted: ListView.isCurrentItem
                onClicked: { listaSugerencias.currentIndex = index; raiz.aceptarSugerencia() }
                contentItem: RowLayout {
                    spacing: Kirigami.Units.smallSpacing
                    QQC2.Label { text: modelData.texto; font.family: Kirigami.Theme.fixedWidthFont.family; elide: Text.ElideRight; Layout.maximumWidth: parent.width * 0.55 }
                    QQC2.Label { text: modelData.detalle || ""; color: Kirigami.Theme.disabledTextColor; elide: Text.ElideRight; Layout.fillWidth: true; font: Kirigami.Theme.smallFont }
                }
            }
        }
    }
}
