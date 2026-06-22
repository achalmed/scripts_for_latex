#!/usr/bin/env bash
# ==============================================================================
# lib/detector.sh — Detección automática del motor LaTeX más adecuado
# Proyecto: compilar_latex
# ==============================================================================
# Cuando el usuario no especifica --engine, este módulo inspecciona el .tex
# y elige el motor más adecuado según las paquetes y comandos que usa.
#
# Heurística (en orden de prioridad):
#   1. fontspec / polyglossia / unicode-math → xelatex o lualatex
#   2. luacode / luaexec / directlua        → lualatex
#   3. Sin indicadores especiales            → pdflatex (máxima compatibilidad)
#
# Para la distinción xelatex vs lualatex cuando hay fontspec:
#   - luacode o directlua → lualatex
#   - caso contrario      → xelatex (más rápido para documentos estándar)

# detectar_engine()
# Lee el archivo .tex y determina el motor más apropiado.
#
# Arguments:
#   $1 - Ruta absoluta al archivo .tex principal
#
# Outputs (stdout):
#   El nombre del motor: pdflatex | xelatex | lualatex
#
# Returns:
#   0 siempre (siempre hay un motor sugerido)
detectar_engine() {
    local tex_file="$1"

    # Grep sin distinción de mayúsculas; solo el nombre del paquete o comando
    local usa_lua=false
    local usa_fontspec=false

    # Indicadores de scripting Lua embebido
    if grep -qiE '\\(directlua|luaexec|luacode)' "$tex_file" 2>/dev/null; then
        usa_lua=true
    fi

    # Indicadores de fuentes del sistema o Unicode avanzado
    if grep -qiE '\\usepackage\{(fontspec|polyglossia|unicode-math)\}' \
            "$tex_file" 2>/dev/null; then
        usa_fontspec=true
    fi

    if $usa_lua; then
        echo "lualatex"
    elif $usa_fontspec; then
        echo "xelatex"
    else
        echo "pdflatex"
    fi
}

# detectar_y_anunciar_engine()
# Llama a detectar_engine() e imprime un mensaje informativo si se usó
# la detección automática (no cuando el usuario eligió explícitamente).
#
# Arguments:
#   $1 - Ruta absoluta al .tex
#   $2 - Valor actual de ENGINE (puede ser "auto" o uno ya elegido)
#
# Sets (global):
#   ENGINE — el motor final que se usará
#
# Returns:
#   0 siempre
detectar_y_anunciar_engine() {
    local tex_file="$1"
    local engine_actual="$2"

    if [ "$engine_actual" != "auto" ]; then
        # El usuario eligió explícitamente; no tocar nada
        ENGINE="$engine_actual"
        return 0
    fi

    ENGINE="$(detectar_engine "$tex_file")"
    info "Motor detectado automáticamente: ${BOLD}${ENGINE}${NC}"
    dim "(usa --engine para sobreescribir: pdflatex | xelatex | lualatex)"
}
