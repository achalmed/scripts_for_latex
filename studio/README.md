---
tipo: readme
estado: activo
---
# studio/ — LaTeX Studio, la ventana (QML + Kirigami sobre gui-comun 2.x) del compilador del .tex suelto de este repo
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

La ventana de `../script_compilar_latex` con el espacio de trabajo de la familia de studios (`gui-comun` 2.x; el diseño,
en [../docs/rediseno.md](../docs/rediseno.md)): menú, barra corta, navegación, centro, detalles, panel inferior, barra de
estado y paleta de órdenes (Ctrl+Alt+I · Ctrl+K). Tres vistas (Ctrl+1 · Ctrl+2 · Ctrl+3) y en todas la fila elegida es
el **documento actual**, sobre el que actúan **Compilar (F5)**, **Compilar con Biber (Ctrl+B)**, **Simular (Mayús+F5)**,
**Limpiar auxiliares… (Ctrl+Mayús+L)**, **Abrir el PDF** y **Abrir en el editor**:

| vista | centro | detalles (del documento actual) |
|---|---|---|
| Carpeta de trabajo (el campo de la barra; Ctrl+Mayús+O; Alt+↑ sube) | la tabla de los `.tex` de la carpeta: Estado leído del disco (compilado, con avisos, con errores, PDF anterior al .tex, sin compilar), Motor (el declarado con `% !TEX program` o LuaLaTeX), fecha del PDF, modificado | Resumen (documento, carpeta, motor, estado, el PDF con fecha, tamaño y páginas, la última compilación) · Opciones (motor `auto` o LuaLaTeX, pasadas, bibliografía, índice, glosarios, borrador, carpeta del PDF, abrir al terminar, recompilar al guardar; la orden que correría) · Problemas (cada error, aviso y aviso tipográfico con su archivo y su línea; Intro abre el editor ahí; filtros por nivel) · Registro (la salida íntegra de la última corrida) · Salidas (el PDF y los auxiliares, con tamaño y fecha) |
| Recientes | la misma tabla sobre los últimos documentos abiertos o compilados | los mismos |
| Compilaciones (historial) | cada compilación: cuándo, documento, resultado, duración, detalle; elegir una vuelve a ese documento; Supr la quita | los mismos |

La compilación es siempre `../script_compilar_latex/main.sh` (la orden de `latex_app/compilador.py`): su salida corre en el
panel inferior (F4), la barra de estado dice en qué pasada va y Esc cancela; el registro de cada corrida (`--log`) queda
en la caché del studio por documento, y de él salen Problemas, Registro y el estado. Limpiar muestra primero la lista
exacta de lo que `main.sh -c` borraría y pide confirmación. Un `.tex` se abre con Ctrl+O, por argumento o soltándolo en
la ventana: su carpeta pasa a ser la de trabajo. **La ventana no ofrece pdfLaTeX ni XeLaTeX** (regla 6 del workspace):
un `.tex` heredado que los declare con `% !TEX program` lo compila la CLI con ellos y la tabla lo dice en Motor.

## Estructura

| archivo | qué es |
|---|---|
| `main.py` | el punto de entrada, sin lógica (`/usr/bin/python3`) |
| `latex_app/aplicacion.py` | arma la aplicación: controladores, el registro de acciones (menú, barra, menú contextual, paleta, atajos: cada operación una sola vez) y `latex_app/qml/Main.qml` |
| `latex_app/controladores/` | lo que QML ve: `espacio` (vista, carpeta de trabajo, barra de estado, rutas), `opciones` (las de compilación, en QSettings), `documentos` (las tablas, el documento actual, problemas, registro, salidas, recompilar al guardar), `corrida` (compilar, simular y limpiar por `main.sh`), `historial`, `ajustes` |
| `latex_app/modelos/` | las filas de las tablas y de la lista de problemas, sin Qt (los modelos de Qt son los de `gui_comun.modelos`) |
| `latex_app/compilador.py` | el servicio, sin Qt: la orden de la CLI, la lectura del registro y las consultas (motor declarado, auxiliares, salidas, estado del documento, progreso) |
| `latex_app/qml/` | `Main.qml` sobre `GuiComun.VentanaStudio` y los componentes propios (`componentes/`) |
| `latex_app/recursos/marca.svg` | el icono del lanzador: la única marca del studio |
| `ejemplo/` | el documento de ejemplo (`articulo.tex`, `referencias.bib`, `con-error.tex`) de las capturas y las pruebas; se compila siempre en una carpeta temporal |
| `capturar.py` | las capturas de la documentación sobre el ejemplo compilado en un temporal |

## Uso

```bash
/usr/bin/python3 studio/main.py [documento.tex]       # desde latex-studio/, en la sesión real
QT_QPA_PLATFORM=offscreen /usr/bin/python3 studio/main.py --smoke     # construye la interfaz y sale
../install.sh                                         # acceso directo en el menú (con -n, simula)
/usr/bin/python3 studio/capturar.py docs/figuras/latex-studio-oscuro.png --esquema <LliphiOscuro.colors> --pestana 2
tests/run.sh                                          # desde latex-studio/: el ejemplo compilado en un temporal, cada QML y --smoke
```

## Límite honesto

- **El editor en la línea** usa Kate o KWrite (`--line`) o VS Code (`-g`), el que esté (Ajustes); sin ellos abre el `.tex` con la
  aplicación por omisión.
- **Recompilar al guardar** vigila solo el `.tex` principal, no los `\input` ni la bibliografía.
- **La tabla lista los `.tex` de la carpeta, sin subcarpetas**; un documento de otra carpeta se abre con Ctrl+O.
- **El estado se lee del disco**: con `--draft` no hay PDF y el documento figura «sin compilar» aunque compile.
