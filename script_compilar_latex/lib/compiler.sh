#!/usr/bin/env bash
# ==============================================================================
# lib/compiler.sh — Lógica de compilación LaTeX
# Proyecto: compilar_latex
# ==============================================================================
# Contiene las funciones que realmente invocan los binarios LaTeX.
# Trabaja siempre en TEX_DIR (el directorio donde vive el .tex),
# independientemente de desde dónde se invocó el script.

# construir_flags()
# Construye el array de flags para el motor LaTeX según la configuración activa.
#
# Outputs (stdout):
#   Los flags separados por espacios
#
# Globals leídas:
#   MODO_DRAFT ENGINE
construir_flags() {
    local -a flags=(-interaction=nonstopmode -halt-on-error)

    # Modo draft: compilación rápida sin imágenes embebidas
    $MODO_DRAFT && flags+=(-draftmode)

    # XeLaTeX en draft: evitar la generación del .xdv intermedio
    if [ "$ENGINE" = "xelatex" ] && $MODO_DRAFT; then
        flags+=(-no-pdf)
    fi

    # SyncTeX: permite saltar entre editor y PDF en visores compatibles
    # (no útil en draft donde el PDF no se genera completo)
    if ! $MODO_DRAFT; then
        flags+=(-synctex=1)
    fi

    echo "${flags[@]}"
}

# ejecutar_latex()
# Invoca el motor LaTeX para una pasada de compilación.
# Se ejecuta desde TEX_DIR para que LaTeX encuentre los \include y \input.
#
# Arguments:
#   $1 - Número de pasada actual (para mostrar en el log)
#
# Globals leídas:
#   ENGINE PASADAS TEX_DIR TEX_BASE LOG_FILE VERBOSE MODO_SILENCIOSO
#
# Returns:
#   0 si el motor terminó sin errores
#   Exits 1 si hubo errores de compilación
ejecutar_latex() {
    local num_pasada="$1"
    local -a flags
    read -ra flags <<< "$(construir_flags)"

    paso "Pasada ${num_pasada}/${PASADAS} con ${ENGINE}..."

    local -a cmd=("$ENGINE" "${flags[@]}" "${TEX_BASE}.tex")
    local status=0

    # Compilar desde el directorio del .tex para que \include / \input funcionen
    pushd "$TEX_DIR" > /dev/null

    if $VERBOSE; then
        "${cmd[@]}" 2>&1 | tee -a "$LOG_FILE"
        status=${PIPESTATUS[0]}
    elif $MODO_SILENCIOSO; then
        "${cmd[@]}" >> "$LOG_FILE" 2>&1
        status=$?
    else
        # Modo normal: filtrar solo líneas relevantes (errores, warnings)
        "${cmd[@]}" 2>&1 | tee -a "$LOG_FILE" \
            | grep -E --color=never \
                '(^!|Warning|Error|Overfull|Underfull|LaTeX Font|Package|Class)' \
            || true
        status=${PIPESTATUS[0]}
    fi

    popd > /dev/null

    if [ "$status" -ne 0 ]; then
        error "El compilador terminó con errores en la pasada ${num_pasada}."
        mostrar_errores_log
        exit 1
    fi
}

# ejecutar_bibliografia()
# Invoca BibTeX o Biber según la configuración.
# También se ejecuta desde TEX_DIR.
#
# Globals leídas:
#   USAR_BIBTEX USAR_BIBER TEX_DIR TEX_BASE LOG_FILE MODO_SILENCIOSO
ejecutar_bibliografia() {
    pushd "$TEX_DIR" > /dev/null

    if $USAR_BIBTEX; then
        paso "Ejecutando BibTeX..."
        if $MODO_SILENCIOSO; then
            bibtex "$TEX_BASE" >> "$LOG_FILE" 2>&1 \
                || warn "BibTeX reportó advertencias (revisa ${TEX_BASE}.blg)"
        else
            bibtex "$TEX_BASE" 2>&1 | tee -a "$LOG_FILE" \
                || warn "BibTeX reportó advertencias (revisa ${TEX_BASE}.blg)"
        fi
    fi

    if $USAR_BIBER; then
        paso "Ejecutando Biber..."
        if $MODO_SILENCIOSO; then
            biber "$TEX_BASE" >> "$LOG_FILE" 2>&1 \
                || warn "Biber reportó advertencias (revisa ${TEX_BASE}.blg)"
        else
            biber "$TEX_BASE" 2>&1 | tee -a "$LOG_FILE" \
                || warn "Biber reportó advertencias (revisa ${TEX_BASE}.blg)"
        fi
    fi

    popd > /dev/null
}

# ejecutar_indices()
# Invoca makeindex y/o makeglossaries según la configuración.
#
# Globals leídas:
#   USAR_MAKEINDEX USAR_MAKEGLOSSARIES TEX_DIR TEX_BASE LOG_FILE
ejecutar_indices() {
    pushd "$TEX_DIR" > /dev/null

    if $USAR_MAKEINDEX; then
        paso "Ejecutando makeindex..."
        makeindex "$TEX_BASE" >> "$LOG_FILE" 2>&1 \
            || warn "makeindex reportó advertencias."
    fi

    if $USAR_MAKEGLOSSARIES; then
        paso "Ejecutando makeglossaries..."
        makeglossaries "$TEX_BASE" >> "$LOG_FILE" 2>&1 \
            || warn "makeglossaries reportó advertencias."
    fi

    popd > /dev/null
}

# mostrar_errores_log()
# Extrae y muestra los primeros bloques de error del archivo .log de LaTeX.
# Busca líneas que comienzan con ! (errores fatales de LaTeX).
#
# Globals leídas:
#   LOG_FILE TEX_BASE
mostrar_errores_log() {
    echo ""
    warn "Extracto de errores del log:"
    separador
    grep -n -A 4 '^!' "$LOG_FILE" 2>/dev/null | head -50 \
        || echo "  (No se pudo leer el log o no hay errores con '!')"
    separador
    echo "  Log completo: ${LOG_FILE}"
    echo ""
}

# limpiar_auxiliares()
# Elimina archivos auxiliares generados por LaTeX en el directorio del .tex.
# También limpia .aux de subdirectorios (para proyectos con \include).
#
# Globals leídas:
#   TEX_DIR TEX_BASE EXTENSIONES_AUXILIARES (de config.sh)
limpiar_auxiliares() {
    paso "Eliminando archivos auxiliares..."
    local eliminados=0

    pushd "$TEX_DIR" > /dev/null

    for ext in "${EXTENSIONES_AUXILIARES[@]}"; do
        local archivo="${TEX_BASE}.${ext}"
        if [ -f "$archivo" ]; then
            rm -f "$archivo"
            (( eliminados++ )) || true
        fi
    done

    # Limpiar .aux de subdirectorios (proyectos con \include{capitulos/...})
    find . -name '*.aux' -not -path './.git/*' -delete 2>/dev/null || true

    popd > /dev/null

    ok "Eliminados ${eliminados} archivo(s) auxiliar(es)."
}
