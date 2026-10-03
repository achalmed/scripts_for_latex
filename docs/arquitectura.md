---
tipo: doc
estado: activo
titulo: "Arquitectura de compilar_latex: flujo, módulos, estado global y cómo se amplía"
---
# Arquitectura de compilar_latex

Para quien amplía o mantiene `script_compilar_latex/`. El uso está en
`../script_compilar_latex/README.md`; el porqué de cada elección y lo que falta, en
`decisiones.md`.

## Flujo

`main.sh` carga `config.sh`, inicializa colores y hace `source` de los módulos de `lib/`; después
`main()` encadena:

1. `banner` (también antes de `--help` y `--version`).
2. `parsear_args` (`cli.sh`): fija las variables globales; `--bibtex` y `--biber` se excluyen;
   con `-b`, `--biber` o `-g`, las pasadas suben a 3 si eran menos.
3. `resolver_ruta_tex` (`resolver.sh`) contra el directorio desde el que se invocó (`USER_CWD`,
   guardado antes de cualquier `cd`); si falla, `sugerir_tex_cercanos` y salida 1.
4. Con `-c`: `limpiar_auxiliares` y salida 0, sin mirar el motor.
5. `detectar_y_anunciar_engine` (`detector.sh`): con `auto`, decide por `grep` sobre el `.tex`
   principal.
6. `verificar_dependencias` (`validator.sh`): binarios obligatorios según las opciones.
7. `LOG_FILE` por defecto: `<TEX_DIR>/<TEX_BASE>.log`.
8. `modo_watch` (`watch.sh`) o `compilar` + `limpiar_auxiliares`.

`compilar()`, en `main.sh`, vacía el log, ejecuta la pasada 1, la bibliografía y los índices (si
hay al menos 2 pasadas), las pasadas 2…N, y luego `mostrar_info_pdf`, `mover_pdf` y `abrir_pdf`
(`output.sh`).

## Módulos

| archivo | responsabilidad | funciones |
|---|---|---|
| `main.sh` | orquesta; declara el estado global | `compilar`, `main` |
| `config.sh` | todos los valores por defecto y constantes | `_init_colores` |
| `script_compilar_latex/lib/logger.sh` | envoltorio de `core/shell-lib/logger.sh` con nombres cortos | `info`, `ok`, `warn`, `error`, `paso`, `titulo`, `separador`, `dim` |
| `script_compilar_latex/lib/resolver.sh` | de lo que escribió el usuario a `TEX_PATH`, `TEX_DIR`, `TEX_BASE` (con `realpath -m`) | `resolver_ruta_tex`, `sugerir_tex_cercanos` |
| `script_compilar_latex/lib/detector.sh` | el motor de `auto` | `detectar_engine`, `detectar_y_anunciar_engine` |
| `script_compilar_latex/lib/validator.sh` | argumentos y binarios | `validar_engine`, `validar_pasadas`, `verificar_dependencias` |
| `script_compilar_latex/lib/cli.sh` | argumentos y ayuda | `parsear_args`, `mostrar_ayuda` |
| `script_compilar_latex/lib/compiler.sh` | invoca motor, bibliografía e índices dentro de `pushd "$TEX_DIR"`; extracto de errores; limpieza | `construir_flags`, `ejecutar_latex`, `ejecutar_bibliografia`, `ejecutar_indices`, `mostrar_errores_log`, `limpiar_auxiliares` |
| `script_compilar_latex/lib/output.sh` | banner y resultado | `banner`, `mostrar_info_pdf`, `mover_pdf`, `abrir_pdf`, `sugerir_apertura`, `elapsed` |
| `script_compilar_latex/lib/watch.sh` | vigilancia con `inotifywait` o `fswatch` | `modo_watch`, `compilar_segura`, `_watch_linux`, `_watch_macos` |

## Estado global

Los módulos se comunican por variables globales que declara `main.sh` con los valores de
`config.sh` y que `parsear_args` sobrescribe: `ARCHIVO`, `ENGINE`, `PASADAS`, `MODO_SILENCIOSO`,
`SOLO_LIMPIAR`, `MODO_WATCH`, `MODO_DRAFT`, `DIRECTORIO_SALIDA`, `USAR_BIBTEX`, `USAR_BIBER`,
`USAR_MAKEINDEX`, `USAR_MAKEGLOSSARIES`, `ABRIR_PDF`, `VERBOSE`, `LOG_FILE`, `TIEMPO_INICIO`; las
rutas `TEX_PATH`, `TEX_DIR`, `TEX_BASE` (y sus alias `ARCHIVO_DIR`, `ARCHIVO_BASE`); y `PDF_FINAL`.
Cada función documenta en su cabecera qué globales lee y cuáles fija.

`LOG_FILE` es también el nombre que lee `core/shell-lib/logger.sh` para copiar cada mensaje a un
archivo: por eso los mensajes del logger acaban dentro del log del motor (`decisiones.md`
§Pendientes).

## La relación con `core/`

`logger.sh` es el envoltorio modelo: sube por el árbol hasta hallar
`core/shell-lib/logger.sh`, falla con un mensaje claro si no lo encuentra, fija
`LOG_FORMATO=corto` (icono y mensaje, sin hora) y solo debajo define los nombres cortos de la suite.
No se define otro logger. El manifiesto `suite.yml` sigue `core/suite.schema.yml`; los bloques
`suites:` y `suite:` de los README los escribe `core/suites.py generar --aplicar`.

## Cómo se amplía

**Una opción nueva:**

1. El caso en `parsear_args()` (`cli.sh`).
2. La variable global con su valor inicial en `main.sh`; si es configurable, el valor por defecto
   en `config.sh` y no en el módulo.
3. La lógica en el módulo de su responsabilidad.
4. La línea en `mostrar_ayuda()` y en la tabla de opciones del manual.

**Un motor nuevo:** el nombre en `validar_engine()` (`validator.sh`), la heurística en
`detectar_engine()` (`detector.sh`) y sus banderas, si las necesita, en `construir_flags()`
(`compiler.sh`). Antes, `decisiones.md`: el motor del ecosistema es uno.

**Una extensión auxiliar:** en `EXTENSIONES_AUXILIARES` (`config.sh`) y en la lista de
`mostrar_ayuda()`, que la repite a mano.

## Convenciones del código

- Funciones y variables en español, como el resto del ecosistema; cabecera de cada función con
  propósito, argumentos, globales leídas y fijadas, y retorno.
- Todo cambio de directorio con `pushd`/`popd` dentro de la función que lo necesita.
- `set -euo pipefail` global. Un código de salida se captura en una línea aparte de `local`
  (`local x=$(…)` devuelve el de `local`), y nunca detrás de `|| true`, que reescribe
  `PIPESTATUS` (`decisiones.md` §Pendientes).
- Rutas: ninguna de máquina en código (el comentario de cabecera de `resolver.sh` aún la
  tiene).

## Cómo se verifica

```bash
cd scripts_for_latex/script_compilar_latex
for f in *.sh lib/*.sh; do bash -n "$f"; done      # bash -n comprueba un archivo por llamada
./main.sh --help
# un .tex mínimo fuera de los repos (nunca uno con PDF versionado):
d=$(mktemp -d)
printf '\\documentclass{article}\\begin{document}Hola\\end{document}\n' > "$d/a.tex"
./main.sh -e lualatex "$d/a" && ls "$d"
```

Para un error, el mismo `.tex` con un comando inexistente, en los tres modos (normal, `-s`, `-v`) y
con y sin un PDF anterior en la carpeta.
