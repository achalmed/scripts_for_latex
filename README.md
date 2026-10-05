---
tipo: readme
estado: activo
---
# scripts-latex/ — el compilador LaTeX del workspace para el .tex suelto, desde cualquier ruta

<!-- suites:inicio -->
Suites de esta carpeta (1); índice global en `meta/INDICE_SCRIPTS.md`. Patrón: M main · C config · L lib.

| Suite | Carpeta | Objetivo | Escribe en | Simula | Timer | Estado | Patrón |
|---|---|---|---|---|---|---|---|
| `compilar_latex` | [scripts-latex/script_compilar_latex](script_compilar_latex/) | latex | archivos | no |  | activo | `MCL` |

<sub>Bloque generado desde los `suite.yml` por `core/suites.py generar` (2026-10-05); no se edita a mano.</sub>
<!-- suites:fin -->

## Qué es

Una sola herramienta, `script_compilar_latex/` (alias `compilar`), que compila un `.tex` suelto
desde cualquier directorio: resuelve la ruta, elige el motor si no se le indica, encadena un número
fijo de pasadas con BibTeX o Biber, makeindex y makeglossaries, enseña el resultado, borra los
auxiliares y puede vigilar la carpeta para recompilar al guardar. No trae clases, plantillas ni
preámbulos: el diseño vive en `sistema-editorial` y en cada framework. Depende de `core/` (el
logger) y de una instalación TeX Live; su remoto en GitHub es público y se llama igual que la
carpeta.

El motor normativo del ecosistema es **LuaLaTeX + Biber** (regla 7 del `CLAUDE.md` raíz). Esta
herramienta lo aplica por defecto: `auto` elige **lualatex**, salvo que el `.tex` declare otro motor
con `% !TEX program = …` en sus 5 primeras líneas (material heredado). La bibliografía se pide con
`--biber`.

Quién compila qué en el ecosistema (comprobado en el código de cada repo):

| repo | qué compila | con qué | ¿pasa por aquí? |
|---|---|---|---|
| `03 writing` | documentos con esquema: tesis, monografías, informes, láminas | `03 writing/scripts/build.sh`: LuaLaTeX + Biber, módulos propios, sin latexmk | no |
| `10 Class` | los `\documentclass{academic-*}` del framework | `10 Class/scripts/build.sh` | no |
| `10 Class` | cualquier otro `.tex` de una sesión o un curso | `compile_tex` de `10 Class/scripts/lib/common.sh` llama a este `main.sh` (contrato en `docs/arquitectura.md` §Consumidores) | **sí** (único consumidor por código) |
| `11 Book` | libros de curso CampusTeX | `11 Book/scripts/build-course.sh`: latexmk si está instalado; si no, dos pasadas de lualatex | no |
| `sgdp/marco_documental` | documentos oficiales | `sgdp/marco_documental/Makefile` → `sgdp/marco_documental/scripts/build.sh`: de 2 a 4 pasadas de lualatex, hasta que `.aux` y `.toc` dejan de cambiar | no |
| **este repo** | el `.tex` que no pertenece a un framework: un post con LaTeX de los pubs, una nota, una prueba | `script_compilar_latex/main.sh`, pasadas explícitas, sin latexmk | — |

`core/env.sh` y `core/env.py` exportan su ruta como `SCRIPTS_LATEX`; el alias `compilar` está en
`~/.dotfiles/shell/.zshrc`.

## Uso

```bash
script_compilar_latex/main.sh --help                                  # todas las opciones
script_compilar_latex/main.sh -e lualatex --biber -p 3 documento      # el modo normativo
script_compilar_latex/main.sh -e lualatex documento.tex               # 2 pasadas, sin bibliografía
script_compilar_latex/main.sh -c documento                            # solo borra auxiliares
compilar -e lualatex --biber ~/Documents/03\ writing/<carpeta>/nota   # alias; espacio escapado
```

El manual (opciones, ejemplos por caso, problemas frecuentes) es `script_compilar_latex/README.md`.

## Estructura

| carpeta | qué es | dueño / generador |
|---|---|---|
| `script_compilar_latex/main.sh` | punto de entrada: carga módulos y encadena `parsear_args → resolver_ruta_tex → detectar_y_anunciar_engine → verificar_dependencias → compilar / modo_watch` | a mano |
| `script_compilar_latex/config.sh` | los valores por defecto: `DEFAULT_ENGINE`, `DEFAULT_PASADAS`, auxiliares que se borran, visores, colores | a mano |
| `script_compilar_latex/lib/` | un módulo por responsabilidad (resolver, detector, validator, cli, compiler, output, watch) y `logger.sh`, envoltorio de `core/shell-lib/logger.sh` | a mano |
| `script_compilar_latex/README.md` | el manual de uso | a mano; el bloque `suite:` lo genera `core/suites.py` |
| `script_compilar_latex/suite.yml` | manifiesto de la suite (`core/suite.schema.yml`) | a mano; de él salen los bloques generados |
| `docs/` | arquitectura, decisiones y pendientes, historial | a mano; el índice de `docs/README.md` lo genera `core/docs.py indice` |

## Documentación

| documento | para qué leerlo |
|---|---|
| `script_compilar_latex/README.md` | **quien usa**: opciones, ejemplos, problemas frecuentes |
| `docs/arquitectura.md` | **quien amplía o mantiene**: flujo, módulos, variables globales, cómo añadir una opción o un motor |
| `docs/arquitectura.md` §Consumidores | **otro repo**: qué usa `10 Class` de esta herramienta y qué no se puede cambiar sin mirarlo |
| `docs/decisiones.md` | por qué está hecho así y qué queda pendiente (errores conocidos sin corregir) |
| `docs/historial/` | la bitácora de la reescritura modular |
| `CLAUDE.md` | reglas para el asistente |
| `meta/INDICE_SCRIPTS.md` | la suite entre las del workspace (generado) |

## Límite honesto

- **No usa latexmk**: pasadas fijas (`-p`, 2 por defecto y 3 si se pide bibliografía o glosario).
- **El modo watch vigila solo la carpeta del `.tex`, sin subcarpetas**, y necesita `inotifywait`
  (Linux) o `fswatch` (macOS).
- **La tilde entre comillas no se expande**: `"~/Documents/…"` falla; se escribe
  `"$HOME/Documents/…"` o la tilde fuera de las comillas con el espacio escapado.
- **`--draft` no produce PDF**: comprueba que compila; con lualatex el PDF anterior se pierde.
- **`-o DIR` es relativo al directorio desde el que se invoca**, no al del `.tex`.
- **Sin pruebas automáticas**: se verifica con `bash -n` y compilando un `.tex` mínimo fuera de los
  repos.
- **Licencia MIT** (`LICENSE`), como el resto del código del ecosistema.
