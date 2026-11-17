---
tipo: readme
estado: activo
---
# studio/ — LaTeX Studio, el entorno de escritura científica (QML + Kirigami sobre gui-comun 2.x)
<!-- suite:inicio -->
**Suite `latex_studio`** · objetivo *latex* · estado *activo* · python · interfaz gui

Entorno de escritura científica (QML + Kirigami sobre gui-comun 3.0): detecta los proyectos LaTeX de las carpetas de trabajo (WRITING_DIR, DESPACHO_DIR, la raíz DOCS_ROOT y las que se añadan), los compila con su compilador y su motor (el del marco, latexmk o main.sh; LuaLaTeX + Biber sin declaración), en cola; editor con resaltado, estructura, autocompletado de \ref y \cite, buscar y reemplazar; PDF integrado con pdftoppm y SyncTeX; problemas con causa y acción.

- Escribe en: archivos · simula por defecto: no
- Depende de: /usr/bin/python3 con PySide6 del sistema (python3-pyside6.*) y Kirigami (qml6-module-org-kde-kirigami), gui-comun 3.0 (módulo QML GuiComun; QApplication para los diálogos de KDE), script_compilar_latex, poppler-utils (pdftoppm, pdfinfo) y synctex para el visor; latexmk para los proyectos con latexmkrc
- Nota: No compila por su cuenta: cada proyecto con su compilador (el scripts/build.sh de su marco, latexmk si tiene latexmkrc, o script_compilar_latex/main.sh -k); nunca escribe fuentes salvo Ctrl+S en el editor, «Configurar el documento» (Ctrl+Alt+D: solo el preámbulo, tras mostrar la diferencia; lo configurable lo declara el latex-studio.yml del marco) y lo que el marco declara y se confirma (citar un libro nuevo, guardar una ficha tras revisarla); la ayuda de la IA (Ctrl+Alt+I) solo copia el prompt y pone lo pegado en el editor; no ofrece pdfLaTeX ni XeLaTeX a un proyecto que no los declare (regla 6). Las carpetas de trabajo del usuario van a sus ajustes, nunca al repo.

Comandos:

```bash
main.py [documento.tex]
main.py --smoke
../install.sh
```

<sub>Bloque generado desde `suite.yml` por `core/suites.py generar` (2026-11-08); no se edita a mano.</sub>
<!-- suite:fin -->

## Qué es

El entorno donde el autor escribe, compila y revisa sus proyectos LaTeX (reingeniería del 2026-11-02; diagnóstico,
referencias y decisiones R1–R16 en [../docs/reingenieria.md](../docs/reingenieria.md)) y rediseñado el 2026-11-17 al estilo
de Datafw Studio (decisiones §1.17). Dos vistas sobre la misma ventana. **La barra de arriba** es ligera: en Proyectos,
«Tus documentos» con Abrir un .tex y Compilar los marcados; en Escritura, el documento, el estado de su última
compilación en una línea («Con avisos hace 2 min · 1 aviso») y tres acciones: **Compilar** (o Detener), **Configurar** y,
si su marco lo declara, el programa de sus datos. Lo demás sigue en los menús, en ⋮ y en la paleta (Ctrl+K).

| vista | izquierda | centro | derecha | abajo (F4) |
|---|---|---|---|---|
| **Proyectos** (Ctrl+1) | categorías (solo las que tienen proyectos) en árbol con su tipo y su grupo (tres niveles como mucho), recientes, carpetas de trabajo | los documentos como **tarjetas** con la miniatura de su primera página, su tipo, cuándo se compilaron y un punto con su estado (o, con «Lista», la tabla: estado, motor, última compilación, problemas, bibliografía, auxiliares, categoría); Ctrl+clic marca varios → cola | la ficha del proyecto: principal, clase, motor y de dónde sale, compilador, categoría y su motivo, archivos, configuración, la orden exacta | Problemas · Registro de LaTeX · Cola · Historial · Salida |
| **Escritura** (Ctrl+2) | Archivos (principal, `\input`, `.bib`, configuración) · Esquema (secciones, figuras, tablas, etiquetas) · Citas (claves de los `.bib` y, si el marco declara su biblioteca, toda la biblioteca con portada para citar y las fichas del proyecto para insertar con su página, crear y editar con su huella) · Datos (figuras con su miniatura, tablas y cifras que el marco declara: doble clic las inserta; «Actualizar» trae la versión nueva; abre su productor) | la **barra de insertar** (sección, figura, tabla celda por celda, cita de los `.bib`, ecuación, referencia a una `\label`, lista, negrita, énfasis, nota al pie: un formulario corto que muestra el LaTeX antes de escribirlo), la **franja del primer problema** con su arreglo, «Ir a la línea», «Siguiente» y «Ver todos», las palabras del archivo abierto y el editor: pestañas, resaltado LaTeX/BibTeX de KSyntaxHighlighting con el tema claro u oscuro, números de línea, buscar y reemplazar (con expresiones regulares), ir a línea, comentar, autocompletado | el PDF integrado (F7): páginas de `pdftoppm`, zoom, ajustar al ancho, miniaturas; Ctrl+clic en el editor → PDF, doble clic en el PDF → código (SyncTeX) | los mismos |

**Un proyecto** es un documento principal con `\documentclass` y lo que incluye (R1). Se detectan en las carpetas de
trabajo (por omisión `WRITING_DIR`, `DESPACHO_DIR` y la raíz `DOCS_ROOT` de `core/env.py` —con ella aparecen todos los proyectos:
docencia, documentos legislativos, CampusTeX, el CV…—, más las que se añadan con el diálogo de KDE;
profundidad configurable; caché por fecha y tamaño). **Cada proyecto se compila con su compilador y su motor** (R4, R5):
el `<marco>/scripts/build.sh` de su marco si la clase es de un marco (como `escritura`), latexmk si tiene `latexmkrc`, o
`../script_compilar_latex/main.sh -k` con el motor que declare (`% !TEX program`, arara) o LuaLaTeX + Biber. La
compilación nunca escribe fuentes; el editor escribe solo con Ctrl+S y avisa si el archivo cambió fuera. Los problemas
llevan causa probable, acción recomendada y el detalle del registro (R9); F8 recorre y salta a la línea.

**Configurar el documento** (Ctrl+Alt+D, el botón «Configurar» de la barra de arriba, Herramientas › «Configurar el
documento…» o «Configurar» en la ficha): lo que el marco del documento declara en su
`latex-studio.yml` —metadatos (curso, estudiante, código, fecha, título, autor, logo…), elementos visibles (nivel,
tiempo, puntaje, cajas, títulos de etapa, número y título de paso…) y opciones de la clase (tema, salida, modo…)—, una
sección por grupo. Aceptar muestra la diferencia del preámbulo; «Aplicar» o «Aplicar y compilar» escriben. Sin
esquema, todo documento ofrece título, autor, fecha y opciones de la clase. Contrato y marcos que lo publican:
[../docs/configuracion-de-documentos.md](../docs/configuracion-de-documentos.md).

**Junto a TeXstudio** (Ctrl+Mayús+E): abre el archivo en su línea, o el principal como maestro. La ventana vigila las
fuentes y el PDF del proyecto abierto (`latex_app/controladores/sincronizacion.py`): lo guardado en TeXstudio se recarga,
lo que compile se ve aquí con sus problemas y, si se pide (Ajustes › Compilación), la ventana compila sola. El
«Compilar» de TeXstudio corre `studio/compilar.py %.tex`, la misma receta que F5 (el marco, latexmk o LuaLaTeX + Biber;
`--version`, `--reconstruir`, `--limpiar`, `--simular`): lo deja así Herramientas › «Compilar desde TeXstudio con LaTeX
Studio…» (cuatro claves de su `.ini`, con TeXstudio cerrado, respaldo y deshacer; `latex_app/texstudio.py`).

**El PDF a la derecha del código; Okular, si se elige (2026-11-10).** Por omisión el PDF se ve en el visor integrado,
junto al editor (F7 lo oculta o lo muestra), recargado en cada compilación y con SyncTeX en los dos sentidos. Ajustes ›
«Ver el PDF en Okular, en una ventana aparte» lo pasa a Okular, que lo recarga solo al compilar; «Ver el PDF en Okular»
(barra, Ctrl+Alt+O) lo abre ahí una vez sin cambiar el ajuste. Okular no se puede incrustar (decisiones §1.15). La
ventana arranca en la página de proyectos, con el último abierto marcado (Intro lo abre). Con Okular, Ctrl+clic en el editor (o Ctrl+Alt+J) lleva al punto del PDF;
Ctrl+Alt+O lo trae al frente; Mayús+clic en Okular vuelve al código aquí una vez fijado su editor externo
(Herramientas › «Volver del PDF al código desde Okular…»: `main.py --ir %f %l`; `latex_app/okular.py`, `instancia.py`).

**Versiones de un mismo documento.** Si el marco produce varias salidas de un `.tex` (docencia: examen, claves,
solucionario o las tres), «Versión» bajo el proyecto abierto compila y muestra la elegida sin tocar el documento; la que
compila F5 por omisión, también en TeXstudio, se fija en «Configurar el documento» › Versión (`% !MODO = soluciones`;
contrato: `docs/configuracion-de-documentos.md` §7). Lo propio de LaTeX Studio: la configuración por esquema, la
categoría y el compilador de cada proyecto, los problemas explicados, la cola y el historial. La revisión ortográfica
del editor está apagada por omisión (Ajustes › Editor).

## Atajos

| atajo | qué hace | atajo | qué hace |
|---|---|---|---|
| F5 · Ctrl+B | compilar el proyecto abierto | Ctrl+S · Ctrl+Mayús+S · Ctrl+L | guardar · guardar como · guardar todo |
| F6 | reconstruir todo (limpia y compila) | Ctrl+F · Ctrl+R | buscar · buscar y reemplazar |
| Mayús+F5 | simular (la orden, sin escribir) | Ctrl+G | ir a la línea |
| Ctrl+Mayús+F5 | compilar los marcados (cola) | Ctrl+Espacio | completar (`\ref`, `\cite`, órdenes con su firma, entornos, paquetes, clases, archivos) |
| F8 | siguiente problema | Ctrl+T | comentar o descomentar |
| Ctrl+Alt+J · Ctrl+clic | del código al PDF (SyncTeX) | Ctrl+W | cerrar el archivo |
| doble clic en el PDF | del PDF al código | Ctrl+1 · Ctrl+2 | Proyectos · Escritura |
| Ctrl+Mayús+D | revisar dependencias | F7 · F4 · F9 | PDF · panel inferior · barra lateral |
| Ctrl+Mayús+L | limpiar auxiliares (muestra la lista) | Ctrl+O · Ctrl+Mayús+O | abrir un `.tex` · carpetas de trabajo |
| Ctrl+Mayús+P | abrir el PDF con su aplicación | Ctrl+K · Ctrl+Alt+I | paleta de órdenes |
| Ctrl+Alt+D | configurar el documento (metadatos, elementos visibles, opciones; botón «Configurar» de la barra); Ctrl+Alt+I, la ayuda de la IA de la parte abierta (si el marco la declara) | Ctrl+Mayús+E | abrir en TeXstudio (archivo y línea actuales; botón «TeXstudio» de la barra) |
| Ctrl+Alt+F | buscar en el PDF (Intro · Mayús+Intro: siguiente · anterior) | arrastrar en el PDF · Ctrl+C · Ctrl+A | seleccionar · copiar · toda la página (con QtPdf) |

La lista completa, generada de las acciones: Ayuda › Atajos de teclado.

## Estructura

| archivo | qué es |
|---|---|
| `main.py` | el punto de entrada, sin lógica (`/usr/bin/python3`) |
| `latex_app/aplicacion.py` | arma la aplicación: controladores, acciones (menú, barra de compilación, paleta, atajos: cada operación una sola vez, con su estado de `gui-comun` 3.0), `Sistema` (terminal, portapapeles, editor externo; abrir, mostrar en Dolphin y abrir carpeta son de `escritorio` de la base) y `latex_app/qml/Main.qml` |
| `latex_app/proyectos.py` | la detección (sin Qt): principal, inclusiones, `.bib`, motor, compilador, categoría, estado del disco; caché |
| `latex_app/estructura.py` | estructura, etiquetas, claves de los `.bib`, definiciones y autocompletado (sin Qt) |
| `latex_app/diagnostico.py` | errores presentables (causa y acción) y la revisión de dependencias con `kpsewhich` (sin Qt) |
| `latex_app/visor.py` | SyncTeX (sin Qt); las páginas son del visor de `gui-comun` 3.2 (`gui_comun.visor_pdf`) |
| `latex_app/configuracion.py` | la configuración de un documento (sin Qt): busca el `latex-studio.yml` de su marco, lee los valores del preámbulo, calcula la diferencia y la escribe al confirmar (`../docs/configuracion-de-documentos.md`) |
| `latex_app/compilador.py` | la orden de la CLI, la lectura del registro y `receta()`: los pasos de cada proyecto según su compilador (sin Qt) |
| `latex_app/controladores/` | lo que QML ve: `ajustes`, `proyectos`, `editor`, `compilacion`, `visor`, `historial` |
| `latex_app/qml/` | `Main.qml` sobre `GuiComun.VentanaStudio` y los componentes propios (`componentes/`: `PaginaProyectos`, `BarraLateral`, `EspacioEscritura`, `RegistroCompilacion`, `Cola`, `HistorialCompilaciones`, `DialogoAjustesStudio`, `DialogoConfigurarDocumento`); el editor, la barra de búsqueda y la lista de problemas son de `gui-comun` 3.1 (`EditorTexto`, `BarraBuscarReemplazar`, `ListaErrores`, `gui_comun.editor.ControladorEditor`) y el visor PDF, de la 3.2 (`VistaPdf`, `gui_comun.visor_pdf.VisorPdf`, del que hereda `studio/latex_app/controladores/visor.py` para SyncTeX) |
| `ejemplo/` | `proyectos/`: el árbol de muestra de las pruebas y las capturas (multiarchivo con Biber, BibTeX con comentario mágico, con error, con `latexmkrc`, un marco con compilador propio); los `.tex` sueltos de la ventana 2.0 |
| `capturar.py` | las capturas de la documentación sobre la muestra compilada, con `HOME` y caché temporales (`--lateral N` elige la pestaña de la izquierda; `--insertar <tipo>` abre el diálogo de insertar) |

## Uso

```bash
/usr/bin/python3 studio/main.py [documento.tex]       # desde latex-studio/, en la sesión real (un .tex abre su proyecto)
QT_QPA_PLATFORM=offscreen /usr/bin/python3 studio/main.py --smoke     # construye la interfaz y sale
../install.sh                                         # acceso directo en el menú (con -n, simula)
/usr/bin/python3 studio/capturar.py docs/figuras/latex-studio-oscuro.png --esquema <LliphiOscuro.colors> --vista escritura --archivo capitulos/metodo.tex --linea 4 --synctex
tests/run.sh                                          # desde latex-studio/: la muestra compilada en un temporal, cada QML y --smoke
```

## Límite honesto

- **Visor**: el de `gui-comun` 3.2 (`VistaPdf`): con `QtQuick.Pdf` instalado (`qml6-module-qtquick-pdf`) Qt pinta cada
  página, más nítida y sin caché en disco; sin él, o con `LATEX_STUDIO_VISOR=pdftoppm`, páginas de `pdftoppm`. Con QtPdf,
  selección de texto, enlaces y búsqueda (Ctrl+Alt+F). Lo de LaTeX es SyncTeX: la marca, el doble clic y «Ir al código
  de este punto» (§1.10, §1.11, §1.13).
- **SyncTeX necesita el `.synctex.gz`**: `main.sh -k`, latexmk y los compiladores de `docencia` y `escritura` lo dejan
  junto al PDF (escritura, desde el 2026-11-08; antes solo en su carpeta de auxiliares, donde la ventana ya lo buscaba).
- **El editor es un `TextArea`**: sin plegado, sin multicursor, sin corrector ortográfico; el autocompletado es por
  contexto (no conoce los argumentos de cada orden).
- **«Salir» con cambios sin guardar** pregunta (Ctrl+Q y cerrar la ventana); matar el proceso no.
