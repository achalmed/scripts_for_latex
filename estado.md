---
tipo: estado
estado: activo
actualizado: 2026-10-05
---
# estado.md — scripts-latex

## Hecho

| fecha | qué | dónde se ve |
|---|---|---|
| 2026-10-05 | documentación según la normativa documental: `estado.md`, README de suite, `CLAUDE.md` corto, pendientes fuera de `decisiones.md`, `docs/historial/` e índice retirados | `docs/decisiones.md` §5.2 |
| 2026-10-05 | `--dry-run` (`-n`) y su prueba de suite | `script_compilar_latex/tests/dry-run.sh` |
| 2026-10-05 | renombre `scripts_for_latex` → `scripts-latex` (piloto 1); el remoto no cambia | commit `b14f783`; `docs/decisiones.md` §1.5 |
| 2026-10-04 | licencia MIT; manifiesto y bloques generados al día | commits `d23aee3`, `31cc784` |
| 2026-10-03 | ciclo de compilación robusto: errores del motor, watch, limpieza, `--draft`, `auto` = lualatex | commit `606e4ee`; `docs/decisiones.md` §3 |

## En curso

nada en curso

## Por hacer

Los números P4–P17 son los de la revisión del 2026-10-03 y 2026-10-04; se conservan porque el
manual los cita.

- 2026-10-04 · dueño: el autor · **P17** `sugerir_tex_cercanos` no llega a listar: con `set -e` y `pipefail` un `find` que falla corta el script; con ruta absoluta busca en `<cwd>/<ruta>` (`script_compilar_latex/lib/resolver.sh`).
- 2026-10-04 · dueño: el autor · **P14** `--log` con ruta relativa se escribe en dos sitios: `compilar` la vacía desde el directorio de invocación y `ejecutar_latex` le añade la salida dentro de `pushd "$TEX_DIR"`; hasta corregirlo, ruta absoluta.
- 2026-10-04 · dueño: el autor · **P9** el banner sale también con `--help` y `--version`: `main()` llama a `banner` antes de `parsear_args`.
- 2026-10-04 · dueño: el autor · **P15** la ayuda de `--log` dice «default: ARCHIVO.log» y sin `--log` no hay copia; los ejemplos de la ayuda y de la cabecera de `main.sh` usan rutas que no existen.
- 2026-10-04 · dueño: el autor · **P16** `VERSION` de `config.sh` no se mantiene (sigue en 3.0.0) y nadie la consume: mantenerla a mano o quitarla.
- 2026-10-03 · dueño: el autor · **P4** el watch no vigila subcarpetas (`inotifywait` sin `-r`).
- 2026-10-05 · dueño: el autor · **RQ-COD-09** `pdflatex` y `xelatex` siguen aceptados en `config.sh`, `lib/cli.sh`, `lib/detector.sh` y `lib/validator.sh` para material heredado (decisiones §2.1): retirarlos o declarar la excepción en la normativa.
- 2026-10-05 · dueño: el programa (normativa 2.1.0) · **RQ-COD-01** los módulos de `lib/` no llevan `set -euo pipefail`: se cargan con `source` y lo heredan de `main.sh` (decisiones §4.3); ponerlo en cada uno cambiaría la shell que los carga. La norma debe exceptuar los módulos cargados con `source`.
- 2026-10-05 · dueño: el programa · **RQ-IDN-03** la carpeta `script_compilar_latex/` no es kebab: renombrarla mueve la ruta que leen `10 Class/config/course.yml` y el alias de `~/.dotfiles`; va con la ola 4.
- 2026-10-05 · dueño: core · **manual generado** el manual de `script_compilar_latex/README.md` repite `--help` a mano; la normativa (2.4) lo quiere generado y el generador no existe.
- 2026-10-05 · dueño: meta · **RQ-MAN-03** el doctor ve aristas sin declarar hacia `academic_class_framework` y `academic_writing_framework` en comentarios de `lib/detector.sh` y `lib/resolver.sh`: falsos positivos que la prueba debería ignorar en comentarios.

## Futuro

- Vigilancia recursiva en el modo watch, con exclusión de los auxiliares.
- Generar la tabla de opciones del manual desde `mostrar_ayuda()`.
