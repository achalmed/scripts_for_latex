---
tipo: guia_ia
estado: activo
---
# CLAUDE.md — latex-studio (repo `scripts_for_latex`)

LaTeX Studio: el entorno de escritura científica (`studio/`, QML + Kirigami sobre `gui-comun` 2.x, familia de los
studios) y el compilador del `.tex` suelto (`script_compilar_latex/`, alias `compilar`). Léase antes: `README.md`,
`estado.md` y, antes de tocar código, `docs/reingenieria.md` con `studio/README.md` (la ventana) o `docs/arquitectura.md`
(la CLI). Lo general rige desde el `CLAUDE.md` raíz.

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
- **Cada proyecto con su compilador** (`compilador.receta`, reingeniería R5): el `<marco>/scripts/build.sh` de su marco (decisión
  §1.2), latexmk si tiene `latexmkrc`, o `main.sh -k` con el motor que declare o LuaLaTeX + Biber; la ventana no elige
  otro motor ni ofrece pdfLaTeX o XeLaTeX a quien no los declare (regla 6; `tests/test_studio.py` lo vigila). Una opción
  nueva de `main.sh` entra primero en la CLI.
- **Nunca se escriben fuentes**: compilar no las toca y el editor escribe solo con Ctrl+S (`Editor.guardar`), sin pisar
  un cambio externo sin confirmación. Limpiar muestra la lista y confirma.
- **Las carpetas de trabajo salen de `core/env.py`** (`WRITING_DIR`, `DESPACHO_DIR`; el entorno manda) y las del
  usuario van a QSettings: ninguna ruta de la máquina ni nombre del despacho en el repo, las pruebas o las capturas.
  **Ninguna prueba ni sesión abre, lee ni compila documentos del despacho**: las pruebas usan `studio/ejemplo/proyectos/`.
- **Lo común de los studios es de `gui-comun`** (repo `~/Documents/gui-comun`, paquete `gui_comun` 2.x): la ventana de
  trabajo y sus paneles (módulo QML `GuiComun`: `VentanaStudio`, `TablaDatos`, `PanelDetalles`, `ListaDiagnosticos`,
  `VistaTexto`…), las acciones, las tareas, la consola, los modelos. Un arreglo ahí se hace en `gui-comun`.
- **Python no construye interfaz y QML no ejecuta procesos** (`gui-comun/docs/arquitectura-qml-kirigami.md` §4.2): los
  controladores (`studio/latex_app/controladores/`) exponen modelos, propiedades y `@Slot`; el QML (`studio/latex_app/qml/`)
  pinta y pide. Cada operación existe una sola vez, en `studio/latex_app/aplicacion.py` (`Acciones`). Cero colores propios
  en QML; ningún nombre ni logotipo dentro de la ventana.
- **Corre con el Python del sistema** (`/usr/bin/python3`: `main.py`, `install.sh`, el `.desktop`, `suite.yml`): su Qt
  es el que trae Kirigami. El PySide6 de Anaconda no sirve; nada de QtWidgets en el studio.
- **Las capturas y las pruebas compilan `studio/ejemplo/proyectos/` en una carpeta temporal** (`WRITING_DIR` y
  `DESPACHO_DIR` temporales; `capturar.py` además con `HOME` y `XDG_CACHE_HOME` temporales), nunca en el repo.

## Verificar

```bash
cd latex-studio/script_compilar_latex && for f in *.sh lib/*.sh tests/*.sh; do bash -n "$f"; done; cd -
latex-studio/script_compilar_latex/main.sh --help            # carga todos los módulos
latex-studio/script_compilar_latex/tests/dry-run.sh          # --dry-run, -c -n y --help no escriben
latex-studio/tests/run.sh                                  # servicios, controladores y ventana (sin pantalla, /usr/bin/python3); la muestra compilada en un temporal (fuera de ~/Documents: CORE_DIR)
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
  por la dependencia. La ventana vigila los archivos abiertos con `QFileSystemWatcher` (`Editor`), creado al abrir el
  primero y retirado con `deleteLater` (`Editor.soltar`): su notificador de inotify no sobrevive a que Python recoja
  el controlador.
- **Fuera de `~/Documents` (un worktree) la CLI no encuentra `core/`** subiendo carpetas: exporta `CORE_DIR`
  (`tests/conftest.py` lo toma de `gui_comun.rutas`). `capturar.py` fija además `PYTHONPATH` al `gui_comun` que lo lanzó:
  con `HOME` temporal no se ve el `pip install --user`, y subir carpetas desde un worktree encontraría otro.
- **Una `TabBar` vacía rompe el estilo de KDE** (`'height' of null`): la de los archivos vive en un `Loader`.
- **`<marco>/scripts/build.sh` de `escritura` no pasa `-synctex=1`** y deja los auxiliares en `<proyecto>/.build/`: sus proyectos compilan
  bien pero sin SyncTeX hasta que el marco lo añada.
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
| detección, estructura, diagnósticos, visor, recetas | `studio/latex_app/{proyectos,estructura,diagnostico,visor,compilador}.py` (sin Qt) |
| el alias `compilar` | `~/.dotfiles/shell/.zshrc` (ruta literal: no carga `core/`) |

<!-- Notas para mantenedores: longitud y forma según la normativa documental 3.11; AGENTS.md es un enlace a este archivo. -->
