---
tipo: readme
estado: activo
---
# scripts-latex/ — el compilador LaTeX del workspace para el .tex suelto, desde cualquier ruta (repo `scripts_for_latex`)

<!-- suites:inicio -->
Suites de esta carpeta (1); índice global en `meta/INDICE_SCRIPTS.md`. Patrón: M main · C config · L lib.

| Suite | Carpeta | Objetivo | Escribe en | Simula | Timer | Estado | Patrón |
|---|---|---|---|---|---|---|---|
| `compilar_latex` | [scripts-latex/script_compilar_latex](script_compilar_latex/) | latex | archivos | no |  | activo | `MCL` |

<sub>Bloque generado desde los `suite.yml` por `core/suites.py generar` (2026-10-05); no se edita a mano.</sub>
<!-- suites:fin -->

## Qué es

Una herramienta, `script_compilar_latex/` (alias `compilar`), que compila un `.tex` suelto desde
cualquier carpeta: resuelve la ruta, elige el motor (`auto` = LuaLaTeX salvo `% !TEX program`),
encadena pasadas fijas con Biber o BibTeX, makeindex y makeglossaries, informa del PDF y borra los
auxiliares. Es para el `.tex` que no pertenece a un framework: `03 writing`, `11 Book`,
`sgdp/marco_documental` y los `academic-*` de `10 Class` compilan con su propio build. No trae
clases ni plantillas (eso es `sistema-editorial`). Quién la llama por código y qué no se puede
cambiar sin avisar: `docs/arquitectura.md` §Consumidores.

## Uso

```bash
script_compilar_latex/main.sh --help                                # opciones (no compila)
script_compilar_latex/main.sh -e lualatex --biber documento         # el modo normativo: LuaLaTeX + Biber
script_compilar_latex/main.sh --dry-run -e lualatex --biber documento   # simula: dice qué haría, no escribe
script_compilar_latex/main.sh -c documento                          # solo borra los auxiliares
compilar -e lualatex --biber ~/Documents/03\ writing/<carpeta>/nota   # alias de ~/.dotfiles (zsh)
script_compilar_latex/tests/dry-run.sh                              # prueba de suite: --dry-run no escribe
```

El manual (opciones, cómo se indica la ruta, qué borra la limpieza, problemas frecuentes) es
`script_compilar_latex/README.md`; el porqué de cada elección, `docs/decisiones.md`; lo pendiente,
`estado.md`.

## Estructura

| carpeta | qué es | dueño / generador |
|---|---|---|
| `script_compilar_latex/` | la suite: `main.sh`, `config.sh`, `lib/`, `tests/`, su manual y `suite.yml` | a mano; el bloque `suite:` del manual lo genera `core/suites.py` |
| `docs/` | `arquitectura.md` (flujo, módulos, consumidores) y `decisiones.md` | a mano |

## Límite honesto

- **Sin latexmk**: pasadas fijas (`-p`, 2 por defecto y 3 con bibliografía o glosario).
- **El modo watch vigila solo la carpeta del `.tex`**, sin subcarpetas, y necesita `inotifywait`
  (Linux) o `fswatch` (macOS).
- **La tilde entre comillas no se expande**: `"$HOME/Documents/…"` o la tilde fuera de las comillas.
- **`--draft` no produce PDF**: con lualatex el PDF anterior se pierde.
