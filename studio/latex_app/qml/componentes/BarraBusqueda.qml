// BarraBusqueda — buscar y reemplazar en el archivo actual (Ctrl+F, Ctrl+R), como la barra de Kate: texto, expresión
// regular, mayúsculas, palabra entera, anterior y siguiente, reemplazar y reemplazar todo, «n de m». La búsqueda y
// los reemplazos los calcula Python (editor.buscar / editor.reemplazar, posiciones de QML); aquí se seleccionan y se
// aplican con remove/insert para que Ctrl+Z los deshaga.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

QQC2.ToolBar {
    id: barra

    property var editor: null                     // el EditorArchivo actual
    property bool conReemplazo: false
    property var coincidencias: []
    property int actual: -1
    property string error: ""

    position: QQC2.ToolBar.Footer
    visible: false

    function abrir(reemplazar) {
        conReemplazo = reemplazar
        visible = true
        if (editor && editor.area.selectedText && editor.area.selectedText.indexOf("\n") < 0) campo.text = editor.area.selectedText
        campo.forceActiveFocus()
        campo.selectAll()
        buscar()
    }
    function cerrar() { visible = false; if (editor) editor.area.forceActiveFocus() }
    function buscar() {
        if (!editor || campo.text === "") { coincidencias = []; actual = -1; error = ""; return }
        const r = studio.editor.buscar(editor.area.text, campo.text, regex.checked, mayusculas.checked, palabra.checked)
        error = r.error
        coincidencias = r.coincidencias
        actual = -1
        const pos = editor.area.selectionStart
        for (let i = 0; i < coincidencias.length; i++) if (coincidencias[i][0] >= pos) { actual = i; break }
        if (actual < 0 && coincidencias.length) actual = 0
        marcar()
    }
    function marcar() {
        if (editor && actual >= 0 && actual < coincidencias.length) editor.seleccionar(coincidencias[actual][0], coincidencias[actual][1])
    }
    function siguiente() { if (coincidencias.length) { actual = (actual + 1) % coincidencias.length; marcar() } }
    function anterior() { if (coincidencias.length) { actual = (actual - 1 + coincidencias.length) % coincidencias.length; marcar() } }
    function aplicar(cambios) {
        for (const c of cambios) { editor.area.remove(c[0], c[1]); editor.area.insert(c[0], c[2]) }
    }
    function reemplazarUno() {
        if (!editor || actual < 0) return
        const r = studio.editor.reemplazar(editor.area.text, campo.text, reemplazo.text, regex.checked, mayusculas.checked, palabra.checked, coincidencias[actual][0])
        if (r.error) { error = r.error; return }
        aplicar(r.cambios)
        buscar()
    }
    function reemplazarTodo() {
        if (!editor) return
        const r = studio.editor.reemplazar(editor.area.text, campo.text, reemplazo.text, regex.checked, mayusculas.checked, palabra.checked, -1)
        if (r.error) { error = r.error; return }
        aplicar(r.cambios)
        ventana.mensajes.mostrar(r.cambios.length + " reemplazo" + (r.cambios.length === 1 ? "" : "s") + " (Ctrl+Z los deshace).", "informacion")
        buscar()
    }

    GridLayout {
        anchors.fill: parent
        columns: 2
        columnSpacing: Kirigami.Units.smallSpacing
        rowSpacing: Kirigami.Units.smallSpacing

        QQC2.TextField {
            id: campo
            Layout.fillWidth: true
            placeholderText: "Buscar"
            Accessible.name: "Buscar"
            onTextChanged: barra.buscar()
            Keys.onReturnPressed: event => { if (event.modifiers & Qt.ShiftModifier) barra.anterior(); else barra.siguiente() }
            Keys.onEscapePressed: barra.cerrar()
        }
        RowLayout {
            spacing: Kirigami.Units.smallSpacing
            QQC2.Label {
                text: barra.error !== "" ? barra.error : campo.text === "" ? "" : barra.coincidencias.length === 0 ? "sin coincidencias"
                      : (barra.actual + 1) + " de " + barra.coincidencias.length
                color: barra.error !== "" || (campo.text !== "" && barra.coincidencias.length === 0) ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.disabledTextColor
                Layout.maximumWidth: Kirigami.Units.gridUnit * 14
                elide: Text.ElideRight
            }
            QQC2.ToolButton { icon.name: "go-up"; display: QQC2.AbstractButton.IconOnly; text: "Anterior (Mayús+Intro)"; Accessible.name: text; QQC2.ToolTip.text: text; QQC2.ToolTip.visible: hovered; onClicked: barra.anterior() }
            QQC2.ToolButton { icon.name: "go-down"; display: QQC2.AbstractButton.IconOnly; text: "Siguiente (Intro)"; Accessible.name: text; QQC2.ToolTip.text: text; QQC2.ToolTip.visible: hovered; onClicked: barra.siguiente() }
            QQC2.ToolButton { id: regex; checkable: true; text: ".*"; Accessible.name: "Expresión regular"; QQC2.ToolTip.text: "Expresión regular (Python: \\d, \\b, grupos y \\1 en el reemplazo)"; QQC2.ToolTip.visible: hovered; onToggled: barra.buscar() }
            QQC2.ToolButton { id: mayusculas; checkable: true; text: "Aa"; Accessible.name: "Distinguir mayúsculas"; QQC2.ToolTip.text: Accessible.name; QQC2.ToolTip.visible: hovered; onToggled: barra.buscar() }
            QQC2.ToolButton { id: palabra; checkable: true; text: "\\b"; Accessible.name: "Palabra entera"; QQC2.ToolTip.text: Accessible.name; QQC2.ToolTip.visible: hovered; onToggled: barra.buscar() }
            QQC2.ToolButton { icon.name: "dialog-close"; display: QQC2.AbstractButton.IconOnly; text: "Cerrar (Esc)"; Accessible.name: text; onClicked: barra.cerrar() }
        }
        QQC2.TextField {
            id: reemplazo
            visible: barra.conReemplazo
            Layout.fillWidth: true
            placeholderText: "Reemplazar por"
            Accessible.name: "Reemplazar por"
            Keys.onReturnPressed: barra.reemplazarUno()
            Keys.onEscapePressed: barra.cerrar()
        }
        RowLayout {
            visible: barra.conReemplazo
            spacing: Kirigami.Units.smallSpacing
            QQC2.Button { text: "Reemplazar"; enabled: barra.actual >= 0 && !(barra.editor && barra.editor.soloLectura); onClicked: barra.reemplazarUno() }
            QQC2.Button { text: "Reemplazar todo"; enabled: barra.coincidencias.length > 0 && !(barra.editor && barra.editor.soloLectura); onClicked: barra.reemplazarTodo() }
        }
    }
}
