// Resumen — el documento actual: ruta, carpeta, motor (el declarado o LuaLaTeX), modificado, estado con color semántico,
// el PDF (fecha, tamaño, páginas) y la última compilación del historial; Compilar y Abrir el PDF al pie.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

QQC2.ScrollView {
    id: pagina
    readonly property var d: studio.documentos
    function colorEstado(nivel) {
        switch (nivel) {
        case "positivo": return Kirigami.Theme.positiveTextColor
        case "neutro": return Kirigami.Theme.neutralTextColor
        case "negativo": return Kirigami.Theme.negativeTextColor
        case "activo": return Kirigami.Theme.activeTextColor
        case "inactivo": return Kirigami.Theme.disabledTextColor
        default: return Kirigami.Theme.textColor
        }
    }
    contentWidth: availableWidth
    QQC2.ScrollBar.horizontal.policy: QQC2.ScrollBar.AlwaysOff
    ColumnLayout {
        width: pagina.availableWidth - Kirigami.Units.largeSpacing * 2
        x: Kirigami.Units.largeSpacing
        y: Kirigami.Units.largeSpacing
        spacing: Kirigami.Units.largeSpacing

        Kirigami.PlaceholderMessage {
            Layout.fillWidth: true
            visible: !pagina.d.hayActual
            text: "Ningún documento"
            explanation: "Elige un .tex en la tabla, ábrelo con Ctrl+O o suéltalo en la ventana. F5 lo compila con LuaLaTeX y Biber."
            icon.name: "text-x-tex"
        }
        Kirigami.FormLayout {
            Layout.fillWidth: true
            visible: pagina.d.hayActual
            QQC2.Label { Kirigami.FormData.label: "Documento:"; text: pagina.d.nombre; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
            QQC2.Label { Kirigami.FormData.label: "Carpeta:"; text: pagina.d.carpetaActual; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true; color: Kirigami.Theme.disabledTextColor }
            QQC2.Label { Kirigami.FormData.label: "Motor:"; text: pagina.d.motorTexto; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            QQC2.Label { Kirigami.FormData.label: "Modificado:"; text: pagina.d.modificado }
            QQC2.Label { Kirigami.FormData.label: "Estado:"; text: pagina.d.estadoTexto + (pagina.d.resumenProblemas && pagina.d.resumenProblemas !== "sin problemas" ? " · " + pagina.d.resumenProblemas : ""); color: pagina.colorEstado(pagina.d.estadoNivel); wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Kirigami.Separator { Kirigami.FormData.isSection: true; Kirigami.FormData.label: "PDF" }
            QQC2.Label { Kirigami.FormData.label: "Archivo:"; text: pagina.d.hayPdf ? pagina.d.pdfRuta : "todavía no hay PDF (F5 lo compila)"; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true; color: pagina.d.hayPdf ? Kirigami.Theme.textColor : Kirigami.Theme.disabledTextColor }
            QQC2.Label { Kirigami.FormData.label: "Fecha:"; visible: pagina.d.hayPdf; text: pagina.d.pdfFecha }
            QQC2.Label { Kirigami.FormData.label: "Tamaño:"; visible: pagina.d.hayPdf; text: pagina.d.pdfTamano + (pagina.d.pdfPaginas > 0 ? " · " + pagina.d.pdfPaginas + " página" + (pagina.d.pdfPaginas === 1 ? "" : "s") : "") }
            Kirigami.Separator { Kirigami.FormData.isSection: true; Kirigami.FormData.label: "Última compilación" }
            QQC2.Label { Kirigami.FormData.label: "Aquí:"; text: pagina.d.ultimaCompilacion || "nunca desde esta ventana"; wrapMode: Text.WordWrap; Layout.fillWidth: true; color: pagina.d.ultimaCompilacion ? Kirigami.Theme.textColor : Kirigami.Theme.disabledTextColor }
            QQC2.Label { Kirigami.FormData.label: "Opciones:"; text: studio.opciones.descripcion; wrapMode: Text.WordWrap; Layout.fillWidth: true; color: Kirigami.Theme.disabledTextColor }
        }
        RowLayout {
            visible: pagina.d.hayActual
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing
            Item { Layout.fillWidth: true }
            BotonAccion { accion: studio.acciones.accion("archivo.copiar"); conTexto: false }
            BotonAccion { accion: studio.acciones.accion("doc.pdf") }
            QQC2.Button {
                readonly property var a: studio.acciones.accion("doc.compilar")
                highlighted: true
                text: a.textoPlano; icon.name: a.icono; enabled: a.habilitada
                onClicked: a.disparar()
                QQC2.ToolTip.text: a.descripcion + " (" + a.atajoTexto + ")"; QQC2.ToolTip.visible: hovered
            }
        }
        Item { Layout.preferredHeight: Kirigami.Units.largeSpacing }
    }
}
