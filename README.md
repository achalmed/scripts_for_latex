---
tipo: readme
estado: activo
---
# latex-studio/ — el compilador LaTeX del workspace para el .tex suelto, desde cualquier ruta (repo `scripts_for_latex`)

<!-- suites:inicio -->
Suites de esta carpeta (2); índice global en `meta/INDICE_SCRIPTS.md`. Patrón: M main · C config · L lib.

| Suite | Carpeta | Objetivo | Escribe en | Simula | Timer | Estado | Patrón |
|---|---|---|---|---|---|---|---|
| `compilar_latex` | [latex-studio/script_compilar_latex](script_compilar_latex/) | latex | archivos | no |  | activo | `MCL` |
| `latex_studio` | [latex-studio/studio](studio/) | latex | archivos | no |  | activo | `M··` |

<sub>Bloque generado desde los `suite.yml` por `core/suites.py generar` (2026-10-31); no se edita a mano.</sub>
<!-- suites:fin -->

## Qué es

**LaTeX Studio**: una ventana (`studio/`, de la familia de los studios del espacio de trabajo) sobre una herramienta,
`script_compilar_latex/` (alias `compilar`), que compila un `.tex` suelto desde
cualquier carpeta: resuelve la ruta, elige el motor (`auto` = LuaLaTeX salvo `% !TEX program`),
encadena pasadas fijas con Biber o BibTeX, makeindex y makeglossaries, informa del PDF y borra los
auxiliares. Es para el `.tex` que no pertenece a un framework: `escritura`, `11 Book`,
`sgdp/marco_documental` y los `academic-*` de `docencia` compilan con su propio build. No trae
clases ni plantillas (eso es `sistema-editorial`). Quién la llama por código y qué no se puede
cambiar sin avisar: `docs/arquitectura.md` §Consumidores.

## Uso

```bash
/usr/bin/python3 studio/main.py [documento.tex]                     # LaTeX Studio: la ventana (F5 compila, Ctrl+K paleta; el Python del sistema)
script_compilar_latex/main.sh --help                                # opciones (no compila)
script_compilar_latex/main.sh -e lualatex --biber documento         # el modo normativo: LuaLaTeX + Biber
script_compilar_latex/main.sh --dry-run -e lualatex --biber documento   # simula: dice qué haría, no escribe
script_compilar_latex/main.sh -c documento                          # solo borra los auxiliares
compilar -e lualatex --biber ~/Documents/escritura/<carpeta>/nota   # alias de ~/.dotfiles (zsh)
script_compilar_latex/tests/dry-run.sh                              # prueba de suite: --dry-run no escribe
```

En la ventana (QML + Kirigami sobre `gui-comun` 2.x, el espacio de trabajo de la familia de studios; `docs/rediseno.md`):
la tabla de los `.tex` de la carpeta de trabajo con su estado (compilado, con avisos, con errores, sin compilar), el
documento actual con sus opciones (LuaLaTeX + Biber; pdfLaTeX y XeLaTeX no se ofrecen), cada error y aviso del registro
con su línea (Intro abre el editor ahí), el registro íntegro, el PDF y los auxiliares; F5 compila, Mayús+F5 simula,
Ctrl+B compila con Biber, Limpiar auxiliares… muestra la lista y confirma; «recompilar al guardar» vigila el `.tex`; el
historial guarda cada compilación. Corre con `/usr/bin/python3` (el Qt del sistema, que trae Kirigami).

El manual (opciones, cómo se indica la ruta, qué borra la limpieza, problemas frecuentes) es
`script_compilar_latex/README.md`; el porqué de cada elección, `docs/decisiones.md`; lo pendiente,
`estado.md`.

## Estructura

| carpeta | qué es | dueño / generador |
|---|---|---|
| `script_compilar_latex/` | la suite: `main.sh`, `config.sh`, `lib/`, `tests/`, su manual y `suite.yml` | a mano; el bloque `suite:` del manual lo genera `core/suites.py` |
| `studio/` | LaTeX Studio: `main.py`, `latex_app/` (`compilador.py`: la orden, la lectura del registro y las consultas; `controladores/`, `modelos/`, `qml/`), `ejemplo/` (el documento de las capturas y las pruebas), `capturar.py` y su `suite.yml` (`studio/README.md`) | a mano |
| `tests/` | `tests/run.sh`: el servicio, los controladores y la ventana (sin pantalla, con `/usr/bin/python3`), compilando el ejemplo en una carpeta temporal | a mano |
| `docs/` | `arquitectura.md` (flujo, módulos, consumidores), `decisiones.md` y `rediseno.md` (el diseño de la ventana, con sus capturas) | a mano |

## Límite honesto

- **Sin latexmk**: pasadas fijas (`-p`, 2 por defecto y 3 con bibliografía o glosario).
- **El modo watch vigila solo la carpeta del `.tex`**, sin subcarpetas, y necesita `inotifywait`
  (Linux) o `fswatch` (macOS).
- **La tilde entre comillas no se expande**: `"$HOME/Documents/…"` o la tilde fuera de las comillas.
- **`--draft` no produce PDF**: con lualatex el PDF anterior se pierde.
