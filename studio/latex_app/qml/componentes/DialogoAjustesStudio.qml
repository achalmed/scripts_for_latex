// DialogoAjustesStudio — «Configurar LaTeX Studio…» (Ctrl+Mayús+,): General (el editor de «Ir a la línea» y la terminal).
// Las opciones de compilación no están aquí: viven en la pestaña Opciones del documento.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import org.kde.kirigamiaddons.formcard as FormCard
import GuiComun

DialogoAjustes {
    id: dialogo
    title: "Configurar LaTeX Studio"
    readonly property var a: studio.ajustes
    modulos: [{ titulo: "General", icono: "configure", pagina: paginaGeneral }]
    onGuardado: { dialogo.a.guardar(); ventana.mensajes.mostrar("Preferencias guardadas.", "positivo") }

    Component {
        id: paginaGeneral
        ColumnLayout {
            function guardar() { dialogo.a.editor = editor.text; dialogo.a.terminal = terminal.text }
            FormCard.FormHeader { title: "Sistema" }
            FormCard.FormCard {
                FormCard.FormTextFieldDelegate { id: editor; label: "Editor para «Ir a la línea» y «Abrir en el editor»"; text: dialogo.a.editor; placeholderText: "kate" }
                FormCard.FormTextDelegate { text: "Kate y KWrite abren en la línea con --line; VS Code (code) con -g. Si no está, el .tex se abre con la aplicación del sistema." }
                FormCard.FormTextFieldDelegate { id: terminal; label: "Terminal para «Abrir terminal aquí»"; text: dialogo.a.terminal; placeholderText: "konsole" }
            }
            FormCard.FormHeader { title: "Compilación" }
            FormCard.FormCard {
                FormCard.FormTextDelegate { text: "Las opciones (motor, pasadas, bibliografía, índice, glosarios, borrador, carpeta del PDF) están en la pestaña Opciones del documento y se recuerdan entre sesiones. El motor del ecosistema es LuaLaTeX + Biber; la CLI es script_compilar_latex/main.sh (alias compilar)." }
            }
        }
    }
}
