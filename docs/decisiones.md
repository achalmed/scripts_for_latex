---
tipo: decision
estado: activo
titulo: "Decisiones de latex-studio"
forma: explicacion
---
# Decisiones de latex-studio

Solo decisiones vigentes, con su porqué (normativa documental §3.3). Lo pendiente vive en
`../estado.md` §Por hacer; lo hecho, en el mensaje de commit. Una decisión superada conserva su
número con una línea «superada por».

## 1. Alcance

### §1.1 Una herramienta modular para el `.tex` suelto (2026-06-22)

El script monolítico se dividió en `main.sh`, `config.sh` y un módulo por responsabilidad en `lib/`
(v3.0.0). El `.tex` puede estar en cualquier ruta y se compila dentro de su carpeta. Motivo: una
sola puerta de entrada para lo que no pertenece a un framework (un post con LaTeX, una nota, una
prueba) sin copiar el script a cada carpeta.

### §1.2 Los frameworks compilan con su propio build (2026-09-20)

`escritura`, `11 Book`, `sgdp/marco_documental` y los `academic-*` de `docencia` no pasan por
aquí; un cambio en este repo no puede romperlos. El único consumidor por código es `compile_tex` de
`docencia` para los `.tex` que no son del framework (contrato en `arquitectura.md` §Consumidores).

### §1.3 No trae diseño (2026-09-20)

Ni clases, ni plantillas, ni preámbulos: eso es de `sistema-editorial` y de cada framework.

### §1.4 Sin latexmk (2026-06-22)

Pasadas fijas (`-p`), 3 en cuanto se pide bibliografía o glosario: quien compila ve y controla
cada pasada.

### §1.5 La carpeta se llama `scripts-latex`; el remoto sigue siendo `scripts_for_latex` (2026-10-05; superada por §1.6)

Renombre aprobado en la Puerta P3 (P3-1: carpeta = `id`, kebab) y aplicado como piloto 1 del
programa con `core/renombrar.py`; el manifiesto guarda `id_anterior: scripts_for_latex`. El remoto
de GitHub no cambia (plan de conversión, C7). Los consumidores leen la carpeta por `SCRIPTS_LATEX`
(`core/env.sh`), salvo el alias de `~/.dotfiles`, que no carga `core/`.

### §1.6 LaTeX Studio: la carpeta pasa a `latex-studio` y la herramienta gana ventana (2026-10-31)

Propuesta aprobada por el autor (`meta/programa/08-mantenimiento/familia-studios-2026-10-31.md`): el repo es un
proyecto independiente de la familia de los studios (Filesystem, Git, Quarto, Raphi). Renombre con
`core/renombrar.py` (etiqueta, respaldo y `UNDO.sh` en `$RESPALDOS_DIR/renombres/2026-10-31-scripts-latex-a-latex-studio/`);
el remoto sigue siendo `scripts_for_latex` y `SCRIPTS_LATEX` sigue siendo el nombre de la variable (contrato de
`core`): solo cambió su valor. La ventana (`studio/`, con el marco común `gui_comun` y acento rosa) no compila por su
cuenta: arma la orden de `script_compilar_latex` y lee el `.log` para mostrar cada error y aviso con su línea; la CLI
y su interfaz para `docencia` no cambian. «Recompilar al guardar» lo hace la ventana (con `QFileSystemWatcher`),
porque el `-w` de la CLI necesita `inotifywait`.

### §1.7 La ventana en QML + Kirigami sobre gui-comun 2.x (2026-11-02)

Fase 5 de la modernización de la familia de studios: la ventana de Widgets (tres páginas, tarjetas y cifras) se
reescribe como espacio de trabajo al estilo Dolphin/Kate sobre `gui-comun` 2.3 (`rediseno.md` §8, L1–L10): tres vistas
(Carpeta de trabajo, Recientes, Historial) sobre un documento actual; la tabla de los `.tex` de la carpeta con su estado
leído del disco; F5 compila, Mayús+F5 simula, Ctrl+B con Biber y Limpiar auxiliares… muestra la lista exacta y confirma
(R3); solo LuaLaTeX en la ventana (regla 6; pdfLaTeX y XeLaTeX quedan a la CLI para el material heredado que los
declare); el registro de cada corrida (`--log`) se guarda por documento en la caché y de él salen Problemas, Registro y
el estado; el studio corre con `/usr/bin/python3` y la CLI y su contrato con `docencia` no cambian. Lo que el marco
necesitó (`ListaDiagnosticos`; `Tareas.proceso(progreso_de=)`) subió a `gui-comun` 2.3.0.

### §1.8 Reingeniería: entorno de escritura científica sobre proyectos detectados (2026-11-02)

Encargo del autor del 2026-11-02 (la ventana debe reconocerse como un entorno de escritura científica, no como una
lista de archivos) y decisiones del director de la reingeniería. Diagnóstico, referencias (TeXstudio, TeXmaker, VS Code
con LaTeX Workshop, Overleaf) y las decisiones R1–R16 en `reingenieria.md`; lo esencial: un proyecto es un documento
principal con lo que incluye (R1), detectado en carpetas de trabajo configurables (por omisión `WRITING_DIR` y
`DESPACHO_DIR` de `core/env.py`; la lista del usuario va a sus ajustes, nunca al repo, R2); cada proyecto se compila
con su compilador (el `<marco>/scripts/build.sh` de su marco, latexmk si tiene `latexmkrc`, o `main.sh`) y con el motor que
declare o LuaLaTeX + Biber (R4, R5); editor integrado, PDF integrado con `pdftoppm` y SyncTeX (QtPdf no está
instalado, R10) y errores con causa y acción (R9). Supera §1.7 en la distribución; la ventana 2.0 queda en
`rediseno.md` y en `docs/figuras/antes/`. §1.2 sigue en pie: la ventana compila un proyecto de un marco **con el build
del marco**, nunca con `main.sh`. §1.4 vale para la CLI: la ventana usa latexmk solo para el proyecto que lo pide con
su `latexmkrc`.

### §1.9 La CLI gana `-k` (`--conservar`) y lee `CORE_DIR` (2026-11-02)

`-k` no borra los auxiliares al terminar bien: SyncTeX necesita el `.synctex.gz`, el autocompletado de `\ref` lee el
`.aux` y las pasadas siguientes van más rápido. Sin `-k` todo sigue igual (contrato con `docencia`). El logger busca
`core/` subiendo carpetas como siempre y, si no lo encuentra (un worktree fuera de `~/Documents`, una copia de
pruebas), usa `CORE_DIR` de `core/env.sh` si está exportada.

## 2. Motor

### §2.1 LuaLaTeX + Biber es el motor normativo (2026-09-20)

Regla 7 del `CLAUDE.md` raíz. Ningún ejemplo ni valor nuevo se escribe para pdflatex o xelatex, que
se conservan para material heredado que los declare.

### §2.2 `DEFAULT_ENGINE` en `auto`, y `auto` cae en `pdflatex` (2026-09-20)

Superada por §2.3 (2026-10-03).

### §2.3 `auto` es lualatex, salvo el comentario mágico (2026-10-03)

La heurística por paquetes contradecía la regla 7 y no veía `\usepackage[…]{fontspec}`. `auto` lee
`% !TEX program = …` en las 5 primeras líneas (la convención de `docencia/scripts/lib/common.sh`)
y, sin él, elige lualatex. El andamio de los decks de `docencia` ya declara `lualatex`.

## 3. Robustez del ciclo de compilación (2026-10-03)

### §3.1 El estado del motor se lee con `set +e` y `PIPESTATUS`

Justo después del pipeline, en los tres modos: un error sale con 1 y con el extracto del `.log` del
motor. Antes, `|| true` y `set -e` hacían que un fallo con un PDF anterior se anunciara como éxito.

### §3.2 Un fallo devuelve 1, no hace `exit`

`compilar` se detiene en la primera pasada que falla y el modo watch sigue vigilando;
`mostrar_info_pdf` rechaza un PDF anterior a la compilación o vacío.

### §3.3 La salida de la corrida va a `SALIDA_LOG`

El `--log` o un temporal; nunca `LOG_FILE`, que es del logger de `core/`, ni el `.log` del motor,
que este reescribe en cada pasada.

### §3.4 La limpieza borra solo los auxiliares del documento

Y los `.aux` que su `.aux` declara con `\@input`; ningún otro de la carpeta. `--draft` dice que no
hay PDF y borra el de 0 bytes que deja lualatex.

### §3.5 `--dry-run` simula sin escribir (2026-10-05)

`-n`/`--dry-run` imprime las órdenes que ejecutaría (o, con `-c`, los auxiliares que borraría) y
sale antes de crear el temporal, sin llamar al motor. Es el `--dry-run` real que exige RQ-COD-02;
`simula_por_defecto` sigue en `false` porque compilar es lo que se le pide a la herramienta. Lo
prueba `script_compilar_latex/tests/dry-run.sh`.

## 4. Código y relación con `core/`

### §4.1 El logger es el de `core/shell-lib/logger.sh` (2026-09-07)

El `logger.sh` de la suite es un envoltorio que solo añade sus nombres cortos.

### §4.2 Manifiesto `suite.yml` (2026-09-15)

Según `core/suite.schema.yml`; los bloques de los README los genera `core/suites.py`.

### §4.3 `set -euo pipefail` en `main.sh` (2026-06-22)

Con los códigos de salida capturados en línea aparte de `local` y `set +e` local donde hace falta
leer un estado (§3.1). Los módulos de `lib/` se cargan con `source` y heredan la opción. La bitácora
de la reescritura modular quedó en git: `git show 2a833c3:docs/historial/bugs-corregidos.md`.

### §4.4 Nombres en español (2026-10-03)

El manual anterior pedía nombres en inglés técnico; el código nunca lo siguió y el ecosistema
escribe en español.

## 5. Documentación

### §5.1 Un lector por documento (2026-10-03)

El manual de `script_compilar_latex/` es para quien usa; `arquitectura.md`, para quien amplía; el
README, la puerta. El contrato con `docencia` vive solo en `arquitectura.md` §Consumidores.

### §5.2 `docs/` se conserva con un README corto: apartamiento de la matriz (2026-10-05)

La normativa documental (2.3, fila 13) prohíbe `docs/` en una suite cuyo README tiene menos de 200
líneas, pero recomienda `docs/decisiones.md` (D) y pide la sección «Consumidores» (N) en el documento
dueño del contrato. Se conservan `decisiones.md` y `arquitectura.md` (dueño de §Consumidores) y se
retiran la carpeta de historial de `docs/` (prohibida, 5.3: git la conserva) y su índice
(obligatorio solo desde cinco documentos, 3.5). Apartamiento asentado según 0.5 y 2.5.
