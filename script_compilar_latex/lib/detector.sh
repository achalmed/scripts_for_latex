#!/usr/bin/env bash
# ==============================================================================
# lib/detector.sh — Elección del motor LaTeX cuando el usuario no pasa --engine
# ==============================================================================
# La regla del ecosistema es LuaLaTeX + Biber (~/Documents/CLAUDE.md, regla 7). «auto» respeta un
# comentario mágico en las 5 primeras líneas del .tex («% !TEX program = pdflatex|xelatex|lualatex»),
# que es como el material heredado pide otro motor, y si no lo hay elige lualatex. Es la misma
# convención que latex_engine() de 10 Class/scripts/lib/common.sh.
#
# Antes adivinaba por paquetes (fontspec → xelatex; nada → pdflatex): eso contradecía la regla
# y fallaba con \usepackage[opciones]{fontspec} (docs/decisiones.md).

# detectar_engine()
# Arguments: $1 - Ruta absoluta al archivo .tex principal
# Outputs (stdout): pdflatex | xelatex | lualatex
detectar_engine() {
    local tex_file="$1" magico
    magico="$(head -5 "$tex_file" 2>/dev/null \
        | grep -oiE '%[[:space:]]*!TEX[[:space:]]+(TS-)?program[[:space:]]*=[[:space:]]*(pdflatex|xelatex|lualatex)' \
        | head -1 | grep -oiE '(pdflatex|xelatex|lualatex)$' || true)"
    if [ -n "$magico" ]; then
        echo "${magico,,}"
    else
        echo "lualatex"
    fi
}

# detectar_y_anunciar_engine()
# Arguments: $1 - Ruta al .tex; $2 - ENGINE actual ("auto" o uno elegido)
# Sets (global): ENGINE — el motor final que se usará
detectar_y_anunciar_engine() {
    local tex_file="$1"
    local engine_actual="$2"

    if [ "$engine_actual" != "auto" ]; then
        # El usuario eligió explícitamente; no tocar nada
        ENGINE="$engine_actual"
        return 0
    fi

    ENGINE="$(detectar_engine "$tex_file")"
    info "Motor: ${BOLD}${ENGINE}${NC}"
    dim "(lualatex salvo «% !TEX program = …» en el .tex; --engine lo fija)"
}
