---
tipo: readme
estado: activo
---
# script_compilar_latex/ — compilar un .tex desde cualquier ruta: manual de uso (v3.0.0)

<!-- suite:inicio -->
**Suite `compilar_latex`** · objetivo *latex* · estado *activo* · bash · interfaz cli

Compilador universal de LaTeX (LuaLaTeX + Biber) para los frameworks de escritura, clases y libros; alias `compilar`.

- Escribe en: archivos · simula por defecto: no
- Depende de: lualatex, biber, core/shell-lib

Comandos:

```bash
main.sh documento.tex
main.sh --limpiar documento.tex
main.sh --help
```

<sub>Bloque generado desde `suite.yml` por `core/suites.py generar` (2026-09-20); no se edita a mano.</sub>
<!-- suite:fin -->

El manual de uso. Para quien lo amplía o lo mantiene: `../docs/arquitectura.md`; para saber qué
compila cada framework y qué no pasa por aquí: `../README.md`.

## Qué hace

Compila un `.tex` que puede estar en cualquier carpeta, sin moverlo ni hacer `cd`: resuelve la
ruta, entra en la carpeta del `.tex` para que `\input`, `\include`, imágenes y `.bib` se encuentren,
ejecuta las pasadas pedidas, intercala BibTeX o Biber y makeindex o makeglossaries tras la primera,
informa del PDF (tamaño, páginas, título y autor si hay `pdfinfo`) y borra los auxiliares.

El motor normativo del ecosistema es **LuaLaTeX + Biber**: se pide con `-e lualatex --biber`.

## Requisitos

| herramienta | para qué | obligatoria |
|---|---|---|
| `lualatex` (o `pdflatex`, `xelatex`) | el motor | sí, el que se use |
| `biber` / `bibtex` | `--biber` / `-b` | solo si se pide |
| `makeindex` / `makeglossaries` | `-i` / `-g` | solo si se pide |
| `pdfinfo` (poppler) | páginas y metadatos del PDF | no: sin él, avisa y sigue |
| `inotifywait` (inotify-tools) o `fswatch` (macOS) | `-w` | solo en modo watch |
| un visor (`evince`, `okular`, `zathura`, `atril`, `xpdf`, `mupdf`, `xdg-open`, `open`) | `-a`, el primero que encuentre | no |
| `core/shell-lib/logger.sh` | el logger; se busca subiendo desde `lib/` | sí |

`verificar_dependencias()` (en `lib/validator.sh`) comprueba los obligatorios antes de compilar y
dice qué falta.

## Alias

El alias `compilar` está en `~/.dotfiles/shell/.zshrc` y apunta a `main.sh`. Sin alias, se invoca
la ruta completa: `~/Documents/scripts_for_latex/script_compilar_latex/main.sh`.

## Cómo se indica el archivo

```bash
compilar                                                 # index.tex del directorio actual
compilar tesis                                           # tesis.tex del directorio actual
compilar ../otra-carpeta/nota                            # relativa al directorio actual
compilar ~/Documents/04\ index/_pubs/<pub>/<post>/index  # tilde sin comillas, espacio escapado
compilar "$HOME/Documents/03 writing/<carpeta>/nota"     # entre comillas: $HOME, no tilde
compilar nota.tex                                        # la extensión es opcional
```

La ruta es una sola palabra para la shell: un espacio sin escapar parte el argumento y el script se
queda con la última parte. Entre comillas la shell no expande `~`, y el script la toma por una
carpeta llamada `~`. Si no encuentra el archivo, lista hasta diez `.tex` cercanos.

## Opciones

| opción | qué hace | por defecto |
|---|---|---|
| `-e, --engine M` | `auto`, `lualatex`, `pdflatex` o `xelatex` | `auto` |
| `-p, --pasadas N` | número de pasadas del motor | 2; sube a 3 con `-b`, `--biber` o `-g` |
| `--draft` | `-draftmode` en **todas** las pasadas (y `-no-pdf` con xelatex): comprueba que compila, pero no da PDF; con lualatex deja un PDF de 0 bytes en lugar del anterior | — |
| `-b, --bibtex` | BibTeX tras la primera pasada | — |
| `--biber` | Biber tras la primera pasada (excluye `-b`) | — |
| `-i, --makeindex` | makeindex tras la primera pasada | — |
| `-g, --makeglossaries` | makeglossaries tras la primera pasada | — |
| `-o, --output DIR` | mueve el PDF a `DIR` (relativo al directorio desde el que se invoca) | junto al `.tex` |
| `-s, --silencioso` | la salida del motor solo va al log | — |
| `-v, --verbose` | toda la salida del motor | — |
| `-a, --abrir` | abre el PDF con el primer visor disponible | — |
| `--log FILE` | log en `FILE`, que la limpieza no borra | `<carpeta del .tex>/<nombre>.log` |
| `-c, --limpiar` | solo borra auxiliares y sale | — |
| `-w, --watch` | compila y vuelve a compilar al guardar un `.tex`, `.bib`, `.sty` o `.cls` | — |
| `-h, --help` · `--version` | ayuda · versión | — |

Sin `-s` ni `-v`, de la salida del motor solo se ven las líneas con `!`, `Warning`, `Error`,
`Overfull`, `Underfull`, `LaTeX Font`, `Package` o `Class`. `NO_COLOR=1` quita los colores.

### Cómo elige el motor `auto`

`lib/detector.sh` busca en el `.tex` principal (no en los que este incluye):

| si encuentra | elige |
|---|---|
| `\directlua`, `\luaexec` o `\luacode` | `lualatex` |
| `\usepackage{fontspec}`, `\usepackage{polyglossia}` o `\usepackage{unicode-math}`, sin opciones entre corchetes | `xelatex` |
| ninguna de las anteriores | `pdflatex` |

Por eso un documento del ecosistema se compila con `-e lualatex`: la detección nunca concluye
lualatex por `fontspec` y no ve `\usepackage[…]{fontspec}` ni lo que cargue una clase.

## Ejemplos

```bash
compilar -e lualatex --biber -p 3 documento              # el modo normativo
compilar -e lualatex -i -g documento                     # con índice y glosario (3 pasadas)
compilar -e lualatex --biber -o ../salida documento      # el PDF a ../salida/
compilar -s -e lualatex documento && echo OK             # para un script: sin ruido
compilar -v -e lualatex --log /tmp/depura.log documento  # todo, y el log a salvo
compilar -w -e lualatex documento                        # vigilar mientras se escribe
compilar -c documento                                    # solo limpiar
```

## Qué borra la limpieza

Al terminar bien (y con `-c`), en la carpeta del `.tex`:

- `<nombre>.<ext>` para cada extensión de `EXTENSIONES_AUXILIARES` en `config.sh` (`aux`, `bbl`,
  `bcf`, `blg`, `log`, `toc`, `synctex.gz`, `run.xml`…; la lista completa la da `--help`), y
- **todos los `*.aux` de esa carpeta y de sus subcarpetas**, sean o no del documento (para los
  `\include` en subcarpetas). Ojo con compilar un `.tex` en una carpeta que contiene otros
  proyectos.

Si la compilación falla, los auxiliares se quedan. El `.log` se borra salvo con `--log FILE`.

## Problemas frecuentes

| síntoma | causa y salida |
|---|---|
| «No se encontró el archivo» | la ruta no llegó entera (espacio sin escapar, tilde entre comillas) o falta el `.tex`; mira la lista de cercanos que imprime |
| «Herramientas no instaladas: …» | falta un binario obligatorio para las opciones pedidas: instálalo o quita la opción |
| el PDF no recoge la bibliografía | falta `--biber` (o `-b`); con él las pasadas suben a 3 |
| «¡Compilación completada!» pero el PDF no cambió | en el modo normal un error del motor no se detecta y vale el PDF anterior; repite con `-v` y lee el log (`../docs/decisiones.md` §Pendientes) |
| sale con 1 sin decir por qué | con `-s` o `-v` el error del motor corta en seco; el detalle está en `<nombre>.log` (o en `--log FILE`) |
| salió con `pdflatex` o `xelatex` | la detección automática; pasa `-e lualatex` |
| `-w` no arranca | falta `inotifywait` (paquete `inotify-tools`) o `fswatch` |
| `-w` se cierra tras un error | límite conocido: el modo watch termina al primer fallo |
| el PDF pesa 0 bytes | se compiló con `--draft`: esa opción no produce PDF; recompila sin ella |
| `-a` no abre nada | no hay visor de la lista; el PDF queda donde dice la salida |

## Límite honesto

- **Errores del motor**: en el modo normal no se detectan (vale un PDF anterior y la salida es 0);
  con `-s` o `-v` cortan sin extracto del log.
- **`auto` elige `pdflatex`** cuando el `.tex` no da pistas; el modo normativo es explícito.
- **Sin latexmk**: pasadas fijas; si hacen falta más, se piden con `-p`.
- **La limpieza borra todos los `*.aux` del árbol** de la carpeta del `.tex`.
- **El modo watch** termina al primer fallo y no vigila subcarpetas.
- **`--draft` no produce PDF** y con lualatex sustituye el anterior por uno vacío.
- **No compila los frameworks** (`03 writing`, `10 Class` para `academic-*`, `11 Book`,
  `sgdp/marco_documental`): cada uno tiene su build.
- Sin pruebas automáticas: `bash -n` y un `.tex` mínimo.
