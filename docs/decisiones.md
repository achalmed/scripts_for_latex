---
tipo: decision
estado: activo
titulo: "Decisiones de scripts-latex"
forma: explicacion
---
# Decisiones de scripts-latex

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

`03 writing`, `11 Book`, `sgdp/marco_documental` y los `academic-*` de `10 Class` no pasan por
aquí; un cambio en este repo no puede romperlos. El único consumidor por código es `compile_tex` de
`10 Class` para los `.tex` que no son del framework (contrato en `arquitectura.md` §Consumidores).

### §1.3 No trae diseño (2026-09-20)

Ni clases, ni plantillas, ni preámbulos: eso es de `sistema-editorial` y de cada framework.

### §1.4 Sin latexmk (2026-06-22)

Pasadas fijas (`-p`), 3 en cuanto se pide bibliografía o glosario: quien compila ve y controla
cada pasada.

### §1.5 La carpeta se llama `scripts-latex`; el remoto sigue siendo `scripts_for_latex` (2026-10-05)

Renombre aprobado en la Puerta P3 (P3-1: carpeta = `id`, kebab) y aplicado como piloto 1 del
programa con `core/renombrar.py`; el manifiesto guarda `id_anterior: scripts_for_latex`. El remoto
de GitHub no cambia (plan de conversión, C7). Los consumidores leen la carpeta por `SCRIPTS_LATEX`
(`core/env.sh`), salvo el alias de `~/.dotfiles`, que no carga `core/`.

## 2. Motor

### §2.1 LuaLaTeX + Biber es el motor normativo (2026-09-20)

Regla 7 del `CLAUDE.md` raíz. Ningún ejemplo ni valor nuevo se escribe para pdflatex o xelatex, que
se conservan para material heredado que los declare.

### §2.2 `DEFAULT_ENGINE` en `auto`, y `auto` cae en `pdflatex` (2026-09-20)

Superada por §2.3 (2026-10-03).

### §2.3 `auto` es lualatex, salvo el comentario mágico (2026-10-03)

La heurística por paquetes contradecía la regla 7 y no veía `\usepackage[…]{fontspec}`. `auto` lee
`% !TEX program = …` en las 5 primeras líneas (la convención de `10 Class/scripts/lib/common.sh`)
y, sin él, elige lualatex. El andamio de los decks de `10 Class` ya declara `lualatex`.

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
README, la puerta. El contrato con `10 Class` vive solo en `arquitectura.md` §Consumidores.

### §5.2 `docs/` se conserva con un README corto: apartamiento de la matriz (2026-10-05)

La normativa documental (2.3, fila 13) prohíbe `docs/` en una suite cuyo README tiene menos de 200
líneas, pero recomienda `docs/decisiones.md` (D) y pide la sección «Consumidores» (N) en el documento
dueño del contrato. Se conservan `decisiones.md` y `arquitectura.md` (dueño de §Consumidores) y se
retiran la carpeta de historial de `docs/` (prohibida, 5.3: git la conserva) y su índice
(obligatorio solo desde cinco documentos, 3.5). Apartamiento asentado según 0.5 y 2.5.
