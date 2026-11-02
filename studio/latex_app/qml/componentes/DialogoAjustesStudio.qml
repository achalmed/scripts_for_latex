// DialogoAjustesStudio — «Configurar LaTeX Studio…» (Ctrl+Mayús+,): Carpetas de trabajo (las de omisión, que salen de
// core/env.py, y las añadidas con el diálogo de carpetas de KDE; la profundidad), Compilación (rutas de TeX extra,
// compilar al guardar), Editor (tamaño de letra, ajuste de líneas) y Sistema (editor externo y terminal). Todo va a los
// ajustes del usuario (QSettings), nunca al repo.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import QtQuick.Dialogs
import org.kde.kirigami as Kirigami
import org.kde.kirigamiaddons.formcard as FormCard
import GuiComun

DialogoAjustes {
    id: dialogo
    title: "Configurar LaTeX Studio"
    readonly property var a: studio.ajustes
    modulos: [
        { titulo: "Carpetas de trabajo", icono: "folder-open", pagina: paginaCarpetas },
        { titulo: "Compilación", icono: "run-build", pagina: paginaCompilacion },
        { titulo: "Editor", icono: "document-edit", pagina: paginaEditor },
        { titulo: "Sistema", icono: "configure", pagina: paginaSistema }
    ]
    onGuardado: { dialogo.a.guardar(); ventana.mensajes.mostrar("Preferencias guardadas.", "positivo") }

    FolderDialog {
        id: selectorRutaTex
        title: "Ruta de TeX (clases y paquetes de un marco)"
        onAccepted: { const e = dialogo.a.anadirRutaTex(decodeURIComponent(selectedFolder.toString().replace("file://", ""))); if (e) ventana.mensajes.mostrar(e, "error") }
    }

    Component {
        id: paginaCarpetas
        ColumnLayout {
            FormCard.FormHeader { title: "Dónde se buscan proyectos" }
            FormCard.FormCard {
                Repeater {
                    model: dialogo.a.carpetas
                    delegate: FormCard.FormSwitchDelegate {
                        required property var modelData
                        text: modelData.nombre + (modelData.existe ? "" : " (no existe)")
                        description: modelData.ruta + " · " + modelData.origen
                        checked: modelData.activa
                        enabled: modelData.existe || modelData.quitable
                        onToggled: modelData.quitable ? (checked ? null : dialogo.a.quitarCarpeta(modelData.ruta)) : dialogo.a.activarCarpeta(modelData.ruta, checked)
                    }
                }
                FormCard.FormButtonDelegate { text: "Añadir una carpeta…"; icon.name: "list-add"; onClicked: studio.interfaz.pedir("anadir_carpeta", {}) }
            }
            FormCard.FormHeader { title: "Recorrido" }
            FormCard.FormCard {
                FormCard.FormSpinBoxDelegate { label: "Profundidad (carpetas por debajo de cada una)"; from: 1; to: 12; value: dialogo.a.profundidad; onValueChanged: dialogo.a.profundidad = value }
                FormCard.FormTextDelegate { text: "Se saltan las carpetas ocultas, node_modules, _site, _freeze, .quarto, site_libs, .build y build. Lo leído se guarda en una caché: la segunda búsqueda solo relee lo que cambió." }
            }
        }
    }
    Component {
        id: paginaCompilacion
        ColumnLayout {
            FormCard.FormHeader { title: "Motor" }
            FormCard.FormCard {
                FormCard.FormTextDelegate { text: "Cada proyecto se compila con su compilador y su motor: el de su marco (scripts/build.sh), latexmk si tiene latexmkrc, o script_compilar_latex con el motor que declare (% !TEX program, arara) y, sin declaración, LuaLaTeX + Biber." }
                FormCard.FormSwitchDelegate { text: "Compilar al guardar"; description: "Ctrl+S guarda y compila el proyecto abierto"; checked: dialogo.a.compilarAlGuardar; onToggled: dialogo.a.compilarAlGuardar = checked }
            }
            FormCard.FormHeader { title: "Rutas de TeX extra (TEXINPUTS)" }
            FormCard.FormCard {
                Repeater {
                    model: dialogo.a.rutasTex
                    delegate: FormCard.FormButtonDelegate {
                        required property var modelData
                        text: modelData
                        icon.name: "list-remove"
                        description: "Quitar de la lista (la carpeta no se toca)"
                        onClicked: dialogo.a.quitarRutaTex(modelData)
                    }
                }
                FormCard.FormButtonDelegate { text: "Añadir una ruta…"; icon.name: "list-add"; onClicked: selectorRutaTex.open() }
                FormCard.FormTextDelegate { text: "Para compilar con script_compilar_latex o latexmk documentos cuyas clases viven en un marco que no está instalado en TeX Live." }
            }
        }
    }
    Component {
        id: paginaEditor
        ColumnLayout {
            FormCard.FormHeader { title: "Texto" }
            FormCard.FormCard {
                FormCard.FormSpinBoxDelegate { label: "Tamaño de letra (0: el de la fuente fija del sistema)"; from: 0; to: 32; value: dialogo.a.tamanoLetra; onValueChanged: dialogo.a.tamanoLetra = value }
                FormCard.FormSwitchDelegate { text: "Ajustar las líneas largas"; checked: dialogo.a.ajustarLineas; onToggled: dialogo.a.ajustarLineas = checked }
            }
        }
    }
    Component {
        id: paginaSistema
        ColumnLayout {
            function guardar() { dialogo.a.editor = editor.text; dialogo.a.terminal = terminal.text }
            FormCard.FormHeader { title: "Sistema" }
            FormCard.FormCard {
                FormCard.FormTextFieldDelegate { id: editor; label: "Editor externo («Abrir en el editor externo»)"; text: dialogo.a.editor; placeholderText: "kate" }
                FormCard.FormTextFieldDelegate { id: terminal; label: "Terminal («Abrir terminal aquí»)"; text: dialogo.a.terminal; placeholderText: "konsole" }
            }
        }
    }
}
