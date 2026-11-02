// OpcionesCompilacion — las opciones de la sesión (studio.opciones, en QSettings): motor (solo LuaLaTeX: auto o
// lualatex), pasadas, bibliografía (ninguna · Biber · BibTeX heredado), índice, glosarios, borrador, carpeta del PDF,
// abrir el PDF al terminar, recompilar al guardar; la orden que correría; Simular y Compilar al pie.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

QQC2.ScrollView {
    id: pagina
    readonly property var o: studio.opciones
    readonly property var d: studio.documentos
    contentWidth: availableWidth
    QQC2.ScrollBar.horizontal.policy: QQC2.ScrollBar.AlwaysOff
    ColumnLayout {
        width: pagina.availableWidth - Kirigami.Units.largeSpacing * 2
        x: Kirigami.Units.largeSpacing
        y: Kirigami.Units.largeSpacing
        spacing: Kirigami.Units.largeSpacing

        Kirigami.FormLayout {
            Layout.fillWidth: true
            QQC2.ComboBox {
                id: motor
                Kirigami.FormData.label: "Motor:"
                Layout.fillWidth: true
                model: pagina.o.motores
                textRole: "texto"
                valueRole: "valor"
                currentIndex: Math.max(0, pagina.o.motores.findIndex(m => m.valor === pagina.o.motor))
                onActivated: pagina.o.fijarMotor(currentValue)
                Accessible.name: "Motor"
            }
            QQC2.Label {
                Kirigami.FormData.label: ""
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                font: Kirigami.Theme.smallFont
                color: Kirigami.Theme.disabledTextColor
                text: pagina.d.motorDeclarado !== "" && pagina.d.motorDeclarado !== "lualatex"
                      ? "Este .tex declara «% !TEX program = " + pagina.d.motorDeclarado + "»: en automático la CLI lo obedece (material heredado)."
                      : "LuaLaTeX + Biber es el motor del ecosistema; pdfLaTeX y XeLaTeX no se ofrecen (solo por «% !TEX program» en un .tex heredado)."
            }
            QQC2.SpinBox {
                id: pasadas
                Kirigami.FormData.label: "Pasadas:"
                from: 1; to: 5
                value: pagina.o.pasadas
                onValueModified: pagina.o.pasadas = value
                Accessible.name: "Pasadas"
            }
            QQC2.ComboBox {
                id: bibliografia
                Kirigami.FormData.label: "Bibliografía:"
                Layout.fillWidth: true
                model: pagina.o.bibliografias
                textRole: "texto"
                valueRole: "valor"
                currentIndex: Math.max(0, pagina.o.bibliografias.findIndex(b => b.valor === pagina.o.bibliografia))
                onActivated: pagina.o.fijarBibliografia(currentValue)
                Accessible.name: "Bibliografía"
            }
            QQC2.CheckBox { Kirigami.FormData.label: ""; text: "Índice (makeindex)"; checked: pagina.o.indice; onToggled: pagina.o.indice = checked }
            QQC2.CheckBox { Kirigami.FormData.label: ""; text: "Glosarios (makeglossaries)"; checked: pagina.o.glosarios; onToggled: pagina.o.glosarios = checked }
            QQC2.CheckBox { Kirigami.FormData.label: ""; text: "Borrador: solo comprobar que compila, sin PDF"; checked: pagina.o.borrador; onToggled: pagina.o.borrador = checked }
            CampoRuta {
                id: salida
                Kirigami.FormData.label: "Mover el PDF a:"
                Layout.fillWidth: true
                texto: pagina.o.salida
                marcador: "junto al .tex"
                titulo: "Carpeta del PDF"
                nombreAccesible: "Carpeta del PDF"
                onAceptada: t => pagina.o.salida = t
                Connections { target: pagina.o; function onCambiado() { salida.texto = pagina.o.salida } }
            }
            QQC2.CheckBox { Kirigami.FormData.label: ""; text: "Abrir el PDF al terminar"; checked: pagina.o.abrirAlTerminar; onToggled: pagina.o.abrirAlTerminar = checked }
            QQC2.CheckBox { Kirigami.FormData.label: ""; text: "Recompilar al guardar el .tex"; checked: pagina.o.vigilar; onToggled: pagina.o.vigilar = checked }
            QQC2.Label { Kirigami.FormData.label: "Efectivo:"; text: pagina.o.descripcion; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            QQC2.Label {
                Kirigami.FormData.label: "Orden:"
                visible: pagina.d.hayActual
                text: pagina.o.ordenTexto(pagina.d.actual)
                wrapMode: Text.WrapAnywhere
                Layout.fillWidth: true
                font: Kirigami.Theme.fixedWidthFont
                color: Kirigami.Theme.disabledTextColor
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing
            Item { Layout.fillWidth: true }
            BotonAccion { accion: studio.acciones.accion("doc.cancelar"); conTexto: false; visible: studio.corrida.enCurso }
            BotonAccion { accion: studio.acciones.accion("doc.simular") }
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
