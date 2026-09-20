---
tipo: bitacora
estado: hecho
titulo: "Errores corregidos en la reescritura modular de compilar_latex"
---
# Errores corregidos en la reescritura modular de compilar_latex

Bitácora de depuración: por qué `lib/watch.sh`, `lib/compiler.sh` y `limpiar_auxiliares()` están escritos como están.
Vivía en el manual (`script_compilar_latex/README.md` §«Bugs Corregidos») hasta DOC6 (2026-09-20). Las «líneas
originales» se refieren al script monolítico anterior a la división en módulos (v3.0.0).

### Bug #1: `set -euo pipefail` rompía el modo watch

- **Ubicación**: `set -e` global + `compilar_segura()` (línea 620 original)
- **Descripción**: El `set -e` global hacía que el `|| { ... }` en
  `compilar_segura` no capturase el error correctamente; cualquier fallo
  de compilación terminaba el proceso watch en vez de continuar esperando.
- **Corrección**: En `lib/watch.sh`, `compilar_segura()` desactiva `set -e`
  localmente (`set +e`) antes de llamar a `compilar`, captura el código de
  retorno explícitamente y reactiva `set -e` antes de retornar.

### Bug #2: `local status=${PIPESTATUS[0]}` siempre retornaba 0

- **Ubicación**: `ejecutar_latex()` (líneas 335 y 346 originales)
- **Descripción**: En Bash, `local variable=$(comando)` evalúa `local` como
  el comando y su exit code siempre es 0, descartando el exit code real.
  El error del motor LaTeX pasaba silenciosamente desapercibido.
- **Corrección**: En `lib/compiler.sh`, se declara `local status=0` primero
  y luego se asigna `status=${PIPESTATUS[0]}` en línea separada.

### Bug #3: `limpiar_auxiliares()` no encontraba los auxiliares

- **Ubicación**: `limpiar_auxiliares()` (línea 432 original)
- **Descripción**: Cuando `ARCHIVO` contenía una ruta (no solo un nombre base),
  la función construía rutas incorrectas: buscaba `ruta/al/tex/nombre.aux` en
  el CWD del script en lugar de en el directorio del `.tex`.
- **Corrección**: La función ahora usa `TEX_DIR` y `TEX_BASE` (siempre
  absolutos y correctamente resueltos) en lugar de `ARCHIVO` crudo. Además
  ejecuta la limpieza con `pushd "$TEX_DIR"` para manejar correctamente
  los `.aux` de subdirectorios con `\include`.
