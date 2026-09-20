---
tipo: readme
estado: activo
---
# scripts_for_latex/ — el compilador universal de LaTeX del workspace: cualquier .tex, desde cualquier ruta

<!-- suites:inicio -->
Suites de esta carpeta (1); índice global en `meta/INDICE_SCRIPTS.md`. Patrón: M main · C config · L lib.

| Suite | Carpeta | Objetivo | Escribe en | Simula | Timer | Estado | Patrón |
|---|---|---|---|---|---|---|---|
| `compilar_latex` | [scripts_for_latex/script_compilar_latex](script_compilar_latex/) | latex | archivos | no |  | activo | `MCL` |

<sub>Bloque generado desde los `suite.yml` por `core/suites.py generar` (2026-09-20); no se edita a mano.</sub>
<!-- suites:fin -->

## Qué es

Una sola herramienta, `script_compilar_latex/` (alias `compilar`), que compila un `.tex` suelto desde cualquier
directorio: resuelve la ruta (absoluta, relativa, con tilde, con o sin extensión), elige el motor si no se le indica,
encadena las pasadas con BibTeX o Biber, makeindex y makeglossaries, muestra los errores del log, limpia auxiliares y
puede vigilar la carpeta y recompilar al guardar. El motor normativo del ecosistema es **LuaLaTeX + Biber** (regla 7
del `CLAUDE.md` raíz); `pdflatex` y `xelatex` siguen aceptados por compatibilidad con documentos antiguos y no se
recomiendan para nada nuevo.

De qué **no** es dueña este repo, y quién sí:

| pieza | qué compila | con qué |
|---|---|---|
| `03 writing` | documentos con esquema: tesis, monografías, ensayos, artículos, informes | `03 writing/scripts/build.sh` (latexmk) |
| `11 Book` | libros de curso CampusTeX | `11 Book/scripts/build-course.sh` (latexmk) |
| `10 Class` | sesiones, exámenes y separatas de docencia | `10 Class/scripts/build.sh` (latexmk) |
| `sgdp/marco_documental` | documentos oficiales del despacho (clases LuaLaTeX propias) | `sgdp/marco_documental/Makefile` (latexmk) |
| `sistema-editorial` | nada: es la capa de diseño (documento = formato × tema × salida) que los frameworks consumen | — |
| **este repo** | cualquier `.tex` que no pertenezca a un framework: un post con LaTeX de los pubs, una nota, una prueba | `script_compilar_latex/main.sh`, pasadas explícitas, sin latexmk |

Los frameworks no lo invocan: cada uno tiene su build con sus flags. Este repo existe para lo que queda fuera y para
tener un solo comando en la terminal; no trae clases, plantillas ni preámbulos, porque el diseño vive en
`sistema-editorial` y en cada framework. Depende solo de `core/` (logger) y de una instalación TeX Live
(`meta/workspace.yml`; remoto público `scripts_for_latex`).

## Uso

```bash
script_compilar_latex/main.sh --help                                  # todas las opciones
script_compilar_latex/main.sh documento.tex                           # 2 pasadas; motor por detección (-e lualatex para forzarlo)
script_compilar_latex/main.sh -e lualatex --biber -p 3 documento      # LuaLaTeX + Biber, 3 pasadas: el modo normativo
script_compilar_latex/main.sh -w documento.tex                        # recompila al guardar (inotifywait)
script_compilar_latex/main.sh --limpiar documento.tex                 # solo borra auxiliares
compilar -e lualatex --biber ~/Documents/03\ writing/nota             # con el alias de ~/.dotfiles (shell/.zshrc)
```

## Estructura

| carpeta | qué es | dueño / generador |
|---|---|---|
| `script_compilar_latex/main.sh` | punto de entrada: carga módulos y encadena `parsear_args → resolver_ruta_tex → detectar_engine → verificar_dependencias → compilar / modo_watch` | a mano |
| `script_compilar_latex/config.sh` | todos los valores por defecto: `DEFAULT_ENGINE`, pasadas, auxiliares que se borran, visores, colores | a mano |
| `script_compilar_latex/lib/` | ocho módulos, uno por responsabilidad: `logger.sh` (envoltorio de `core/shell-lib/logger.sh`), `resolver.sh`, `detector.sh`, `validator.sh`, `cli.sh`, `compiler.sh`, `output.sh`, `watch.sh` | a mano |
| `script_compilar_latex/README.md` | el manual completo: opciones, ejemplos, arquitectura, solución de problemas | a mano; el bloque `suite:` lo genera `core/suites.py` |
| `script_compilar_latex/suite.yml` | manifiesto de la suite (`core/suite.schema.yml`); el bloque de arriba lo genera `core/suites.py generar --aplicar` | a mano |
| `docs/` | `historial/` con la bitácora de los errores corregidos en la reescritura modular | a mano; `docs/README.md` lo genera `core/docs.py indice` |

`script_compilar_latex/lib/logger.sh` es el envoltorio modelo de la relación suite ↔ `core/`: sube por el árbol hasta
hallar `core/shell-lib/logger.sh`, falla con un mensaje claro si no lo encuentra y solo debajo añade lo propio de la
suite (nombres cortos en español y los colores de `config.sh`).

## Documentación

| documento | para qué leerlo |
|---|---|
| `script_compilar_latex/README.md` | el manual: requisitos, alias, opciones, ejemplos por caso, arquitectura, solución de problemas |
| `CLAUDE.md` | reglas para el asistente: motor normativo, cómo verificar, trampas |
| `docs/README.md` | índice de `docs/` (generado) |
| `docs/historial/bugs-corregidos.md` | por qué el modo watch, el código de salida y la limpieza están escritos como están |
| `meta/INDICE_SCRIPTS.md` | la suite entre las del workspace (generado) |

## Límite honesto

- **No usa latexmk**: encadena un número fijo de pasadas (`-p`, 2 por defecto y 3 con bibliografía); si un documento
  necesita más, se pide. Los frameworks, que sí usan latexmk, no pasan por aquí.
- **`--engine auto` elige `pdflatex` cuando el `.tex` no da pistas** (`fontspec`, `polyglossia` o `unicode-math` →
  xelatex; `\directlua` o `luacode` → lualatex): para cumplir la regla 7 hay que pasar `-e lualatex` o escribir un
  preámbulo que lo delate. Cambiar ese valor por defecto es un cambio de código en `config.sh`, no de este README.
- **Compila lo que se le da**: no conoce esquemas, plantillas ni temas; un documento de `03 writing`, `10 Class` o
  `11 Book` se compila con el build de su framework.
- **`-o DIR` es relativo al directorio desde el que se invoca**, no al del `.tex`.
- **El modo watch necesita `inotifywait`** (Linux) o `fswatch` (macOS) y vigila toda la carpeta del `.tex`.
- **Sin pruebas automáticas**: se verifica con `bash -n` y compilando un `.tex` de prueba.
- El alias `compilar` no lo instala este repo: vive en `~/.dotfiles/shell/.zshrc`.
