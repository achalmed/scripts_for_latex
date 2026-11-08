// DialogoConfigurarDocumento — «Configurar el documento…» (Ctrl+Alt+D): lo que el latex-studio.yml del marco del
// documento permite configurar (metadatos, elementos visibles, opciones de la clase), un módulo por sección y un control
// por campo según su tipo. Aceptar no escribe: muestra la diferencia y escribe solo al confirmar (y, si se pide,
// compila). Contrato: docs/configuracion-de-documentos.md. Los datos y la escritura son de studio.configuracion.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import org.kde.kirigamiaddons.formcard as FormCard
import GuiComun

DialogoAjustes {
    id: dialogo
    readonly property var c: studio.configuracion
    title: "Configurar el documento" + (c.nombre ? " — " + c.nombre : "")
    preferredWidth: Kirigami.Units.gridUnit * 48
    preferredHeight: Kirigami.Units.gridUnit * 34
    modulos: c.secciones.map((s, i) => ({ titulo: s.titulo, icono: s.icono, pagina: paginaSeccion, indice: i }))

    function abrirPara(ruta) {
        const e = c.abrir(ruta)
        if (e) { ventana.mensajes.mostrar(e, "error"); return }
        dialogo.moduloActual = 0
        dialogo.open()
    }
    onGuardado: {
        const d = c.diferencia()
        if (!d) { ventana.mensajes.mostrar("Sin cambios: el documento ya está así.", "informacion"); return }
        confirmar.diferencia = d
        confirmar.open()
    }
    onRejected: c.descartar()

    Component {
        id: paginaSeccion
        QQC2.ScrollView {
            id: pagina
            readonly property var seccion: parent && parent.modelData ? dialogo.c.secciones[parent.modelData.indice] : null
            contentWidth: availableWidth
            QQC2.ScrollBar.horizontal.policy: QQC2.ScrollBar.AlwaysOff
          ColumnLayout {
            width: pagina.availableWidth
            FormCard.FormHeader { title: pagina.seccion ? pagina.seccion.titulo : "" }
            FormCard.FormCard {
                FormCard.FormTextDelegate {
                    visible: !!(pagina.seccion && pagina.seccion.descripcion)
                    text: pagina.seccion ? pagina.seccion.descripcion : ""
                }
                Repeater {
                    model: pagina.seccion ? pagina.seccion.campos : []
                    delegate: Loader {
                        id: celda
                        required property var modelData
                        readonly property var campo: modelData
                        Layout.fillWidth: true
                        sourceComponent: campo.tipo === "interruptor" ? cInterruptor
                                       : campo.tipo === "opcion" ? cOpcion
                                       : campo.tipo === "texto_largo" ? cTextoLargo : cTexto
                    }
                }
            }
            FormCard.FormTextDelegate {
                visible: dialogo.c.esquema !== ""
                text: "Esquema: " + dialogo.c.esquema + " · clase " + dialogo.c.clase
                textItem.font: Kirigami.Theme.smallFont
                textItem.color: Kirigami.Theme.disabledTextColor
            }
          }
        }
    }
    Component {
        id: cInterruptor
        FormCard.FormSwitchDelegate {
            text: parent.campo.etiqueta
            description: parent.campo.ayuda
            checked: parent.campo.valor === true
            onToggled: dialogo.c.fijar(parent.campo.clave, checked)
        }
    }
    Component {
        id: cTexto
        FormCard.FormTextFieldDelegate {
            label: parent.campo.etiqueta
            text: parent.campo.valor === undefined || parent.campo.valor === null ? "" : String(parent.campo.valor)
            placeholderText: parent.campo.ayuda || (parent.campo.tipo === "archivo" ? "ruta relativa al documento" : "vacío: no se escribe")
            onTextEdited: dialogo.c.fijar(parent.campo.clave, text)
        }
    }
    Component {
        id: cTextoLargo
        FormCard.FormTextAreaDelegate {
            label: parent.campo.etiqueta
            text: parent.campo.valor === undefined || parent.campo.valor === null ? "" : String(parent.campo.valor)
            placeholderText: parent.campo.ayuda
            onTextChanged: if (activeFocus) dialogo.c.fijar(parent.campo.clave, text)
        }
    }
    Component {
        id: cOpcion
        FormCard.FormComboBoxDelegate {
            readonly property var valores: [""].concat(parent.campo.opciones.filter(o => o !== ""))
            text: parent.campo.etiqueta
            description: parent.campo.ayuda
            model: valores.map(v => v === "" ? "(sin valor: el de la clase)" : v)
            currentIndex: Math.max(0, valores.indexOf(String(parent.campo.valor || "")))
            onActivated: index => dialogo.c.fijar(parent.campo.clave, valores[index])
        }
    }

    Kirigami.Dialog {
        id: confirmar
        property string diferencia: ""
        title: "Aplicar la configuración"
        preferredWidth: Kirigami.Units.gridUnit * 44
        preferredHeight: Kirigami.Units.gridUnit * 26
        standardButtons: Kirigami.Dialog.Cancel
        customFooterActions: [
            Kirigami.Action {
                text: "Aplicar"; icon.name: "dialog-ok-apply"
                onTriggered: confirmar.ejecutar(false)
            },
            Kirigami.Action {
                text: "Aplicar y compilar"; icon.name: "run-build"
                onTriggered: confirmar.ejecutar(true)
            }
        ]
        function ejecutar(compilar) {
            const ruta = dialogo.c.principal
            const e = dialogo.c.aplicar()
            confirmar.close()
            if (e) { ventana.mensajes.mostrar(e, "error"); return }
            ventana.mensajes.mostrar("Configuración aplicada al documento.", "positivo")
            if (compilar) studio.compilacion.lanzar(ruta, "compilar")
        }
        ColumnLayout {
            spacing: Kirigami.Units.smallSpacing
            QQC2.Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "Se escribirán estos cambios en el preámbulo (líneas con − salen, con + entran). Nada más del documento se toca."
            }
            QQC2.ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredHeight: Kirigami.Units.gridUnit * 18
                QQC2.TextArea {
                    readOnly: true
                    text: confirmar.diferencia
                    font.family: Kirigami.Theme.fixedWidthFont.family
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    wrapMode: TextEdit.NoWrap
                    Accessible.name: "Diferencia"
                }
            }
        }
    }
}
