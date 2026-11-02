---
tipo: readme
estado: activo
---
# studio/ — LaTeX Studio, el entorno de escritura científica (QML + Kirigami sobre gui-comun 2.x)
<!-- suite:inicio -->
**Suite `latex_studio`** · objetivo *latex* · estado *activo* · python · interfaz gui

Ventana del compilador del .tex suelto (QML + Kirigami sobre gui-comun 2.x): los documentos de una carpeta con su estado, LuaLaTeX + Biber por main.sh (F5 compila, Mayús+F5 simula, Ctrl+B con Biber), cada error y aviso con su línea, el registro íntegro, el PDF y los auxiliares, recompilar al guardar y el historial.

- Escribe en: archivos · simula por defecto: no
- Depende de: /usr/bin/python3 con PySide6 del sistema (python3-pyside6.*) y Kirigami (qml6-module-org-kde-kirigami), gui-comun 2.3 (módulo QML GuiComun), script_compilar_latex
- Nota: No compila por su cuenta: arma la orden de script_compilar_latex/main.sh y lee su registro; la ventana no ofrece pdfLaTeX ni XeLaTeX (regla 6).

Comandos:

```bash
main.py [documento.tex]
main.py --smoke
../install.sh
```

<sub>Bloque generado desde `suite.yml` por `core/suites.py generar` (2026-11-02); no se edita a mano.</sub>
<!-- suite:fin -->

## Qué es

El entorno donde el autor escribe, compila y revisa sus proyectos LaTeX (reingeniería del 2026-11-02; diagnóstico,
referencias y decisiones R1–R16 en [../docs/reingenieria.md](../docs/reingenieria.md)). Dos vistas sobre la misma
ventana; la barra de arriba es la de compilación.

| vista | izquierda | centro | derecha | abajo (F4) |
|---|---|---|---|---|
| **Proyectos** (Ctrl+1) | categorías (solo las que tienen proyectos), recientes, carpetas de trabajo | los proyectos detectados: estado, motor, última compilación, problemas, bibliografía, auxiliares, categoría; selección múltiple → cola | la ficha del proyecto: principal, clase, motor y de dónde sale, compilador, categoría y su motivo, archivos, configuración, la orden exacta | Problemas · Registro de LaTeX · Cola · Historial · Salida |
| **Escritura** (Ctrl+2) | Archivos (principal, `\input`, `.bib`, configuración) · Estructura (secciones, figuras, tablas, etiquetas) · Bibliografía (claves de los `.bib`) | el editor: pestañas, resaltado LaTeX/BibTeX de KSyntaxHighlighting con el tema claro u oscuro, números de línea, buscar y reemplazar (con expresiones regulares), ir a línea, comentar, autocompletado | el PDF integrado (F7): páginas de `pdftoppm`, zoom, ajustar al ancho, miniaturas; Ctrl+clic en el editor → PDF, doble clic en el PDF → código (SyncTeX) | los mismos |

**Un proyecto** es un documento principal con `\documentclass` y lo que incluye (R1). Se detectan en las carpetas de
trabajo (por omisión `WRITING_DIR` y `DESPACHO_DIR` de `core/env.py`, más las que se añadan con el diálogo de KDE;
profundidad configurable; caché por fecha y tamaño). **Cada proyecto se compila con su compilador y su motor** (R4, R5):
el `<marco>/scripts/build.sh` de su marco si la clase es de un marco (como `escritura`), latexmk si tiene `latexmkrc`, o
`../script_compilar_latex/main.sh -k` con el motor que declare (`% !TEX program`, arara) o LuaLaTeX + Biber. La
compilación nunca escribe fuentes; el editor escribe solo con Ctrl+S y avisa si el archivo cambió fuera. Los problemas
llevan causa probable, acción recomendada y el detalle del registro (R9); F8 recorre y salta a la línea.

## Atajos

| atajo | qué hace | atajo | qué hace |
|---|---|---|---|
| F5 · Ctrl+B | compilar el proyecto abierto | Ctrl+S · Ctrl+Mayús+S | guardar · guardar todo |
| F6 | reconstruir todo (limpia y compila) | Ctrl+F · Ctrl+R | buscar · buscar y reemplazar |
| Mayús+F5 | simular (la orden, sin escribir) | Ctrl+G | ir a la línea |
| Ctrl+Mayús+F5 | compilar los marcados (cola) | Ctrl+Espacio | completar (`\ref`, `\cite`, órdenes, entornos) |
| F8 | siguiente problema | Ctrl+T | comentar o descomentar |
| Ctrl+Alt+J · Ctrl+clic | del código al PDF (SyncTeX) | Ctrl+W | cerrar el archivo |
| doble clic en el PDF | del PDF al código | Ctrl+1 · Ctrl+2 | Proyectos · Escritura |
| Ctrl+Mayús+D | revisar dependencias | F7 · F4 · F9 | PDF · panel inferior · barra lateral |
| Ctrl+Mayús+L | limpiar auxiliares (muestra la lista) | Ctrl+O · Ctrl+Mayús+O | abrir un `.tex` · carpetas de trabajo |
| Ctrl+Mayús+P | abrir el PDF con su aplicación | Ctrl+K · Ctrl+Alt+I | paleta de órdenes |

La lista completa, generada de las acciones: Ayuda › Atajos de teclado.

## Estructura

| archivo | qué es |
|---|---|
| `main.py` | el punto de entrada, sin lógica (`/usr/bin/python3`) |
| `latex_app/aplicacion.py` | arma la aplicación: controladores, acciones (menú, barra de compilación, paleta, atajos: cada operación una sola vez), `Escritorio` y `latex_app/qml/Main.qml` |
| `latex_app/proyectos.py` | la detección (sin Qt): principal, inclusiones, `.bib`, motor, compilador, categoría, estado del disco; caché |
| `latex_app/estructura.py` | estructura, etiquetas, claves de los `.bib`, definiciones y autocompletado (sin Qt) |
| `latex_app/diagnostico.py` | errores presentables (causa y acción) y la revisión de dependencias con `kpsewhich` (sin Qt) |
| `latex_app/visor.py` | páginas con `pdftoppm` en una caché acotada y SyncTeX (sin Qt) |
| `latex_app/compilador.py` | la orden de la CLI, la lectura del registro y `receta()`: los pasos de cada proyecto según su compilador (sin Qt) |
| `latex_app/escritorio.py` | abrir con su aplicación, mostrar en Dolphin, abrir carpeta (lo sustituirá `gui-comun` 3.0) |
| `latex_app/controladores/` | lo que QML ve: `ajustes`, `proyectos`, `editor`, `compilacion`, `visor`, `historial` |
| `latex_app/qml/` | `Main.qml` sobre `GuiComun.VentanaStudio` y los componentes propios (`componentes/`: `PaginaProyectos`, `BarraLateral`, `EspacioEscritura`, `EditorArchivo`, `BarraBusqueda`, `VisorPdf`, `ListaProblemas`, `RegistroCompilacion`, `Cola`, `HistorialCompilaciones`, `DialogoAjustesStudio`, `ResaltadoEditor`) |
| `ejemplo/` | `proyectos/`: el árbol de muestra de las pruebas y las capturas (multiarchivo con Biber, BibTeX con comentario mágico, con error, con `latexmkrc`, un marco con compilador propio); los `.tex` sueltos de la ventana 2.0 |
| `capturar.py` | las capturas de la documentación sobre la muestra compilada, con `HOME` y caché temporales |

## Uso

```bash
/usr/bin/python3 studio/main.py [documento.tex]       # desde latex-studio/, en la sesión real (un .tex abre su proyecto)
QT_QPA_PLATFORM=offscreen /usr/bin/python3 studio/main.py --smoke     # construye la interfaz y sale
../install.sh                                         # acceso directo en el menú (con -n, simula)
/usr/bin/python3 studio/capturar.py docs/figuras/latex-studio-oscuro.png --esquema <LliphiOscuro.colors> --vista escritura --archivo capitulos/metodo.tex --linea 4 --synctex
tests/run.sh                                          # desde latex-studio/: la muestra compilada en un temporal, cada QML y --smoke
```

## Límite honesto

- **Visor sin QtPdf**: las páginas son imágenes de `pdftoppm` (sin selección de texto ni enlaces del PDF); con
  `sudo apt install qml6-module-qtquick-pdf python3-pyside6.qtpdf` se podría pasar a `PdfMultiPageView`.
- **SyncTeX necesita el `.synctex.gz`**: `main.sh -k` y latexmk lo dejan; el compilador de `escritura`
  (`<marco>/scripts/build.sh`) no pasa `-synctex=1` y sus proyectos no lo tienen hasta que ese marco lo añada.
- **El editor es un `TextArea`**: sin plegado, sin multicursor, sin corrector ortográfico; el autocompletado es por
  contexto (no conoce los argumentos de cada orden).
- **Los diálogos de archivos y carpetas** son los de KDE cuando la aplicación es una `QApplication` (`gui-comun` 3.0); con
  2.x se ve el diálogo de Qt Quick.
- **«Salir» con cambios sin guardar** pregunta (Ctrl+Q y cerrar la ventana); matar el proceso no.
