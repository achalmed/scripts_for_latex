---
tipo: readme
estado: activo
---
# studio/ — LaTeX Studio, GUI PySide6 del compilador del .tex suelto de este repo
<!-- suite:inicio -->
**Suite `latex_studio`** · objetivo *latex* · estado *activo* · python · interfaz gui

Aplicación de escritorio (PySide6) sobre el compilador del .tex suelto: opciones, errores con su línea, recompilar al guardar e historial.

- Escribe en: archivos · simula por defecto: no
- Depende de: PySide6, script_compilar_latex

Comandos:

```bash
main.py [archivo.tex]
main.py --smoke
```

<sub>Bloque generado desde `suite.yml` por `core/suites.py generar` (2026-10-31); no se edita a mano.</sub>
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

