---
tipo: guia_ia
estado: activo
---
# CLAUDE.md — scripts-latex (repo `scripts_for_latex`)

El compilador del `.tex` suelto (`script_compilar_latex/`, alias `compilar`); no compila los
frameworks ni trae diseño. Léase antes: `README.md`, `estado.md` y, antes de tocar código,
`docs/arquitectura.md`. Lo general rige desde el `CLAUDE.md` raíz.

## Reglas propias

- **`main.sh` orquesta; cada `lib/*.sh` tiene una responsabilidad**; `config.sh` concentra los
  valores por defecto y ningún módulo los redefine.
- **`auto` elige lualatex** salvo un `% !TEX program = …` en las 5 primeras líneas; pdflatex y
  xelatex quedan solo para material heredado que lo declare, y no se amplían.
- **El logger es el de `core/`**: `script_compilar_latex/lib/logger.sh` lo envuelve y solo añade
  nombres cortos.
- **La interfaz que usa `10 Class` es contrato** (`docs/arquitectura.md` §Consumidores): ruta de
  `main.sh`, `-s`, argumento sin extensión, códigos de salida y la elección de `auto`. Se mira allí
  antes de cambiarla.
- **Se prueba fuera de los repos**: compilar dentro de otro repo reescribe PDFs versionados; un
  `.tex` mínimo en una carpeta temporal, o `--dry-run`.
- **Repo público**: nada del despacho ni rutas de máquina en código y ejemplos.

## Verificar

```bash
cd scripts-latex/script_compilar_latex && for f in *.sh lib/*.sh tests/*.sh; do bash -n "$f"; done; cd -
scripts-latex/script_compilar_latex/main.sh --help            # carga todos los módulos
scripts-latex/script_compilar_latex/tests/dry-run.sh          # --dry-run, -c -n y --help no escriben
python3 core/suites.py validar && python3 core/suites.py generar   # suite.yml y bloques (simula)
```

Un cambio en la detección de errores se prueba en los tres modos (normal, `-s`, `-v`), con y sin
un PDF anterior en la carpeta.

## Trampas

- **El estado del motor se lee con `set +e` y `PIPESTATUS` justo después del pipeline**
  (`ejecutar_latex`): un `|| true` o un `set -e` activo lo pierden. Un fallo hace `return 1`, no
  `exit`, para que el watch sobreviva.
- **`LOG_FILE` es del logger de `core/`**: la salida de una corrida va a `SALIDA_LOG`.
- **`-o DIR` es relativo al directorio de invocación**; se compila con `pushd "$TEX_DIR"` para
  que `\include` e `\input` resuelvan.
- **`--draft` no produce PDF** y la bandera de limpieza es `-c`/`--limpiar` (`--clean` no existe).
- **`bash -n` comprueba un archivo por invocación**: de ahí el bucle de arriba.
- `inotifywait` no está instalado en esta máquina: el watch no arranca aquí, y `-n -w` sale con 1
  por la dependencia.

## Dónde está cada cosa

| pregunta | dónde |
|---|---|
| orquestación y estado global | `script_compilar_latex/main.sh` |
| valores por defecto, auxiliares, visores | `script_compilar_latex/config.sh` |
| opciones y ayuda | `script_compilar_latex/lib/cli.sh` |
| motor, pasadas, limpieza, simulación | `script_compilar_latex/lib/compiler.sh` |
| elección de `auto` | `script_compilar_latex/lib/detector.sh` |
| manifiesto de la suite | `script_compilar_latex/suite.yml` |
| el alias `compilar` | `~/.dotfiles/shell/.zshrc` (ruta literal: no carga `core/`) |

<!-- Notas para mantenedores: longitud y forma según la normativa documental 3.11; AGENTS.md es un enlace a este archivo. -->
