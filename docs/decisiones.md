---
tipo: decision
estado: activo
titulo: "Decisiones de scripts_for_latex"
---
# Decisiones

Registro acumulativo y por tema de lo que se decidió en este repo y sigue vigente, con su fecha.
No es una bitácora: el relato de la reescritura modular está en `historial/`. Lo que falta por
decidir o hacer, en §Pendientes al final. Una entrada nueva va al final de su tema; una decisión
superada no se borra: se marca «superada por».

## Alcance

- **2026-06-22 — Una herramienta modular para el `.tex` suelto.** El script monolítico se dividió
  en `main.sh`, `config.sh` y un módulo por responsabilidad en `lib/` (v3.0.0); el `.tex` puede
  estar en cualquier ruta y se compila dentro de su carpeta.
- **2026-09-20 — Los frameworks compilan con su propio build.** `03 writing`, `11 Book`,
  `sgdp/marco_documental` y los `academic-*` de `10 Class` no pasan por aquí; un cambio en este
  repo no puede romperlos. El único consumidor por código es `compile_tex` de `10 Class` para los
  `.tex` que no son del framework (clave `compilador` de `10 Class/config/course.yml`).
- **2026-09-20 — No trae diseño.** Ni clases, ni plantillas, ni preámbulos: eso es de
  `sistema-editorial` y de cada framework.

## Motor

- **2026-09-20 — LuaLaTeX + Biber es el motor normativo** (regla 7 del `CLAUDE.md` raíz); ningún
  ejemplo ni valor nuevo se escribe para pdflatex o xelatex, que se conservan por compatibilidad
  con documentos antiguos.
- **2026-09-20 — `DEFAULT_ENGINE` sigue en `auto`, y `auto` cae en `pdflatex`.** Cambiarlo a
  `lualatex` alteraría lo que hoy recibe `10 Class`, que llama sin `-e`; queda como decisión del
  autor en §Pendientes y, mientras, el manual pide `-e lualatex` explícito.
- **2026-06-22 — Sin latexmk.** Pasadas fijas (`-p`), 3 en cuanto se pide bibliografía o
  glosario: el usuario ve y controla cada pasada.

## Relación con `core/`

- **2026-09-07 — El logger es el de `core/shell-lib/logger.sh`.** El `logger.sh` de la suite es
  un envoltorio que solo añade sus nombres cortos.
- **2026-09-15 — Manifiesto `suite.yml`** según `core/suite.schema.yml`; los bloques de los
  README los genera `core/suites.py`.

## Código

- **2026-06-22 — `set -euo pipefail` global**, con los códigos de salida capturados en línea
  aparte de `local` y `set +e` local en `compilar_segura()` (bitácora en
  `historial/bugs-corregidos.md`). Las dos correcciones resultaron incompletas: §Pendientes.
- **2026-10-03 — Nombres en español.** El manual anterior pedía «nombres en inglés técnico»; el
  código nunca lo siguió y el ecosistema escribe en español (NORMATIVA §9.7). Rige el español.

## Documentación

- **2026-10-03 — Un lector por documento.** El manual de `script_compilar_latex/` es para quien
  usa; `arquitectura.md`, para quien amplía; las afirmaciones sobre qué framework usa qué build se
  comprobaron en el código de cada repo y el README raíz las recoge en una tabla.

## Pendientes

Hallados al revisar el código el 2026-10-03, con un `.tex` mínimo fuera de los repos. Dueño: el
autor, o quien mantenga la suite por encargo suyo. Ninguno está corregido.

1. **El modo normal no detecta el error del motor.** En `ejecutar_latex()` (`compiler.sh`) la
   tubería `motor | tee | grep … || true` hace que `${PIPESTATUS[0]}` lea el estado de `true`
   (0): la pasada que falla sigue, y si queda un PDF anterior el script anuncia «¡Compilación
   completada!» y sale con 0. Reproducido con lualatex.
2. **Con `-s` y `-v` el error corta sin explicación.** `set -e` (y `pipefail` en `-v`) termina el
   proceso en la línea del motor, antes de `status=$?`: nunca se llega a `mostrar_errores_log`.
3. **El modo watch termina al primer fallo.** `compilar_segura()` desactiva `set -e`, pero
   `ejecutar_latex()` y `mostrar_info_pdf()` llaman a `exit 1`, que cierra el proceso entero. La
   corrección del Bug #1 de `historial/bugs-corregidos.md` no lo cubre.
4. **El watch no vigila subcarpetas**: `inotifywait` va sin `-r` (el manual anterior decía lo
   contrario).
5. **Colisión de `LOG_FILE`.** La suite usa ese nombre para el log del motor y
   `core/shell-lib/logger.sh` copia en `LOG_FILE` cada mensaje: los mensajes se mezclan con el log
   de LaTeX y, tras la limpieza, el `ok` final vuelve a crear `<nombre>.log` con una línea.
6. **La limpieza borra todos los `*.aux` del árbol** de la carpeta del `.tex`
   (`find . -name '*.aux' -delete`), también los de otros documentos.
7. **`--draft` no produce PDF**: aplica `-draftmode` a todas las pasadas; con lualatex deja un PDF
   de 0 bytes en lugar del anterior y el script lo anuncia como generado.
8. **La detección de `auto` es estrecha**: solo mira el `.tex` principal, no reconoce
   `\usepackage[…]{fontspec}` ni lo que cargue una clase, y nunca elige lualatex por `fontspec`.
9. **Textos de ayuda desfasados**: `mostrar_ayuda()` y `sugerir_tex_cercanos()` enseñan
   `compilar_latex.sh` (el nombre del monolito); `mostrar_ayuda()` recomienda xelatex en sus
   ejemplos; el banner sale también con `--help` y `--version`.
10. **Ruta de máquina en un comentario**: la cabecera de `resolver.sh` cita la ruta absoluta
    del home (regla 5 del `CLAUDE.md` raíz). La cabecera de `main.sh` aún enseña a instalar un
    alias de fish que `~/.dotfiles` no tiene.
11. **`suite.yml` dice que compila «para los frameworks de escritura, clases y libros»**, lo que
    no es cierto (§Alcance). Corregir el `resumen` obliga a regenerar los bloques
    (`core/suites.py generar --aplicar`, que escribe también `meta/INDICE_SCRIPTS.md`).
12. **Repo público sin `LICENSE`** (NORMATIVA §15.3): la licencia la decide el autor.
13. **¿`DEFAULT_ENGINE=lualatex`?** Alinearía la herramienta con la regla 7; antes hay que ver qué
    `.tex` de `10 Class` compila hoy con pdflatex por la detección.
