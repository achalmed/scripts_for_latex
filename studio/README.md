---
tipo: readme
estado: activo
---
# studio/ — LaTeX Studio, GUI PySide6 del compilador del .tex suelto de este repo
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

La ventana de `../script_compilar_latex` con el marco común de los studios (`gui-comun` (paquete `gui_comun`), acento rosa):
Inicio (recientes), Compilar (opciones, compilar con F5, simular, limpiar; cada error y aviso del `.log` con su línea,
doble clic para abrir el editor en ella) e Historial. No compila por su cuenta: arma la orden de la CLI
(`latex_app/compilador.py`) y lee el `.log`.

## Uso

```bash
python3 studio/main.py [documento.tex]     # desde latex-studio/; Ctrl+O abre, F5 compila, Ctrl+K paleta, Ctrl+J consola
python3 -m pytest -q tests                 # la lectura del .log, una compilación real en un temporal, la prueba de humo
```

## Límite honesto

- **El editor en la línea** usa Kate (o VS Code); sin ellos abre el `.tex` con la aplicación por omisión.
- **Recompilar al guardar** vigila solo el `.tex` principal, no los `\input` ni la bibliografía.

