// ResaltadoEditor — el resaltado de KSyntaxHighlighting del editor (LaTeX, BibTeX…) con el tema claro u oscuro de
// KSyntaxHighlighting según la luminosidad del fondo de Kirigami (el de Lliphi). En archivo aparte: si el módulo
// `org.kde.syntaxhighlighting` faltara, el editor seguiría funcionando sin resaltado (lo carga un Loader).
import QtQuick
import org.kde.syntaxhighlighting

SyntaxHighlighter {
    property string nombreDefinicion: "LaTeX"
    property bool oscuro: false
    definition: Repository.definitionForName(nombreDefinicion)
    theme: Repository.defaultTheme(oscuro ? Repository.DarkTheme : Repository.LightTheme)
}
