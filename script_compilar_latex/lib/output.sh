#!/usr/bin/env bash
# ==============================================================================
# lib/output.sh — Presentación de resultados: info del PDF, mover, abrir, banner
# Proyecto: compilar_latex
# ==============================================================================

# banner()
# Imprime el banner ASCII del script.
banner() {
    echo -e "${BOLD}"
    echo "  ██╗      █████╗ ████████╗███████╗██╗  ██╗"
    echo "  ██║     ██╔══██╗╚══██╔══╝██╔════╝╚██╗██╔╝"
    echo "  ██║     ███████║   ██║   █████╗   ╚███╔╝ "
    echo "  ██║     ██╔══██║   ██║   ██╔══╝   ██╔██╗ "
    echo "  ███████╗██║  ██║   ██║   ███████╗██╔╝ ██╗"
    echo "  ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝"
    echo -e "  ${DIM}${SCRIPT_NAME} v${VERSION} — Universal LaTeX Builder${NC}"
    echo ""
}

# mostrar_info_pdf()
# Muestra información del PDF generado: ruta, tamaño, páginas, título, autor.
# Usa pdfinfo si está disponible (poppler-utils).
#
# Globals leídas:
#   TEX_DIR TEX_BASE DIRECTORIO_SALIDA TIEMPO_INICIO
mostrar_info_pdf() {
    local pdf="${TEX_DIR}/${TEX_BASE}.pdf"

    if [ ! -f "$pdf" ]; then
        error "No se encontró el PDF esperado: ${pdf}"
        exit 1
    fi

    ok "PDF generado: ${BOLD}${pdf}${NC}"

    # Tamaño del archivo
    local tamanio
    tamanio=$(du -h "$pdf" | cut -f1)
    info "Tamaño : ${tamanio}"

    # Metadata y número de páginas (requiere poppler-utils)
    if command -v pdfinfo &>/dev/null; then
        local paginas titulo autor
        paginas=$(pdfinfo "$pdf" 2>/dev/null \
            | grep -i '^Pages:' | awk '{print $2}' || echo "?")
        titulo=$(pdfinfo  "$pdf" 2>/dev/null \
            | grep -i '^Title:'  | sed 's/^Title:[[:space:]]*//' || echo "")
        autor=$(pdfinfo   "$pdf" 2>/dev/null \
            | grep -i '^Author:' | sed 's/^Author:[[:space:]]*//' || echo "")

        info "Páginas: ${paginas}"
        [ -n "$titulo" ] && info "Título : ${titulo}"
        [ -n "$autor"  ] && info "Autor  : ${autor}"
    fi

    info "Tiempo : $(elapsed) segundo(s)"
}

# mover_pdf()
# Si el usuario especificó --output DIR, mueve el PDF al directorio indicado.
# El directorio se crea si no existe.
#
# Globals leídas:
#   TEX_DIR TEX_BASE DIRECTORIO_SALIDA
#
# Sets (global):
#   PDF_FINAL — ruta final donde quedó el PDF (para abrir_pdf)
mover_pdf() {
    local pdf_origen="${TEX_DIR}/${TEX_BASE}.pdf"

    if [ -n "$DIRECTORIO_SALIDA" ]; then
        mkdir -p "$DIRECTORIO_SALIDA"
        mv "$pdf_origen" "${DIRECTORIO_SALIDA}/${TEX_BASE}.pdf"
        PDF_FINAL="${DIRECTORIO_SALIDA}/${TEX_BASE}.pdf"
        ok "PDF movido a: ${PDF_FINAL}"
    else
        PDF_FINAL="$pdf_origen"
    fi
}

# abrir_pdf()
# Abre el PDF con el primer visor disponible en el sistema.
# Solo actúa si ABRIR_PDF=true.
#
# Globals leídas:
#   ABRIR_PDF PDF_FINAL VISORES_PDF (de config.sh)
abrir_pdf() {
    $ABRIR_PDF || return 0

    paso "Abriendo ${PDF_FINAL}..."

    local visor=""
    for v in "${VISORES_PDF[@]}"; do
        if command -v "$v" &>/dev/null; then
            visor="$v"
            break
        fi
    done

    if [ -n "$visor" ]; then
        "$visor" "$PDF_FINAL" &
        ok "PDF abierto con: ${visor}"
    else
        warn "No se encontró un visor de PDF instalado."
        echo "  Instala uno: evince / okular / zathura"
        echo "  O abre manualmente: ${PDF_FINAL}"
    fi
}

# sugerir_apertura()
# Cuando --abrir no se usó, sugiere cómo abrir el PDF manualmente.
#
# Globals leídas:
#   ABRIR_PDF PDF_FINAL
sugerir_apertura() {
    $ABRIR_PDF && return 0

    echo ""
    dim "Para abrir el PDF:"
    dim "  evince  \"${PDF_FINAL}\" &"
    dim "  okular  \"${PDF_FINAL}\" &"
    dim "  zathura \"${PDF_FINAL}\" &"
    echo ""
}

# elapsed()
# Retorna los segundos transcurridos desde TIEMPO_INICIO.
#
# Globals leídas:
#   TIEMPO_INICIO
elapsed() {
    echo $(( $(date +%s) - TIEMPO_INICIO ))
}
