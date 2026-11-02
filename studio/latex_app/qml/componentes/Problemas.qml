// Problemas — cada error, aviso y aviso tipográfico del registro de la última corrida del documento actual, con su archivo
// y su línea (GuiComun.ListaDiagnosticos); Intro o doble clic abre el editor ahí; filtros por nivel arriba.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

ColumnLayout {
    id: pagina
    readonly property var d: studio.documentos
    readonly property alias filaActual: lista.filaActual
    spacing: 0
    RowLayout {
        Layout.fillWidth: true
        Layout.margins: Kirigami.Units.smallSpacing
        spacing: Kirigami.Units.smallSpacing
        visible: pagina.d.hayActual && (pagina.d.nErrores + pagina.d.nAvisos + pagina.d.nTipografia) > 0
        QQC2.ToolButton { checkable: true; checked: pagina.d.mostrarErrores; onToggled: pagina.d.mostrarErrores = checked; icon.name: "data-error"; text: pagina.d.nErrores; Accessible.name: "Errores: " + pagina.d.nErrores; QQC2.ToolTip.text: "Errores"; QQC2.ToolTip.visible: hovered }
        QQC2.ToolButton { checkable: true; checked: pagina.d.mostrarAvisos; onToggled: pagina.d.mostrarAvisos = checked; icon.name: "data-warning"; text: pagina.d.nAvisos; Accessible.name: "Avisos: " + pagina.d.nAvisos; QQC2.ToolTip.text: "Avisos"; QQC2.ToolTip.visible: hovered }
        QQC2.ToolButton { checkable: true; checked: pagina.d.mostrarTipografia; onToggled: pagina.d.mostrarTipografia = checked; icon.name: "format-justify-fill"; text: pagina.d.nTipografia; Accessible.name: "Tipografía: " + pagina.d.nTipografia; QQC2.ToolTip.text: "Avisos tipográficos (Overfull, Underfull)"; QQC2.ToolTip.visible: hovered }
        Item { Layout.fillWidth: true }
        QQC2.Label { text: "Intro: ir a la línea"; font: Kirigami.Theme.smallFont; color: Kirigami.Theme.disabledTextColor }
    }
    ListaDiagnosticos {
        id: lista
        Layout.fillWidth: true
        Layout.fillHeight: true
        modelo: pagina.d.problemas
        nombreAccesible: "Problemas de " + (pagina.d.nombre || "ningún documento")
        mensajeVacio: !pagina.d.hayActual ? "Ningún documento" : pagina.d.origenProblemas === "" ? "Sin registro todavía: compila el documento (F5) para leer sus errores y avisos"
                                          : pagina.d.nProblemas === 0 ? "Sin errores ni avisos" : "Todos los problemas están filtrados"
        iconoVacio: pagina.d.hayActual && pagina.d.origenProblemas !== "" && pagina.d.nProblemas === 0 ? "data-success" : "data-information"
        onActivada: fila => pagina.d.irA(fila)
        menuContextual: MenuAcciones {
            acciones: studio.acciones
            conAtajos: false
            elementos: [{ tipo: "accion", nombre: "prob.ir" }, { tipo: "accion", nombre: "doc.editor" }, { tipo: "separador" }, { tipo: "accion", nombre: "doc.compilar" }]
        }
    }
}
