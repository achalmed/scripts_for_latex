---
tipo: guia_ia
estado: activo
---
# CLAUDE.md — latex-studio (repo `scripts_for_latex`)

LaTeX Studio: el entorno de escritura científica (`studio/`, QML + Kirigami sobre `gui-comun` 2.x, familia de los
studios) y el compilador del `.tex` suelto (`script_compilar_latex/`, alias `compilar`). Léase antes: `README.md`,
`estado.md` y, antes de tocar código, `docs/reingenieria.md` con `studio/README.md` (la ventana) o
`docs/arquitectura.md` (la CLI). Lo general rige desde el `CLAUDE.md` raíz.

## Reglas propias

- **`main.sh` orquesta; cada `lib/*.sh` tiene una responsabilidad**; `config.sh` concentra los valores por defecto. El
  logger es el de `core/` (`script_compilar_latex/lib/logger.sh` solo añade nombres cortos). **`auto` elige lualatex** salvo un `% !TEX program`
  en las 5 primeras líneas; pdflatex y xelatex quedan solo para material heredado que lo declare.
- **La interfaz que usa `docencia` es contrato** (`docs/arquitectura.md` §Consumidores): ruta de `main.sh`, `-s`,
  argumento sin extensión, códigos de salida y la elección de `auto`. Se mira allí antes de cambiarla.
- **Se prueba fuera de los repos** (compilar dentro de otro reescribe PDFs versionados): `--dry-run`, o las capturas y
  las pruebas compilan `studio/ejemplo/proyectos/` en un temporal (`WRITING_DIR`, `DESPACHO_DIR` y, en `capturar.py`,
  `HOME` y `XDG_CACHE_HOME` temporales).
- **Repo público**: nada del despacho ni rutas de máquina en código y ejemplos.
- **Cada proyecto con su compilador** (`compilador.receta`, reingeniería R5): el `<marco>/scripts/build.sh` de su marco
  (decisión §1.2), latexmk si tiene `latexmkrc`, o `main.sh -k` con el motor que declare o LuaLaTeX + Biber; la ventana
  no elige otro motor ni ofrece pdfLaTeX o XeLaTeX a quien no los declare (regla 6; `tests/test_studio.py` lo vigila).
  Una opción nueva de `main.sh` entra primero en la CLI.
- **Nunca se escriben fuentes**: compilar no las toca y el editor escribe solo con Ctrl+S (`Editor.guardar`), sin pisar
  un cambio externo sin confirmación. Limpiar muestra la lista y confirma. «Configurar el documento» (Ctrl+Alt+D,
  `studio/latex_app/configuracion.py`) toca solo el preámbulo y escribe tras mostrar la diferencia, sin pisar cambios
  sin guardar; citar, fichar y crear un documento nuevo los declara el marco y van tras confirmar (§1.18 a §1.20).
- **TeXstudio compila con la misma receta** (`studio/compilar.py`, sin Qt; decisiones §1.15). Su `texstudio.ini` lo toca
  solo `studio/latex_app/texstudio.py`: como texto (QSettings pierde sus tipos), las claves de `deseado()`, con TeXstudio
  cerrado, respaldo y deshacer; las pruebas, en un `.ini` temporal; ninguna sesión lo aplica sin el sí del autor.
- **Lo configurable de un documento lo declara su marco** en `latex-studio.yml` (contrato:
  `docs/configuracion-de-documentos.md`); la ventana no sabe nada de ningún marco ni añade campos propios de uno.
- **Las carpetas de trabajo salen de `core/env.py`** (`WRITING_DIR`, `DESPACHO_DIR`; el entorno manda) y las del usuario
  van a QSettings: ninguna ruta de la máquina ni nombre del despacho en el repo, las pruebas o las capturas. **Ninguna
  prueba ni sesión abre, lee ni compila documentos del despacho**: las pruebas usan `studio/ejemplo/proyectos/`.
- **Lo común de los studios es de `gui-comun`** (repo `~/Documents/gui-comun`, paquete `gui_comun` 2.x): la ventana de
  trabajo y sus paneles (módulo QML `GuiComun`: `VentanaStudio`, `TablaDatos`, `PanelDetalles`, `ListaDiagnosticos`,
  `VistaTexto`…), las acciones, las tareas, la consola, los modelos. Un arreglo ahí se hace en `gui-comun`.
- **Python no construye interfaz y QML no ejecuta procesos** (`gui-comun/docs/arquitectura-qml-kirigami.md` §4.2): los
  controladores (`studio/latex_app/controladores/`) exponen modelos, propiedades y `@Slot`; el QML
  (`studio/latex_app/qml/`) pinta y pide. Cada operación existe una sola vez, en `studio/latex_app/aplicacion.py`
  (`Acciones`). Cero colores propios en QML; ningún nombre ni logotipo dentro de la ventana.
- **Corre con el Python del sistema** (`/usr/bin/python3`: `main.py`, `install.sh`, el `.desktop`, `suite.yml`): su Qt
  es el que trae Kirigami. El PySide6 de Anaconda no sirve; nada de QtWidgets en el studio.

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

Un cambio en la detección de errores se prueba en los tres modos (normal, `-s`, `-v`), con y sin un PDF anterior.

## Trampas

- **El estado del motor se lee con `set +e` y `PIPESTATUS` justo después del pipeline** (`ejecutar_latex`): un `|| true`
  o un `set -e` activo lo pierden. Un fallo hace `return 1`, no `exit`, para que el watch sobreviva.
- **`LOG_FILE` es del logger de `core/`**: la salida de una corrida va a `SALIDA_LOG`.
- **`-o DIR` es relativo a la invocación**; se compila con `pushd "$TEX_DIR"` para que `\include` e `\input` resuelvan.
- **`--draft` no produce PDF**, la limpieza es `-c`/`--limpiar` (`--clean` no existe) y `bash -n` mira un archivo por vez.
- `inotifywait` no está instalado: el watch no arranca aquí (`-n -w` sale con 1). La ventana vigila con
  `QFileSystemWatcher` (`Editor`, y `Sincronizacion` el proyecto abierto y la carpeta de su PDF, que se reemplaza), retirado
  con `deleteLater` (`soltar`): su notificador de inotify no sobrevive a que Python recoja el controlador.
- **Fuera de `~/Documents` (un worktree) la CLI no encuentra `core/`** subiendo carpetas: exporta `CORE_DIR`
  (`tests/conftest.py` lo toma de `gui_comun.rutas`). `capturar.py` fija además `PYTHONPATH` al `gui_comun` que lo
  lanzó: con `HOME` temporal no se ve el `pip install --user`, y subir carpetas desde un worktree encontraría otro.
- **Una `TabBar` vacía rompe el estilo de KDE** (`'height' of null`): la de los archivos es `PestanasArchivos` de gui-comun (4.2), con su `Loader`.
- **SyncTeX de los marcos**: `escritura` deja auxiliares en `<proyecto>/.build/` y, desde el 2026-11-08, copia el
  `.synctex.gz` junto al PDF (TeXstudio y Okular lo buscan ahí); `docencia` pasa `-synctex=1` desde el mismo día.
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
| Okular como visor y la ventana única (`--ir`) | `studio/latex_app/okular.py` · `studio/latex_app/instancia.py` |
| compilar desde TeXstudio (puente y su configuración) | `studio/compilar.py` · `studio/latex_app/texstudio.py` · `studio/latex_app/qml/componentes/DialogoTexstudio.qml` |
| configuración de documentos (esquema, lectura, diferencia, escritura) | `studio/latex_app/configuracion.py` (sin Qt) · `docs/configuracion-de-documentos.md` |
| el alias `compilar` | `~/.dotfiles/shell/.zshrc` (ruta literal: no carga `core/`) |

<!-- Notas para mantenedores: longitud y forma según la normativa documental 3.11; AGENTS.md es un enlace a este archivo. -->
