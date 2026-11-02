---
tipo: guia_ia
estado: activo
---
# CLAUDE.md — latex-studio (repo `scripts_for_latex`)

LaTeX Studio: la ventana (`studio/`, QML + Kirigami sobre `gui-comun` 2.x, familia de los studios) y el compilador del
`.tex` suelto (`script_compilar_latex/`, alias `compilar`); no compila los frameworks ni trae diseño. Léase antes:
`README.md`, `estado.md` y, antes de tocar código, `docs/arquitectura.md` (la CLI) y `docs/rediseno.md` con
`studio/README.md` (la ventana). Lo general rige desde el `CLAUDE.md` raíz.

## Reglas propias

- **`main.sh` orquesta; cada `lib/*.sh` tiene una responsabilidad**; `config.sh` concentra los
  valores por defecto y ningún módulo los redefine.
- **`auto` elige lualatex** salvo un `% !TEX program = …` en las 5 primeras líneas; pdflatex y
  xelatex quedan solo para material heredado que lo declare, y no se amplían.
- **El logger es el de `core/`**: `script_compilar_latex/lib/logger.sh` lo envuelve y solo añade
  nombres cortos.
- **La interfaz que usa `docencia` es contrato** (`docs/arquitectura.md` §Consumidores): ruta de
  `main.sh`, `-s`, argumento sin extensión, códigos de salida y la elección de `auto`. Se mira allí
  antes de cambiarla.
- **Se prueba fuera de los repos**: compilar dentro de otro repo reescribe PDFs versionados; un
  `.tex` mínimo en una carpeta temporal, o `--dry-run`.
- **Repo público**: nada del despacho ni rutas de máquina en código y ejemplos.
- **La ventana no compila por su cuenta**: arma la orden de `main.sh` (`studio/latex_app/compilador.py`) y lee el
  registro de la corrida (`--log`, uno por documento en la caché del studio); una opción nueva entra primero en la CLI.
  La ventana no ofrece pdfLaTeX ni XeLaTeX (regla 6): `tests/test_studio.py` lo vigila.
- **Lo común de los studios es de `gui-comun`** (repo `~/Documents/gui-comun`, paquete `gui_comun` 2.x): la ventana de
  trabajo y sus paneles (módulo QML `GuiComun`: `VentanaStudio`, `TablaDatos`, `PanelDetalles`, `ListaDiagnosticos`,
  `VistaTexto`…), las acciones, las tareas, la consola, los modelos. Un arreglo ahí se hace en `gui-comun`.
- **Python no construye interfaz y QML no ejecuta procesos** (`gui-comun/docs/arquitectura-qml-kirigami.md` §4.2): los
  controladores (`studio/latex_app/controladores/`) exponen modelos, propiedades y `@Slot`; el QML (`studio/latex_app/qml/`)
  pinta y pide. Cada operación existe una sola vez, en `studio/latex_app/aplicacion.py` (`Acciones`). Cero colores propios
  en QML; ningún nombre ni logotipo dentro de la ventana.
- **Corre con el Python del sistema** (`/usr/bin/python3`: `main.py`, `install.sh`, el `.desktop`, `suite.yml`): su Qt
  es el que trae Kirigami. El PySide6 de Anaconda no sirve; nada de QtWidgets en el studio.
- **Las capturas y las pruebas compilan `studio/ejemplo/` en una carpeta temporal**, nunca en el repo ni un documento
  del despacho.

## Verificar

```bash
cd latex-studio/script_compilar_latex && for f in *.sh lib/*.sh tests/*.sh; do bash -n "$f"; done; cd -
latex-studio/script_compilar_latex/main.sh --help            # carga todos los módulos
latex-studio/script_compilar_latex/tests/dry-run.sh          # --dry-run, -c -n y --help no escriben
latex-studio/tests/run.sh                                  # el servicio, los controladores y la ventana (sin pantalla, /usr/bin/python3); el ejemplo compilado en un temporal
QT_QPA_PLATFORM=offscreen /usr/bin/python3 latex-studio/studio/main.py --smoke
python3 core/archivos.py validar latex-studio --linea-base "$PWD/meta/programa/05-piloto/linea-base/validador.json"
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
  por la dependencia. «Recompilar al guardar» lo hace la ventana con `QFileSystemWatcher`, que se crea solo al
  vigilar: su notificador de inotify no sobrevive a que Python recoja un controlador (las pruebas lo descubrieron).
- **El registro de una corrida lleva todas las pasadas**: los problemas salen de la última pasada del motor y de las
  líneas `ERROR`/`WARN` de Biber (`compilador.problemas_de_registro`); el `.log` del motor es una sola pasada.

## Dónde está cada cosa

| pregunta | dónde |
|---|---|
| orquestación y estado global | `script_compilar_latex/main.sh` |
| valores por defecto, auxiliares, visores | `script_compilar_latex/config.sh` |
| opciones y ayuda | `script_compilar_latex/lib/cli.sh` |
| motor, pasadas, limpieza, simulación | `script_compilar_latex/lib/compiler.sh` |
| elección de `auto` | `script_compilar_latex/lib/detector.sh` |
| manifiesto de la suite | `script_compilar_latex/suite.yml` · `studio/suite.yml` |
| la ventana: acciones, controladores, QML | `studio/latex_app/aplicacion.py` · `studio/latex_app/controladores/` · `studio/latex_app/qml/` |
| el alias `compilar` | `~/.dotfiles/shell/.zshrc` (ruta literal: no carga `core/`) |

<!-- Notas para mantenedores: longitud y forma según la normativa documental 3.11; AGENTS.md es un enlace a este archivo. -->
