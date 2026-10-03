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
| `--draft` | `-draftmode` en **todas** las pasadas (y `-no-pdf` con xelatex): comprueba que compila y no da PDF (con lualatex el anterior se pierde; el de 0 bytes se borra) | — |
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

`lib/detector.sh` lee las 5 primeras líneas del `.tex` principal:

| si encuentra | elige |
|---|---|
| `% !TEX program = pdflatex`, `xelatex` o `lualatex` (también `!TEX TS-program`) | ese motor |
| nada de eso | `lualatex`, el motor del ecosistema |

El comentario mágico es la vía del material heredado que necesita otro motor; es la misma
convención que usa `10 Class`.

## Qué borra la limpieza

Al terminar bien (y con `-c`), en la carpeta del `.tex`:

- `<nombre>.<ext>` para cada extensión de `EXTENSIONES_AUXILIARES` en `config.sh` (`aux`, `bbl`,
  `bcf`, `blg`, `log`, `toc`, `synctex.gz`, `run.xml`…; la lista completa la da `--help`), y
- los `.aux` de los `\include` que el `.aux` principal declara con `\@input{…}` (rutas relativas
  dentro de la carpeta). Ningún otro `.aux` de la carpeta se toca.

Si la compilación falla, los auxiliares se quedan, incluido el `.log` del motor, que es de donde
sale el extracto de errores. `--log FILE` guarda además una copia de la salida de la corrida.

## Problemas frecuentes

| síntoma | causa y salida |
|---|---|
| «No se encontró el archivo» | la ruta no llegó entera (espacio sin escapar, tilde entre comillas) o falta el `.tex`; mira la lista de cercanos que imprime |
| «Herramientas no instaladas: …» | falta un binario obligatorio para las opciones pedidas: instálalo o quita la opción |
| el PDF no recoge la bibliografía | falta `--biber` (o `-b`); con él las pasadas suben a 3 |
| «El PDF no se actualizó en esta compilación» | el motor no escribió el PDF aunque no dio error; lee `<nombre>.log` |
| salió con `pdflatex` o `xelatex` | el `.tex` lo pide con `% !TEX program = …`; quítalo o pasa `-e lualatex` |
| `-w` no arranca | falta `inotifywait` (paquete `inotify-tools`) o `fswatch` |
| no hay PDF tras `--draft` | es lo esperado: esa opción solo comprueba que compila |
| `-a` no abre nada | no hay visor de la lista; el PDF queda donde dice la salida |

## Límite honesto

- **Sin latexmk**: pasadas fijas; si hacen falta más, se piden con `-p`.
- **`auto` mira solo el comentario mágico**, no lo que el documento carga: un `.tex` heredado que
  exija pdflatex sin declararlo falla con lualatex y hay que añadirle la línea o pasar `-e`.
- **El modo watch** no vigila subcarpetas.
- **`--draft` no produce PDF**: con lualatex el PDF anterior se pierde.
- **No compila los frameworks** (`03 writing`, `10 Class` para `academic-*`, `11 Book`,
  `sgdp/marco_documental`): cada uno tiene su build.
- Sin pruebas automáticas: `bash -n` y un `.tex` mínimo.
