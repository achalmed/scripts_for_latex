// DialogoAlt — el texto alternativo de una figura, obligatorio al insertarla (decisiones §1.22, contrato §8; mejora C8.3):
// cuando el marco da `insertar_alt` (la orden con el hueco {alt}), el doble clic en la figura de la pestaña Datos abre
// este diálogo con el borrador que el marco arma desde el indicador (o el texto ya aprobado). El autor lo lee, lo
// corrige y lo aprueba; sin texto no se inserta. Lo aprobado entra en la orden y de ahí al PDF etiquetado.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.Dialog {
    id: dialogo
    signal insertar(string texto)
    property var figura: null

    title: "Texto alternativo de la figura"
    preferredWidth: Kirigami.Units.gridUnit * 34
    standardButtons: Kirigami.Dialog.NoButton
    padding: Kirigami.Units.largeSpacing

    function abrir(f) { figura = f; alt.text = f.alt || ""; open(); alt.forceActiveFocus() }
    // lo que LaTeX no admite tal cual dentro de la clave alt={…}
    function escapar(t) { return t.replace(/\s+/g, " ").trim().replace(/[{}]/g, "").replace(/([%&#_$])/g, "\\$1") }

    footer: QQC2.ToolBar {
        position: QQC2.ToolBar.Footer
        padding: Kirigami.Units.largeSpacing
        background: Item {}
        RowLayout {
            anchors.fill: parent
            QQC2.Label {
                Layout.fillWidth: true
                text: alt.text.trim().length + " caracteres"
                font: Kirigami.Theme.smallFont
                color: alt.text.trim().length > 250 ? Kirigami.Theme.neutralTextColor : Kirigami.Theme.disabledTextColor
            }
            Chip { text: "Cancelar"; onClicked: dialogo.close() }
            Chip {
                text: "Insertar con este texto"; icono: "insert-image"; destacado: true
                enabled: alt.text.trim() !== ""
                opacity: enabled ? 1 : 0.5
                onClicked: { dialogo.insertar(dialogo.figura.insertarAlt.replace("{alt}", dialogo.escapar(alt.text))); dialogo.close() }
            }
        }
    }

    ColumnLayout {
        spacing: Kirigami.Units.smallSpacing
        Kirigami.Heading { level: 4; text: dialogo.figura ? dialogo.figura.titulo || dialogo.figura.id : ""; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        QQC2.Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: dialogo.figura && dialogo.figura.altAprobado ? "El texto ya aprobado de esta figura. Puedes ajustarlo."
                  : "Un borrador desde el indicador: léelo y corrígelo. Di qué muestra la figura (la tendencia, la comparación, el hallazgo), no cómo se ve."
        }
        QQC2.TextArea {
            id: alt
            Layout.fillWidth: true
            Layout.minimumHeight: Kirigami.Units.gridUnit * 5
            wrapMode: TextEdit.Wrap
            placeholderText: "Qué muestra la figura, para quien no la ve"
            Accessible.name: "Texto alternativo"
        }
        QQC2.Label {                                       // por qué · fuente
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            font: Kirigami.Theme.smallFont
            color: Kirigami.Theme.disabledTextColor
            text: "Quien lee con un lector de pantalla recibe la figura por su texto alternativo · W3C (2024, Calibre 10443); LaTeX Project (2025)"
        }
    }
}
