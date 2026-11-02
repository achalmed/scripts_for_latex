// HistorialCompilaciones — cada compilación hecha desde la ventana (proyecto, resultado, duración, detalle, cuándo;
// las 60 últimas, en los ajustes del usuario), ordenable y filtrable; doble clic abre ese proyecto. Vaciar solo borra
// la lista.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

ColumnLayout {
    readonly property var h: studio.historial
    spacing: 0
    RowLayout {
        Layout.fillWidth: true
        Layout.margins: Kirigami.Units.smallSpacing
        Kirigami.SearchField { Layout.preferredWidth: Kirigami.Units.gridUnit * 12; placeholderText: "Filtrar"; onTextChanged: h.modelo.filtrar(text) }
        QQC2.Label { Layout.fillWidth: true; text: h.total + " compilación" + (h.total === 1 ? "" : "es"); color: Kirigami.Theme.disabledTextColor }
        QQC2.Button { text: "Vaciar…"; icon.name: "edit-clear-history"; flat: true; enabled: h.total > 0; onClicked: studio.interfaz.pedir("historial_vaciar", {}) }
    }
    TablaDatos {
        id: tabla
        Layout.fillWidth: true
        Layout.fillHeight: true
        modelo: h.modelo
        claveAjustes: "historial"
        umbralEstrecho: Kirigami.Units.gridUnit * 34
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
        onOrdenar: (columna, descendente) => h.modelo.ordenar(columna, descendente)
        onActivada: fila => studio.interfaz.pedir("abrir_proyecto", { ruta: h.tabla.fila(h.modelo.filaOrigen(fila)).ruta })
    }
}
