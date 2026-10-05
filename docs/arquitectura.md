---
tipo: doc
estado: activo
forma: referencia
titulo: "Arquitectura de compilar_latex: flujo, módulos, estado global, cómo se amplía y quién la usa"
---
# Arquitectura de compilar_latex

Para quien amplía o mantiene `script_compilar_latex/`, y para el repo que la invoca (§Consumidores).
El uso está en `../script_compilar_latex/README.md`; el porqué de cada elección y lo que falta, en
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
5. `detectar_y_anunciar_engine` (`detector.sh`): con `auto`, el `% !TEX program` de las 5 primeras
   líneas del `.tex` o, sin él, lualatex.
6. `verificar_dependencias` (`validator.sh`): binarios obligatorios según las opciones. Con `-n`
   (`--dry-run`), `plan_de_compilacion` (`compiler.sh`) imprime las órdenes y sale con 0 sin crear el
   temporal ni llamar al motor; con `-c -n`, `listar_auxiliares` dice qué borraría (paso 4).
7. `SALIDA_LOG`: el archivo de `--log` (`LATEX_LOG`) o un temporal que se borra al salir.
8. `modo_watch` (`watch.sh`), o `compilar` y, si devolvió 0, `limpiar_auxiliares` (si no, salida 1
   con los auxiliares en su sitio).

`compilar()`, en `main.sh`, vacía `SALIDA_LOG`, anota la hora de inicio, ejecuta la pasada 1, la
bibliografía y los índices (si hay al menos 2 pasadas) y las pasadas 2…N, y devuelve 1 en cuanto una
pasada falla. Después, en `--draft`, solo informa de que compila; si no, `mostrar_info_pdf` (que
rechaza un PDF anterior a la compilación o vacío), `mover_pdf` y `abrir_pdf` (`output.sh`).

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
| `script_compilar_latex/lib/compiler.sh` | invoca motor, bibliografía e índices dentro de `pushd "$TEX_DIR"`; extracto de errores; limpieza | `construir_flags`, `ejecutar_latex`, `ejecutar_bibliografia`, `ejecutar_indices`, `mostrar_errores_log`, `limpiar_auxiliares`; en simulación, `plan_de_compilacion` y `listar_auxiliares` |
| `script_compilar_latex/lib/output.sh` | banner y resultado | `banner`, `mostrar_info_pdf`, `mover_pdf`, `abrir_pdf`, `sugerir_apertura`, `elapsed` |
| `script_compilar_latex/lib/watch.sh` | vigilancia con `inotifywait` o `fswatch` | `modo_watch`, `compilar_segura`, `_watch_linux`, `_watch_macos` |

## Estado global

Los módulos se comunican por variables globales que declara `main.sh` con los valores de
`config.sh` y que `parsear_args` sobrescribe: `ARCHIVO`, `ENGINE`, `PASADAS`, `MODO_SILENCIOSO`,
`SOLO_LIMPIAR`, `MODO_WATCH`, `MODO_DRAFT`, `MODO_SIMULAR`, `DIRECTORIO_SALIDA`, `USAR_BIBTEX`, `USAR_BIBER`,
`USAR_MAKEINDEX`, `USAR_MAKEGLOSSARIES`, `ABRIR_PDF`, `VERBOSE`, `LATEX_LOG`, `SALIDA_LOG`,
`TIEMPO_INICIO`, `INICIO_COMPILACION`; las
rutas `TEX_PATH`, `TEX_DIR`, `TEX_BASE` (y sus alias `ARCHIVO_DIR`, `ARCHIVO_BASE`); y `PDF_FINAL`.
Cada función documenta en su cabecera qué globales lee y cuáles fija.

`LOG_FILE` no se usa: es el nombre que lee `core/shell-lib/logger.sh` para copiar cada mensaje a
un archivo, y cuando la suite lo usaba los mensajes del logger acababan en el log del motor.

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
- `set -euo pipefail` global. El estado de un pipeline se lee con `set +e` y `PIPESTATUS` en la
  línea siguiente, nunca detrás de `|| true` (que lo reescribe); un código de salida se captura en
  una línea aparte de `local` (`local x=$(…)` devuelve el de `local`).
- Una función que puede fallar en el ciclo de compilación devuelve 1 (`return`), no `exit`: el
  modo watch la llama con `set +e` y tiene que seguir vigilando.
- Rutas: ninguna de máquina en código; en comentarios, `~/Documents/…`.

## Cómo se verifica

```bash
cd scripts-latex/script_compilar_latex
for f in *.sh lib/*.sh; do bash -n "$f"; done      # bash -n comprueba un archivo por llamada
./main.sh --help
# un .tex mínimo fuera de los repos (nunca uno con PDF versionado):
d=$(mktemp -d)
printf '\\documentclass{article}\\begin{document}Hola\\end{document}\n' > "$d/a.tex"
./main.sh -e lualatex "$d/a" && ls "$d"
tests/dry-run.sh                                    # --dry-run, -c -n y --help no escriben; opción desconocida ≠ 0
```

Para un error, el mismo `.tex` con un comando inexistente, en los tres modos (normal, `-s`, `-v`) y
con y sin un PDF anterior en la carpeta.

## Consumidores

Lo que otros repos usan de esta herramienta, comprobado en su código. Cambiar la ruta de `main.sh`,
la bandera `-s`, la forma del argumento posicional, los códigos de salida o la elección de `auto` es
cambiar la interfaz de estos consumidores: se mira allí antes y se anota en `decisiones.md`.

| consumidor | cómo la invoca | de qué depende |
|---|---|---|
| `10 Class` · `compile_tex` (`10 Class/scripts/lib/common.sh`) | toma la ruta de la clave `compilador` de `10 Class/config/course.yml` (`$SCRIPTS_LATEX/script_compilar_latex/main.sh`; `common.sh` resuelve la variable con `core/env.sh`) y llama `"$compilador" -s "<carpeta absoluta>/<nombre sin .tex>"` para todo `.tex` que no sea `\documentclass{academic-*}` (esos van a `10 Class/scripts/build.sh`) | la ruta de `script_compilar_latex/main.sh`; `-s`; el argumento sin extensión; salida 0 si hay PDF nuevo y 1 si no, con el PDF anterior y los auxiliares en su sitio; sin `-e`, `auto` elige por `% !TEX program` o lualatex, la misma convención que `latex_engine()` de ese archivo. Si la ruta no es ejecutable, `compile_tex` compila con `latex_engine()` dos pasadas |
| `10 Class` · `10 Class/scripts/doctor.sh` | comprueba que la ruta de `compilador` es ejecutable | la ruta de `main.sh` |
| alias `compilar` (`~/.dotfiles/shell/.zshrc`) | apunta a `main.sh` | la ruta de `main.sh` |
| `core/env.sh`, `core/env.py` | exportan `SCRIPTS_LATEX` con la raíz del repo | el nombre de la carpeta; la lee `10 Class/scripts/lib/common.sh` |

Ningún otro framework pasa por aquí (`../README.md` §Qué es).
