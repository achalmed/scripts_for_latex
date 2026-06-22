#!/usr/bin/env bash
# ==============================================================================
# lib/watch.sh — Modo watch: recompilación automática al detectar cambios
# Proyecto: compilar_latex
# ==============================================================================
# Vigila el directorio del .tex (TEX_DIR) en busca de cambios en
# archivos .tex, .bib, .sty y .cls.
#
# En Linux  → usa inotifywait (paquete: inotify-tools)
# En macOS  → usa fswatch

# compilar_segura()
# Llama a compilar() sin propagar errores al caller.
# Necesaria en modo watch para que un error de compilación no termine el loop.
# Desactivamos set -e localmente para que el || funcione correctamente.
# (Bug #1 corregido: set -euo pipefail global rompía este patrón)
compilar_segura() {
    # Desactivar exit-on-error solo en este scope para capturar el fallo
    set +e
    compilar
    local resultado=$?
    set -e

    if [ "$resultado" -ne 0 ]; then
        warn "Compilación fallida. Esperando próximo cambio para reintentar..."
    fi
}

# modo_watch()
# Inicia el bucle de vigilancia de archivos.
# Hace una compilación inicial inmediata y luego espera cambios.
#
# Globals leídas:
#   TEX_DIR OSTYPE TIEMPO_INICIO
modo_watch() {
    info "Modo watch activado. Vigilando: ${TEX_DIR}"
    info "Archivos observados: *.tex  *.bib  *.sty  *.cls"
    info "Presiona Ctrl+C para salir."
    echo ""

    # Primera compilación inmediata al activar el modo watch
    compilar_segura

    if [[ "$OSTYPE" == "darwin"* ]]; then
        _watch_macos
    else
        _watch_linux
    fi
}

# _watch_linux()
# Bucle de vigilancia usando inotifywait (Linux).
# Observa el directorio del .tex, no el CWD del script.
_watch_linux() {
    while inotifywait -q -e close_write,moved_to \
            --include '.*\.(tex|bib|sty|cls)$' \
            "$TEX_DIR" 2>/dev/null; do
        echo ""
        info "Cambio detectado. Recompilando..."
        TIEMPO_INICIO=$(date +%s)
        compilar_segura
    done
}

# _watch_macos()
# Bucle de vigilancia usando fswatch (macOS).
_watch_macos() {
    fswatch -0 --event Updated \
            --include '.*\.(tex|bib|sty|cls)$' \
            "$TEX_DIR" \
    | while IFS= read -r -d '' _; do
        echo ""
        info "Cambio detectado. Recompilando..."
        TIEMPO_INICIO=$(date +%s)
        compilar_segura
    done
}
