---
tipo: guia_ia
estado: activo
---
# CLAUDE.md — scripts_for_latex

Guía para el asistente. En español, como todo el ecosistema. `AGENTS.md` es un enlace a este archivo.
Léase antes: `README.md` (de qué es dueño frente a los frameworks), `script_compilar_latex/suite.yml` y
`script_compilar_latex/README.md` (el manual).

## Reglas que no se negocian

- **LuaLaTeX + Biber es el motor normativo** (regla 7 del `CLAUDE.md` raíz): ningún ejemplo, valor por defecto
  ni documento nuevo del ecosistema se escribe para pdflatex o xelatex; compilar con ellos se conserva por
  compatibilidad y no se amplía.
- **Un punto de entrada y ocho módulos**: `main.sh` solo orquesta; cada `lib/*.sh` tiene una responsabilidad
  (tabla del manual); `config.sh` concentra todos los valores por defecto y ningún módulo los redefine.
- **El logger es de `core/`**: `script_compilar_latex/lib/logger.sh` es un envoltorio de
  `core/shell-lib/logger.sh` y solo añade nombres cortos (`info`, `ok`, `warn`, `error`, `paso`, `titulo`); no
  se define otro.
- **Los frameworks no dependen de este repo**: `03 writing`, `10 Class`, `11 Book` y `sgdp/marco_documental`
  compilan con su propio build (latexmk). Un cambio aquí no puede romperlos y tampoco se les impone.
- **`set -e` y el modo watch**: `compilar_segura()` desactiva `set -e` localmente y los códigos de salida se
  capturan en una línea aparte de `local` (`docs/historial/bugs-corregidos.md`). No se «simplifica».
- **Repo público** (`meta/workspace.yml`): nada del despacho ni rutas de máquina en código y ejemplos;
  español.
- **Lo generado no se edita**: los bloques `suites:` del README y `suite:` del manual (`core/suites.py generar
  --aplicar`) y `docs/README.md` (`core/docs.py indice`).

## Cómo se verifica un cambio

```bash
cd scripts_for_latex/script_compilar_latex && for f in *.sh lib/*.sh; do bash -n "$f"; done; cd -   # sintaxis
scripts_for_latex/script_compilar_latex/main.sh --help                    # la CLI carga los ocho módulos
scripts_for_latex/script_compilar_latex/main.sh -e lualatex --biber -p 3 prueba.tex   # modo normativo
python3 core/archivos.py validar scripts_for_latex                 # A01–A14 y D01–D12, desde ~/Documents
python3 core/suites.py validar && python3 core/suites.py generar          # suite.yml y bloques (simula)
python3 core/docs.py verificar scripts_for_latex                          # índice de docs/ al día
```

## Detalles que cuesta redescubrir

- **`--engine auto` acaba en `pdflatex`** si el `.tex` no usa `fontspec`, `polyglossia`, `unicode-math`,
  `\directlua` ni `luacode`; `DEFAULT_ENGINE` está en `config.sh`.
- **`--clean` nunca existió**: la bandera es `-c` o `--limpiar` (el `suite.yml` lo decía mal hasta DOC6).
- **`-o DIR` es relativo al directorio de invocación**; `--log FILE` conserva el log, que si no se borra con
  los auxiliares. Se compila siempre con `pushd "$TEX_DIR"` para que `\include` e `\input` resuelvan.
- **`bash -n` comprueba un archivo por invocación**: de ahí el bucle de arriba.
- El alias `compilar` vive en `~/.dotfiles/shell/.zshrc`; la cabecera de `main.sh` repite cómo instalarlo.
- `.directory` es el icono de carpeta de KDE, no del proyecto: ignorado en git.

## Dónde está cada cosa

| pregunta | documento |
|---|---|
| opciones, ejemplos, requisitos, solución de problemas | `script_compilar_latex/README.md` |
| por qué watch, `PIPESTATUS` y la limpieza están como están | `docs/historial/bugs-corregidos.md` |
| el contrato de suite, el logger y el envoltorio modelo | `core/README.md`, `core/suite.schema.yml` |
| quién compila qué en el ecosistema | `README.md` §Qué es; `meta/ARQUITECTURA.md` §2 |
| el diseño editorial que este repo no trae | `sistema-editorial/README.md` |
