#!/usr/bin/env bash
# ==============================================================================
# lib/compiler.sh — Lógica de compilación LaTeX
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
#   ENGINE PASADAS TEX_DIR TEX_BASE SALIDA_LOG VERBOSE MODO_SILENCIOSO
#
# Returns:
#   0 si el motor terminó sin errores
#   1 si el motor falló (no hace exit: el modo watch tiene que sobrevivir al fallo)
ejecutar_latex() {
    local num_pasada="$1"
    local -a flags
    read -ra flags <<< "$(construir_flags)"

    paso "Pasada ${num_pasada}/${PASADAS} con ${ENGINE}..."

    local -a cmd=("$ENGINE" "${flags[@]}" "${TEX_BASE}.tex")
    local status=0

    # Compilar desde el directorio del .tex para que \include / \input funcionen
    pushd "$TEX_DIR" > /dev/null

    # El estado del MOTOR se captura con set +e y PIPESTATUS leído en la línea siguiente al
    # pipeline: con `set -e` el script moría antes de leerlo (-s, -v) y con `|| true` PIPESTATUS
    # pasaba a ser el de `true` (modo normal), así que un fallo se anunciaba como éxito.
    local -a estados
    set +e
    if $VERBOSE; then
        "${cmd[@]}" 2>&1 | tee -a "$SALIDA_LOG"
        estados=("${PIPESTATUS[@]}")
    elif $MODO_SILENCIOSO; then
        "${cmd[@]}" >> "$SALIDA_LOG" 2>&1
        estados=("$?")
    else
        # Modo normal: filtrar solo líneas relevantes (errores, warnings); grep sin coincidencias
        # sale con 1 y no cuenta.
        "${cmd[@]}" 2>&1 | tee -a "$SALIDA_LOG" \
            | grep -E --color=never \
                '(^!|Warning|Error|Overfull|Underfull|LaTeX Font|Package|Class)'
        estados=("${PIPESTATUS[@]}")
    fi
    set -e
    status=${estados[0]}

    popd > /dev/null

    if [ "$status" -ne 0 ]; then
        error "El compilador terminó con errores en la pasada ${num_pasada}."
        mostrar_errores_log
        return 1
    fi
}

# ejecutar_bibliografia()
# Invoca BibTeX o Biber según la configuración.
# También se ejecuta desde TEX_DIR.
#
# Globals leídas:
#   USAR_BIBTEX USAR_BIBER TEX_DIR TEX_BASE SALIDA_LOG MODO_SILENCIOSO
ejecutar_bibliografia() {
    pushd "$TEX_DIR" > /dev/null

    if $USAR_BIBTEX; then
        paso "Ejecutando BibTeX..."
        if $MODO_SILENCIOSO; then
            bibtex "$TEX_BASE" >> "$SALIDA_LOG" 2>&1 \
                || warn "BibTeX reportó advertencias (revisa ${TEX_BASE}.blg)"
        else
            bibtex "$TEX_BASE" 2>&1 | tee -a "$SALIDA_LOG" \
                || warn "BibTeX reportó advertencias (revisa ${TEX_BASE}.blg)"
        fi
    fi

    if $USAR_BIBER; then
        paso "Ejecutando Biber..."
        if $MODO_SILENCIOSO; then
            biber "$TEX_BASE" >> "$SALIDA_LOG" 2>&1 \
                || warn "Biber reportó advertencias (revisa ${TEX_BASE}.blg)"
        else
            biber "$TEX_BASE" 2>&1 | tee -a "$SALIDA_LOG" \
                || warn "Biber reportó advertencias (revisa ${TEX_BASE}.blg)"
        fi
    fi

    popd > /dev/null
}

# ejecutar_indices()
# Invoca makeindex y/o makeglossaries según la configuración.
#
# Globals leídas:
#   USAR_MAKEINDEX USAR_MAKEGLOSSARIES TEX_DIR TEX_BASE SALIDA_LOG
ejecutar_indices() {
    pushd "$TEX_DIR" > /dev/null

    if $USAR_MAKEINDEX; then
        paso "Ejecutando makeindex..."
        makeindex "$TEX_BASE" >> "$SALIDA_LOG" 2>&1 \
            || warn "makeindex reportó advertencias."
    fi

    if $USAR_MAKEGLOSSARIES; then
        paso "Ejecutando makeglossaries..."
        makeglossaries "$TEX_BASE" >> "$SALIDA_LOG" 2>&1 \
            || warn "makeglossaries reportó advertencias."
    fi

    popd > /dev/null
}

# mostrar_errores_log()
# Extrae y muestra los primeros bloques de error del .log que escribe el MOTOR (el completo);
# si no existe, de la salida capturada de esta corrida.
# Busca líneas que comienzan con ! (errores fatales de LaTeX).
#
# Globals leídas:
#   TEX_DIR TEX_BASE SALIDA_LOG
mostrar_errores_log() {
    local log="${TEX_DIR}/${TEX_BASE}.log"
    [ -f "$log" ] || log="$SALIDA_LOG"
    echo ""
    warn "Extracto de errores del log:"
    separador
    grep -n -A 4 '^!' "$log" 2>/dev/null | head -50 \
        || echo "  (No se pudo leer el log o no hay errores con '!')"
    separador
    echo "  Log completo: ${log}"
    echo ""
}

# limpiar_auxiliares()
# Elimina archivos auxiliares generados por LaTeX en el directorio del .tex.
# De los subdirectorios, solo los .aux que el .aux principal declara con \@input{…} (los de los
# \include de ESTE documento): antes borraba todo *.aux bajo la carpeta, fuera de quien fuera.
#
# Globals leídas:
#   TEX_DIR TEX_BASE EXTENSIONES_AUXILIARES (de config.sh)
limpiar_auxiliares() {
    paso "Eliminando archivos auxiliares..."
    local eliminados=0

    pushd "$TEX_DIR" > /dev/null

    # Los .aux de los \include se leen del .aux principal antes de borrarlo.
    local -a aux_incluidos=()
    if [ -f "${TEX_BASE}.aux" ]; then
        mapfile -t aux_incluidos < <(grep -oE '\\@input\{[^}]+\.aux\}' "${TEX_BASE}.aux" \
            | sed -E 's/^\\@input\{(.*)\}$/\1/')
    fi

    for ext in "${EXTENSIONES_AUXILIARES[@]}"; do
        local archivo="${TEX_BASE}.${ext}"
        if [ -f "$archivo" ]; then
            rm -f "$archivo"
            (( eliminados++ )) || true
        fi
    done

    local aux
    for aux in "${aux_incluidos[@]}"; do
        case "$aux" in /*|*..*) continue ;; esac      # solo rutas relativas dentro de la carpeta
        if [ -f "$aux" ]; then
            rm -f "$aux"
            (( eliminados++ )) || true
        fi
    done

    popd > /dev/null

    ok "Eliminados ${eliminados} archivo(s) auxiliar(es)."
}
