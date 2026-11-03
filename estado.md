---
tipo: estado
estado: activo
actualizado: 2026-11-03
---
# estado.md — latex-studio

## Hecho

| fecha | qué | dónde se ve |
|---|---|---|
| 2026-11-03 | **Visor**: con QtPdf se selecciona texto arrastrando (Ctrl+C, Ctrl+A, menú del clic derecho), se siguen los enlaces del PDF (internos a su página; externos solo http, https y mailto) y se busca (Ctrl+Alt+F, resultados resaltados, Intro y Mayús+Intro), sin perder la marca de SyncTeX ni el doble clic | `decisiones.md` §1.11; `tests/test_visor_qtpdf.py` |
| 2026-11-03 | **Editor y problemas**: el archivo ya no sale modificado al abrirlo (compara con el texto del disco); firma de las órdenes y autocompletado de argumentos (paquetes, clases, estilos, archivos del proyecto); los problemas de Biber se leen de su `.blg` (el `.bib` y la línea de un error de sintaxis; también con el compilador del marco, que calla a Biber); plegado, multicursor y corrector descartados con `TextArea` (recomendación en §1.12) | `decisiones.md` §1.12; `tests/test_proyectos.py`, `tests/test_compilador.py` |
| 2026-11-03 | **CLI**: P9 (`--help` y `--version` sin banner), P14 (`--log` relativo, una sola copia en el directorio de invocación), P15 (la ayuda de `--log` dice lo que hace; los ejemplos sin carpetas que ya no existen) y P17 (sugerir `.tex` cercanos no se corta y con ruta absoluta busca en su carpeta); `tests/dry-run.sh` 8 casos (los cuatro nuevos fallan con `main`) | `script_compilar_latex/tests/dry-run.sh` |
| 2026-11-03 | SyncTeX en los proyectos de `escritura` (su `CFG_TEX_FLAGS` con `-synctex=1`, en ese repo) y el aviso RQ-DOC-08 de `docs/rediseno.md`, que el validador ya no da | `escritura/scripts/config.sh` |
| 2026-11-03 | El visor PDF pinta con QtPdf (`PdfPageImage`) ahora que el autor instaló `qml6-module-qtquick-pdf`; `pdftoppm` queda de respaldo; papel blanco y página correcta en cada recuadro (una prueba vigila el fotograma); 77 pruebas | `decisiones.md` §1.10; `docs/figuras/latex-studio-oscuro.png` |
| 2026-11-02 | **Reingeniería: LaTeX Studio 3.0, entorno de escritura científica** (rama `wip/2026-11-02-reingenieria`, worktree `~/.cache/reingenieria/latex-studio`, sin fusionar ni empujar): proyectos detectados en las carpetas de trabajo (`WRITING_DIR`, `DESPACHO_DIR` y las del usuario; caché; categorías solo con información), cada uno compilado con su compilador y su motor (marco, latexmk, `main.sh -k`), en cola; editor con resaltado, estructura, autocompletado de `\ref`/`\cite`, buscar y reemplazar con regex; PDF integrado con `pdftoppm` y SyncTeX; errores con causa y acción; revisión de dependencias. CLI: `-k` y `CORE_DIR`. 73 pruebas | `docs/reingenieria.md`; `docs/figuras/`; `tests/run.sh` |
| 2026-11-02 | Fase 5 dada por buena (el autor delegó la decisión al director con las pruebas en verde y las capturas): `wip/2026-11-02-qml` fusionada en `main` y retirada; `docs/rediseno.md` a `hecho`; `gui-comun` 2.3.0 en `main` y en su remoto con `v2.3.0` | `git log` |
| 2026-11-02 | **LaTeX Studio en QML + Kirigami sobre `gui-comun` 2.3** (fase 5 de la modernización de la familia; rama `wip/2026-11-02-qml`, sin fusionar): `docs/rediseno.md` (auditoría, ocho preguntas, arquitectura de información, decisiones L1–L10, lo construido con capturas), `studio/` reescrito (tres vistas sobre un documento actual; la tabla de la carpeta con el estado leído del disco; F5 compila, Mayús+F5 simula, Ctrl+B con Biber, Limpiar muestra la lista y confirma; Problemas con «ir a la línea», Registro íntegro, Salidas; recompilar al guardar; solo LuaLaTeX en la ventana; `/usr/bin/python3`), 30 pruebas en `tests/run.sh` sobre `studio/ejemplo/` compilado en un temporal, tres capturas reales, el lanzador del menú reinstalado con `install.sh`. En `gui-comun`, 2.3.0 (`ListaDiagnosticos`; `Tareas.proceso(progreso_de=)`; rama `wip/2026-11-02-qml-latex`, etiqueta local) | `tests/run.sh`; `docs/figuras/latex-studio-*.png`; `/usr/bin/python3 studio/main.py` |
| 2026-10-31 | **LaTeX Studio**: la carpeta pasa a `latex-studio` (remoto `scripts_for_latex` intacto) y la herramienta gana ventana con el marco común de los studios: opciones, errores del `.log` con su línea, recompilar al guardar, historial | `docs/decisiones.md` §1.6; `python3 -m pytest -q tests` |
| 2026-10-05 | documentación según la normativa documental: `estado.md`, README de suite, `CLAUDE.md` corto, pendientes fuera de `decisiones.md`, `docs/historial/` e índice retirados | `docs/decisiones.md` §5.2 |
| 2026-10-05 | `--dry-run` (`-n`) y su prueba de suite | `script_compilar_latex/tests/dry-run.sh` |
| 2026-10-05 | renombre `scripts_for_latex` → `latex-studio` (piloto 1); el remoto no cambia | commit `b14f783`; `docs/decisiones.md` §1.5 |
| 2026-10-04 | licencia MIT; manifiesto y bloques generados al día | commits `d23aee3`, `31cc784` |
| 2026-10-03 | ciclo de compilación robusto: errores del motor, watch, limpieza, `--draft`, `auto` = lualatex | commit `606e4ee`; `docs/decisiones.md` §3 |

## En curso

nada en curso

## Por hacer

- 2026-11-02 · dueño: director · fusionar en `main` el último tramo de `wip/2026-11-02-reingenieria` (la base
  `gui-comun` 3.0: `escritorio` y diálogos de la base, confirmaciones de la base, «Guardar como»; capturas «antes» sin la
  carpeta de inicio). Valorar después pasar de `VentanaStudio` a `VentanaBase` (no cambia lo que se ve).
- 2026-11-02 · dueño: **el autor** · usar LaTeX Studio 3.0 en la sesión real (`/usr/bin/python3 ~/Documents/latex-studio/studio/main.py`
  tras la fusión): la página de proyectos sobre `escritura` y el despacho, abrir un proyecto, editar y guardar, F5,
  SyncTeX en un proyecto de `main.sh` o latexmk, F8, Ctrl+Mayús+D, la cola; lo que no convenza se anota aquí.
- 2026-11-03 · dueño: **el autor** · lo que sigue fuera de la 3.0 (`docs/reingenieria.md` §6, decisiones §1.12): plegado,
  multicursor y corrector no caben en un `TextArea` (recomendación: dejarlos fuera; «Abrir en el editor externo» los da);
  el modo watch de la CLI (`-w`) sigue sin ofrecerse (necesita `inotifywait`, que no está; la ventana compila al guardar
  si se marca); el registro de cada corrida de `main.sh` queda en la caché del studio (uno por proyecto, se reemplaza);
  la caché de páginas del visor se poda a 200 MB; la selección de texto del PDF es de una página a la vez. Ninguno es un
  defecto: son límites elegidos.
- 2026-11-03 · dueño: **el autor** · probar en la sesión real la selección, los enlaces y la búsqueda del PDF (Ctrl+Alt+F)
  y el autocompletado de argumentos; las pruebas los ejercitan con eventos de ratón sin pantalla.
Los números P4–P17 son los de la revisión del 2026-10-03 y 2026-10-04; se conservan porque el
manual los cita.

- 2026-10-04 · dueño: el autor · **P16** `VERSION` de `config.sh` no se mantiene (sigue en 3.0.0) y nadie la consume: mantenerla a mano o quitarla.
- 2026-10-03 · dueño: el autor · **P4** el watch no vigila subcarpetas (`inotifywait` sin `-r`).
- 2026-10-05 · dueño: el autor · **RQ-COD-09** `pdflatex` y `xelatex` siguen aceptados en `config.sh`, `lib/cli.sh`, `lib/detector.sh` y `lib/validator.sh` para material heredado (decisiones §2.1): retirarlos o declarar la excepción en la normativa.
- 2026-10-05 · dueño: el programa (normativa 2.1.0) · **RQ-COD-01** los módulos de `lib/` no llevan `set -euo pipefail`: se cargan con `source` y lo heredan de `main.sh` (decisiones §4.3); ponerlo en cada uno cambiaría la shell que los carga. La norma debe exceptuar los módulos cargados con `source`.
- 2026-10-05 · dueño: el programa · **RQ-IDN-03** la carpeta `script_compilar_latex/` no es kebab: renombrarla mueve la ruta que leen `docencia/config/course.yml` y el alias de `~/.dotfiles`; va con la ola 4.
- 2026-10-05 · dueño: core · **manual generado** el manual de `script_compilar_latex/README.md` repite `--help` a mano; la normativa (2.4) lo quiere generado y el generador no existe.
- 2026-10-05 · dueño: meta · **RQ-MAN-03** el doctor ve aristas sin declarar hacia `academic_class_framework` y `academic_writing_framework` en comentarios de `lib/detector.sh` y `lib/resolver.sh`: falsos positivos que la prueba debería ignorar en comentarios.

## Futuro

- Vigilancia recursiva en el modo watch, con exclusión de los auxiliares.
- Generar la tabla de opciones del manual desde `mostrar_ayuda()`.
