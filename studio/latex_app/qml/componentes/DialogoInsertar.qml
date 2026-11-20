// DialogoInsertar — la barra de insertar del editor (rediseño del 2026-11-17, decisiones §1.17): una sección, una figura,
// una tabla, una cita, una ecuación, una referencia o una lista, con un formulario corto en vez de la orden de memoria.
// Escribe el LaTeX en el cursor (lo ves antes de aceptar, abajo); nada más se toca. Las citas y las referencias son las
// del proyecto abierto (sus .bib y sus \label, por studio.proyectos.completar); la ruta de una imagen se escribe
// relativa al documento principal.
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import GuiComun

Kirigami.Dialog {
    showCloseButton: false            // ya hay botones al pie: sin la × roja del encabezado
    id: raiz

    property string tipo: "seccion"
    property var elegidas: []                                // claves (citas) o etiquetas (referencias) marcadas
    readonly property var p: studio.proyectos
    readonly property string carpeta: p.hayAbierto ? p.abierto.carpeta : ""
    readonly property var titulos: ({ seccion: "Insertar una sección", figura: "Insertar una figura", tabla: "Insertar una tabla",
                                      cita: "Citar", ecuacion: "Insertar una ecuación", referencia: "Insertar una referencia", lista: "Insertar una lista" })
    signal insertar(string texto)

    title: titulos[tipo] || "Insertar"
    preferredWidth: Kirigami.Units.gridUnit * 34
    padding: Kirigami.Units.largeSpacing * 2          // la rejilla y lo que se escribirá, con el mismo aire que el formulario
    standardButtons: Kirigami.Dialog.Cancel
    customFooterActions: [Kirigami.Action {
        text: "Insertar"; icon.name: "insert-text"
        enabled: raiz.codigo() !== ""
        onTriggered: { raiz.insertar(raiz.codigo()); raiz.close() }
    }]

    function abrir(t) {
        tipo = t
        elegidas = []
        titulo.text = ""; etiqueta.text = ""; ruta.text = ""; pie.text = ""; buscar.text = ""; ecuacion.text = ""; items.text = ""; pagina.text = ""
        celdas = []
        hacerCeldas()
        resultados = []
        open()
        Qt.callLater(() => { if (tipo === "cita" || tipo === "referencia") { buscar.forceActiveFocus(); filtrar() } else titulo.forceActiveFocus() })
    }
    function slug(t) {
        return (t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 32)
    }
    function etiquetaFinal(prefijo) { return etiqueta.text.trim() || (titulo.text.trim() ? prefijo + ":" + slug(titulo.text) : "") }
    function relativa(r) { return carpeta && r.startsWith(carpeta + "/") ? r.substring(carpeta.length + 1) : r }

    // --- la tabla: una rejilla de celdas
    property var celdas: []
    function hacerCeldas() {
        const n = []
        for (let f = 0; f < filas.value; f++) { n.push([]); for (let c = 0; c < columnas.value; c++) n[f].push(celdas[f] && celdas[f][c] !== undefined ? celdas[f][c] : "") }
        celdas = n
    }
    function fijarCelda(f, c, v) { const n = celdas.map(r => r.slice()); n[f][c] = v; celdas = n }

    // --- citas y referencias del proyecto
    property var resultados: []
    function filtrar() {
        const r = p.completar((tipo === "cita" ? "\\cite{" : "\\ref{") + buscar.text)
        resultados = r.elementos || []
    }

    function codigo() {
        const nl = "\n"
        switch (tipo) {
        case "seccion": {
            if (!titulo.text.trim()) return ""
            const orden = ["chapter", "section", "subsection", "subsubsection", "paragraph"][nivel.currentIndex]
            const e = etiquetaFinal(nivel.currentIndex === 0 ? "cap" : "sec")
            return "\\" + orden + "{" + titulo.text.trim() + "}" + (e ? nl + "\\label{" + e + "}" : "") + nl
        }
        case "figura": {
            if (!ruta.text.trim()) return ""
            const e = etiquetaFinal("fig")
            return "\\begin{figure}[" + posicion.currentValue + "]" + nl + "  \\centering" + nl
                 + "  \\includegraphics[width=" + (ancho.value / 100).toFixed(2) + "\\textwidth]{" + relativa(ruta.text.trim()) + "}" + nl
                 + (titulo.text.trim() ? "  \\caption{" + titulo.text.trim() + "}" + nl : "") + (e ? "  \\label{" + e + "}" + nl : "")
                 + (pie.text.trim() ? "  \\par\\small\\textit{Fuente:} " + pie.text.trim() + nl : "") + "\\end{figure}" + nl
        }
        case "tabla": {
            const e = etiquetaFinal("tab")
            const cols = "l" + "r".repeat(Math.max(0, columnas.value - 1))
            let cuerpo = ""
            celdas.forEach((fila, i) => {
                cuerpo += "    " + fila.map(x => x || " ").join(" & ") + " \\\\" + nl
                if (i === 0 && encabezado.checked) cuerpo += "    \\midrule" + nl
            })
            return "\\begin{table}[" + posicion.currentValue + "]" + nl + "  \\centering" + nl
                 + (titulo.text.trim() ? "  \\caption{" + titulo.text.trim() + "}" + nl : "") + (e ? "  \\label{" + e + "}" + nl : "")
                 + "  \\begin{tabular}{" + cols + "}" + nl + "    \\toprule" + nl + cuerpo + "    \\bottomrule" + nl + "  \\end{tabular}" + nl
                 + (pie.text.trim() ? "  \\par\\small\\textit{Fuente:} " + pie.text.trim() + nl : "") + "\\end{table}" + nl
        }
        case "cita": {
            if (elegidas.length === 0) return ""
            return "\\" + ordenCita.currentText + (pagina.text.trim() ? "[" + pagina.text.trim() + "]" : "") + "{" + elegidas.join(",") + "}"
        }
        case "ecuacion": {
            if (!ecuacion.text.trim()) return ""
            const e = numerada.checked ? etiquetaFinal("eq") : ""
            const entorno = numerada.checked ? "equation" : "equation*"
            return "\\begin{" + entorno + "}" + nl + "  " + ecuacion.text.trim().replace(/\n/g, nl + "  ") + nl + (e ? "  \\label{" + e + "}" + nl : "") + "\\end{" + entorno + "}" + nl
        }
        case "referencia":
            return elegidas.length ? "\\" + ordenRef.currentText + "{" + elegidas[0] + "}" : ""
        case "lista": {
            const filasLista = items.text.split("\n").map(x => x.trim()).filter(x => x)
            if (!filasLista.length) return ""
            const entorno = numerada2.checked ? "enumerate" : "itemize"
            return "\\begin{" + entorno + "}" + nl + filasLista.map(x => "  \\item " + x).join(nl) + nl + "\\end{" + entorno + "}" + nl
        }
        }
        return ""
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Kirigami.FormLayout {
            Layout.fillWidth: true
            QQC2.ComboBox {
                id: nivel
                visible: raiz.tipo === "seccion"
                Kirigami.FormData.label: "Nivel:"
                model: ["Capítulo", "Sección", "Subsección", "Subsubsección", "Párrafo"]
                currentIndex: 1
            }
            RowLayout {
                visible: raiz.tipo === "figura"
                Kirigami.FormData.label: "Imagen:"
                QQC2.TextField { id: ruta; Layout.fillWidth: true; placeholderText: "figures/mi-figura.pdf"; font.family: Kirigami.Theme.fixedWidthFont.family }
                QQC2.Button { text: "Elegir…"; icon.name: "document-open"; onClicked: elegirImagen.abrir(raiz.carpeta) }
            }
            QQC2.TextField {
                id: titulo
                visible: raiz.tipo === "seccion" || raiz.tipo === "figura" || raiz.tipo === "tabla" || (raiz.tipo === "ecuacion" && numerada.checked)
                Kirigami.FormData.label: raiz.tipo === "seccion" ? "Título:" : raiz.tipo === "ecuacion" ? "Nombre (para la etiqueta):" : "Título (\\caption):"
                Layout.fillWidth: true
            }
            QQC2.TextField {
                id: etiqueta
                visible: raiz.tipo !== "cita" && raiz.tipo !== "referencia" && raiz.tipo !== "lista" && (raiz.tipo !== "ecuacion" || numerada.checked)
                Kirigami.FormData.label: "Etiqueta:"
                Layout.fillWidth: true
                placeholderText: raiz.etiquetaFinal({ seccion: nivel.currentIndex === 0 ? "cap" : "sec", figura: "fig", tabla: "tab", ecuacion: "eq" }[raiz.tipo] || "") || "se arma del título"
                font.family: Kirigami.Theme.fixedWidthFont.family
            }
            RowLayout {
                visible: raiz.tipo === "figura"
                Kirigami.FormData.label: "Ancho:"
                QQC2.Slider { id: ancho; from: 30; to: 100; stepSize: 5; value: 80; Layout.fillWidth: true }
                QQC2.Label { text: ancho.value + " % del texto" }
            }
            RowLayout {
                visible: raiz.tipo === "tabla"
                Kirigami.FormData.label: "Tamaño:"
                QQC2.SpinBox { id: filas; from: 1; to: 30; value: 3; onValueModified: raiz.hacerCeldas() }
                QQC2.Label { text: "filas ×" }
                QQC2.SpinBox { id: columnas; from: 1; to: 10; value: 3; onValueModified: raiz.hacerCeldas() }
                QQC2.Label { text: "columnas" }
                QQC2.CheckBox { id: encabezado; text: "La primera es el encabezado"; checked: true }
            }
            QQC2.TextField {
                id: pie
                visible: raiz.tipo === "figura" || raiz.tipo === "tabla"
                Kirigami.FormData.label: "Fuente:"
                Layout.fillWidth: true
                placeholderText: "INEI (2025), ENAHO 2024 (opcional)"
            }
            QQC2.ComboBox {
                id: posicion
                visible: raiz.tipo === "figura" || raiz.tipo === "tabla"
                Kirigami.FormData.label: "Ubicación:"
                textRole: "t"; valueRole: "v"
                model: [{ t: "Donde quepa mejor (htbp)", v: "htbp" }, { t: "Aquí, si cabe (h)", v: "h" }, { t: "Arriba de la página (t)", v: "t" }, { t: "En su propia página (p)", v: "p" }]
            }
            RowLayout {
                visible: raiz.tipo === "cita"
                Kirigami.FormData.label: "Forma:"
                QQC2.ComboBox { id: ordenCita; model: ["parencite", "textcite", "cite", "citep", "citet", "autocite"] }
                QQC2.TextField { id: pagina; placeholderText: "página (p. 12)"; Layout.fillWidth: true }
            }
            QQC2.ComboBox {
                id: ordenRef
                visible: raiz.tipo === "referencia"
                Kirigami.FormData.label: "Forma:"
                model: ["ref", "autoref", "cref", "eqref", "pageref", "nameref"]
            }
            QQC2.Switch { id: numerada; visible: raiz.tipo === "ecuacion"; Kirigami.FormData.label: "Numerada:"; checked: true }
            QQC2.Switch { id: numerada2; visible: raiz.tipo === "lista"; Kirigami.FormData.label: "Numerada:"; checked: false }
        }

        // la rejilla de la tabla
        GridLayout {
            visible: raiz.tipo === "tabla"
            Layout.fillWidth: true
            columns: columnas.value
            rowSpacing: Kirigami.Units.smallSpacing
            columnSpacing: Kirigami.Units.smallSpacing
            Repeater {
                model: raiz.tipo === "tabla" ? filas.value * columnas.value : 0
                QQC2.TextField {
                    required property int index
                    readonly property int f: Math.floor(index / columnas.value)
                    readonly property int c: index % columnas.value
                    Layout.fillWidth: true
                    font.weight: f === 0 && encabezado.checked ? Font.Medium : Font.Normal
                    placeholderText: f === 0 && encabezado.checked ? "Columna " + (c + 1) : ""
                    text: raiz.celdas[f] ? raiz.celdas[f][c] || "" : ""
                    onTextEdited: raiz.fijarCelda(f, c, text)
                    Accessible.name: "Fila " + (f + 1) + ", columna " + (c + 1)
                }
            }
        }

        // la ecuación y la lista
        QQC2.TextArea {
            id: ecuacion
            visible: raiz.tipo === "ecuacion"
            Layout.fillWidth: true
            Layout.preferredHeight: Kirigami.Units.gridUnit * 4
            placeholderText: "y_i = \\beta_0 + \\beta_1 x_i + \\varepsilon_i"
            font.family: Kirigami.Theme.fixedWidthFont.family
        }
        QQC2.TextArea {
            id: items
            visible: raiz.tipo === "lista"
            Layout.fillWidth: true
            Layout.preferredHeight: Kirigami.Units.gridUnit * 6
            placeholderText: "Un elemento por línea"
        }

        // citas y referencias del proyecto
        ColumnLayout {
            visible: raiz.tipo === "cita" || raiz.tipo === "referencia"
            Layout.fillWidth: true
            Kirigami.SearchField {
                id: buscar
                Layout.fillWidth: true
                placeholderText: raiz.tipo === "cita" ? "Autor, año, título o clave" : "Etiqueta (fig:, tab:, sec:, eq:…)"
                onTextChanged: raiz.filtrar()
            }
            ListView {
                Layout.fillWidth: true
                Layout.preferredHeight: Kirigami.Units.gridUnit * 12
                clip: true
                model: raiz.resultados
                delegate: QQC2.CheckDelegate {
                    required property var modelData
                    width: ListView.view.width
                    checked: raiz.elegidas.includes(modelData.insertar)
                    onToggled: raiz.elegidas = raiz.tipo === "referencia" ? (checked ? [modelData.insertar] : [])
                                             : (checked ? raiz.elegidas.concat([modelData.insertar]) : raiz.elegidas.filter(x => x !== modelData.insertar))
                    contentItem: ColumnLayout {
                        spacing: 0
                        QQC2.Label { Layout.fillWidth: true; text: modelData.texto; font.family: Kirigami.Theme.fixedWidthFont.family; elide: Text.ElideRight }
                        QQC2.Label { Layout.fillWidth: true; text: modelData.detalle || ""; font: Kirigami.Theme.smallFont; color: Kirigami.Theme.disabledTextColor; elide: Text.ElideRight }
                    }
                }
                Kirigami.PlaceholderMessage {
                    anchors.centerIn: parent
                    width: parent.width - Kirigami.Units.gridUnit * 2
                    visible: parent.count === 0
                    text: raiz.tipo === "cita" ? "Sin entradas en los .bib del proyecto" : "Sin etiquetas en el proyecto"
                    explanation: raiz.tipo === "cita" ? "Añade un .bib con \\addbibresource." : "Una figura, tabla o sección con \\label aparece aquí."
                }
            }
        }

        // lo que se va a escribir, en un pozo tenue con letra de código (antes, texto gris suelto pegado al borde)
        QQC2.Label { text: "Se escribirá"; color: Kirigami.Theme.disabledTextColor; font: Kirigami.Theme.smallFont }
        Rectangle {
            readonly property bool oscuro: Kirigami.ColorUtils.brightnessForColor(Kirigami.Theme.backgroundColor) === Kirigami.ColorUtils.Dark
            Layout.fillWidth: true
            implicitHeight: codigoEscrito.implicitHeight + Kirigami.Units.largeSpacing * 2
            radius: Kirigami.Units.cornerRadius
            color: Kirigami.ColorUtils.linearInterpolation(Kirigami.Theme.backgroundColor, Kirigami.Theme.textColor, oscuro ? 0.07 : 0.04)
            border.width: 1
            border.color: Kirigami.ColorUtils.linearInterpolation(Kirigami.Theme.backgroundColor, Kirigami.Theme.textColor, oscuro ? 0.12 : 0.10)
            QQC2.Label {
                id: codigoEscrito
                anchors.fill: parent
                anchors.margins: Kirigami.Units.largeSpacing
                text: raiz.codigo() || "—"
                font.family: Kirigami.Theme.fixedWidthFont.family
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                wrapMode: Text.WrapAnywhere
                maximumLineCount: 12
                elide: Text.ElideRight
                color: Kirigami.ColorUtils.linearInterpolation(Kirigami.Theme.textColor, Kirigami.Theme.disabledTextColor, 0.35)
            }
        }
    }

    ElegirArchivos {
        id: elegirImagen
        titulo: "Elegir una imagen"
        filtros: ["Imágenes (*.pdf *.png *.jpg *.jpeg *.eps *.svg)"]
        onElegido: r => ruta.text = raiz.relativa(r)
    }
}
