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

- **LuaLaTeX + Biber es el motor normativo** (regla 7 del `CLAUDE.md` raíz): ningún ejemplo, valor
  por defecto nuevo ni documento del ecosistema se escribe para pdflatex o xelatex; compilar con
  ellos se conserva por compatibilidad y no se amplía.
- **Un punto de entrada y un módulo por responsabilidad**: `main.sh` orquesta; cada `lib/*.sh`
  tiene una tarea (`docs/arquitectura.md`); `config.sh` concentra los valores por defecto y ningún
  módulo los redefine.
- **El logger es de `core/`**: el `logger.sh` de `lib/` envuelve `core/shell-lib/logger.sh` y
  solo añade nombres cortos; no se define otro.
- **Los frameworks no dependen de este repo, salvo `10 Class`**: `compile_tex` de
  `10 Class/scripts/lib/common.sh` llama a este `main.sh` (con `-s`, sin `-e`) para los `.tex` que
  no son `academic-*`. Cambiar banderas, valores por defecto o códigos de salida es cambiar lo que
  recibe `10 Class`: se mira allí antes.
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

- **El modo normal no ve el error del motor**: `… | grep … || true` deja `PIPESTATUS` en 0. Con
  `-s` y `-v`, `set -e` corta antes de mostrar el extracto. El watch muere al primer `exit 1`. Todo
  en `docs/decisiones.md` §Pendientes, sin corregir.
- **`LOG_FILE` es a la vez el log del motor y el archivo al que el logger de `core/` copia cada
  mensaje**: por eso queda un `<nombre>.log` de una línea tras la limpieza.
- **`--engine auto` acaba en `pdflatex`** si el `.tex` principal no usa `\directlua`, `\luaexec`,
  `\luacode` ni `\usepackage{fontspec|polyglossia|unicode-math}` escrito sin opciones.
- **`--draft` no produce PDF** (con lualatex, uno de 0 bytes).
- **La limpieza borra todos los `*.aux` del árbol** bajo la carpeta del `.tex`.
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
| el contrato de suite y el logger | `core/README.md`, `core/suite.schema.yml` |
| el diseño editorial que este repo no trae | `sistema-editorial/README.md` |
