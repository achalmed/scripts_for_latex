---
tipo: guia_ia
estado: activo
---
# CLAUDE.md — scripts_for_latex

Guía para el asistente. En español, como todo el ecosistema. `AGENTS.md` es un enlace a este
archivo. Léase antes: `README.md` (qué compila cada framework y qué pasa por aquí),
`docs/README.md`, `script_compilar_latex/suite.yml` y, antes de tocar código,
`docs/arquitectura.md` y `docs/decisiones.md` §Pendientes.

## Reglas que no se negocian

- **LuaLaTeX + Biber es el motor normativo** (regla 7 del `CLAUDE.md` raíz): `auto` elige lualatex
  salvo un `% !TEX program = …` en las 5 primeras líneas del `.tex`; pdflatex y xelatex se conservan
  solo para material heredado que lo declare, y no se amplían.
- **Un punto de entrada y un módulo por responsabilidad**: `main.sh` orquesta; cada `lib/*.sh`
  tiene una tarea (`docs/arquitectura.md`); `config.sh` concentra los valores por defecto y ningún
  módulo los redefine.
- **El logger es de `core/`**: el `logger.sh` de `lib/` envuelve `core/shell-lib/logger.sh` y
  solo añade nombres cortos; no se define otro.
- **Los frameworks no dependen de este repo, salvo `10 Class`**: el contrato está en
  `docs/arquitectura.md` §Consumidores. Cambiar la ruta, banderas, valores por defecto o códigos de
  salida es cambiar lo que recibe `10 Class`: se mira allí antes.
- **No se compila nada dentro de otro repo para probar**: compilar reescribe PDFs versionados. Se
  prueba con un `.tex` mínimo en una carpeta temporal.
- **Repo público** (`meta/workspace.yml`): nada del despacho ni rutas de máquina en código y
  ejemplos.
- **Lo generado no se edita**: el bloque `suites:` del README y `suite:` del manual
  (`core/suites.py generar --aplicar`) y el índice de `docs/README.md` (`core/docs.py indice`).

## Cómo se verifica un cambio

```bash
cd scripts_for_latex/script_compilar_latex && for f in *.sh lib/*.sh; do bash -n "$f"; done; cd -
scripts_for_latex/script_compilar_latex/main.sh --help                 # carga todos los módulos
# compilar un .tex mínimo en una carpeta temporal: docs/arquitectura.md §Cómo se verifica
python3 core/archivos.py validar scripts_for_latex                     # desde ~/Documents
python3 core/suites.py validar && python3 core/suites.py generar   # suite.yml y bloques; simula
python3 core/docs.py verificar scripts_for_latex                       # índice de docs/ al día
```

Un cambio en la detección de errores se prueba en los tres modos (normal, `-s`, `-v`), con y sin un
PDF anterior en la carpeta.

## Detalles que cuesta redescubrir

- **El estado del motor se lee con `set +e` y `PIPESTATUS` justo después del pipeline**
  (`ejecutar_latex`): un `|| true` o un `set -e` activo lo pierden, y el script anunciaba éxito con
  un PDF viejo. Un fallo hace `return 1`, no `exit`, para que el watch sobreviva; y `mostrar_info_pdf`
  rechaza un PDF anterior a la compilación o vacío.
- **`LOG_FILE` es del logger de `core/`**: no se usa aquí. La salida de una corrida va a
  `SALIDA_LOG` (el `--log` o un temporal); el extracto de errores sale del `.log` del motor.
- **`--draft` no produce PDF**: lo dice y borra el de 0 bytes que deja lualatex.
- **La limpieza borra los auxiliares del documento y los `.aux` que su `.aux` declara con
  `\@input`**, nunca otros de la carpeta.
- **La bandera de limpieza es `-c`/`--limpiar`**; `--clean` no existe.
- **`-o DIR` es relativo al directorio de invocación**; se compila con `pushd "$TEX_DIR"` para que
  `\include` e `\input` resuelvan.
- **La tilde entre comillas no se expande** y el resolver no la interpreta.
- **`bash -n` comprueba un archivo por invocación**: de ahí el bucle de arriba.
- `inotifywait` no está instalado en esta máquina: el watch no arranca aquí.
- El alias `compilar` vive en `~/.dotfiles/shell/.zshrc` (solo zsh); `.directory` es el icono de
  carpeta de KDE, ignorado en git.

## Dónde está cada cosa

| pregunta | documento |
|---|---|
| opciones, ejemplos, problemas frecuentes | `script_compilar_latex/README.md` |
| flujo, módulos, estado global, cómo añadir una opción o un motor | `docs/arquitectura.md` |
| por qué está así; errores conocidos sin corregir | `docs/decisiones.md` |
| la reescritura modular y sus tres errores | `docs/historial/bugs-corregidos.md` |
| quién compila qué en el ecosistema | `README.md` §Qué es; `meta/ARQUITECTURA.md` §2 y §3 |
| qué usa `10 Class` de esta herramienta | `docs/arquitectura.md` §Consumidores |
| el contrato de suite y el logger | `core/README.md`, `core/suite.schema.yml` |
| el diseño editorial que este repo no trae | `sistema-editorial/README.md` |

## Dónde va lo nuevo

| lo que apareció | va a |
|---|---|
| una opción, un ejemplo, un problema frecuente | `script_compilar_latex/README.md` |
| cómo funciona por dentro; un consumidor nuevo | `docs/arquitectura.md` (§Consumidores) |
| por qué se decidió; un error o una carencia | `docs/decisiones.md` (§Pendientes, con fecha y dueño) |
| lo que se hizo en una tarea | el mensaje de commit |

Nunca un `.md` nuevo en la raíz ni en `docs/` por sesión, fecha o tarea.
