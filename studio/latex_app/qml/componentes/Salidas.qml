// Salidas — el PDF y los auxiliares que hay en la carpeta del documento actual (los que main.sh -c borraría), con tipo,
// tamaño y fecha; doble clic abre el archivo con el sistema; Abrir el PDF y Limpiar auxiliares… al pie.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

ColumnLayout {
    readonly property var d: studio.documentos
    spacing: 0
    TablaDatos {
        id: tabla
        Layout.fillWidth: true
        Layout.fillHeight: true
        modelo: d.salidas
        umbralEstrecho: Kirigami.Units.gridUnit * 22
        columnas: [
            { ancho: 0, minimo: 10, conIcono: true, semantica: true },
            { ancho: 5, secundaria: true },
            { ancho: 6, alinear: "derecha", mono: true },
            { ancho: 8, secundaria: true, estrecho: true }
        ]
        mensajeVacio: !d.hayActual ? "Ningún documento" : "Ni PDF ni auxiliares en la carpeta: el documento no se ha compilado (o ya se limpió)"
        iconoVacio: "application-pdf"
        onActivada: fila => studio.espacio.abrir(d.salidas.fila(fila).ruta)
        menuContextual: MenuAcciones {
            acciones: studio.acciones
            conAtajos: false
            elementos: [{ tipo: "accion", nombre: "doc.pdf" }, { tipo: "accion", nombre: "doc.limpiar" }, { tipo: "separador" }, { tipo: "accion", nombre: "archivo.dolphin" }]
        }
    }
    RowLayout {
        visible: d.hayActual
        Layout.fillWidth: true
        Layout.margins: Kirigami.Units.largeSpacing
        spacing: Kirigami.Units.smallSpacing
        QQC2.Label { Layout.fillWidth: true; text: d.salidas.filas + " archivo" + (d.salidas.filas === 1 ? "" : "s"); font: Kirigami.Theme.smallFont; color: Kirigami.Theme.disabledTextColor }
        BotonAccion { accion: studio.acciones.accion("doc.limpiar") }
        BotonAccion { accion: studio.acciones.accion("doc.pdf") }
    }
}
