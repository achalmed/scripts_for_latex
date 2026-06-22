#!/usr/bin/env bash
# ==============================================================================
#  compilar_latex / main.sh — Punto de entrada
#  Script universal de compilación LaTeX
#
#  Autor  : Edison Achalma <achalmaedison@gmail.com>
#  GitHub : github.com/achalmed
#  ORCID  : 0000-0001-6996-3364
#  Versión: 3.0.0
# ==============================================================================
#
#  INSTALACIÓN (una sola vez)
#  --------------------------
#  El script vive siempre en:
#    ~/Documents/scripts_for_latex/script_compilar_latex/
#
#  Para usarlo desde cualquier directorio, crea un alias en tu ~/.zshrc o
#  ~/.config/fish/config.fish:
#
#    # zsh
#    alias compilar='~/Documents/scripts_for_latex/script_compilar_latex/main.sh'
#
#    # fish
#    alias compilar '~/Documents/scripts_for_latex/script_compilar_latex/main.sh'
#
#  Luego recargas: source ~/.zshrc  (o abre una nueva terminal)
#
#  USO (desde CUALQUIER directorio, o indicando la ruta exacta del .tex)
#  ----------------------------------------------------------------------
#  compilar                                          → compila index.tex en el CWD
#  compilar tesis                                    → compila tesis.tex en el CWD
#  compilar ~/Documents/pub_dialectica/articulo      → ruta con tilde
#  compilar ../pub_axiomata/paper                    → ruta relativa
#  compilar /home/achalmaedison/Documents/pub_res-publica/capitulo1
#  compilar -e xelatex ~/Documents/03\ writing/nota
#  compilar --biber -p 3 ~/Documents/pub_numerus-scriptum/python_intro
#  compilar -w ~/Documents/02\ analysis/informe      → modo watch
#  compilar -c ~/Documents/pub_chaska/slides         → solo limpiar auxiliares
#
# ==============================================================================

# Salir inmediatamente si un comando falla, variable no definida, o pipe falla
set -euo pipefail

# ── Directorio del script (siempre fijo, independiente del CWD) ───────────────
# Guardar el CWD del usuario ANTES de cualquier cd, para resolver rutas relativas
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly USER_CWD="$(pwd)"

# ── Cargar módulos ────────────────────────────────────────────────────────────
# shellcheck source=config.sh
source "${SCRIPT_DIR}/config.sh"

# Inicializar colores después de cargar config (las variables ya existen)
_init_colores

# shellcheck source=lib/logger.sh
source "${SCRIPT_DIR}/lib/logger.sh"

# shellcheck source=lib/validator.sh
source "${SCRIPT_DIR}/lib/validator.sh"

# shellcheck source=lib/resolver.sh
source "${SCRIPT_DIR}/lib/resolver.sh"

# shellcheck source=lib/detector.sh
source "${SCRIPT_DIR}/lib/detector.sh"

# shellcheck source=lib/cli.sh
source "${SCRIPT_DIR}/lib/cli.sh"

# shellcheck source=lib/compiler.sh
source "${SCRIPT_DIR}/lib/compiler.sh"

# shellcheck source=lib/output.sh
source "${SCRIPT_DIR}/lib/output.sh"

# shellcheck source=lib/watch.sh
source "${SCRIPT_DIR}/lib/watch.sh"

# ── Variables de estado global ────────────────────────────────────────────────
# Inicializadas con los defaults de config.sh; sobreescritas por parsear_args()
ARCHIVO="$DEFAULT_ARCHIVO"
ENGINE="$DEFAULT_ENGINE"
PASADAS="$DEFAULT_PASADAS"
MODO_SILENCIOSO=false
SOLO_LIMPIAR=false
MODO_WATCH=false
MODO_DRAFT=false
DIRECTORIO_SALIDA=""
USAR_BIBTEX=false
USAR_BIBER=false
USAR_MAKEINDEX=false
USAR_MAKEGLOSSARIES=false
ABRIR_PDF=false
VERBOSE=false
LOG_FILE=""
TIEMPO_INICIO=$(date +%s)

# Rutas resueltas del .tex (pobladas por resolver_ruta_tex en main())
TEX_PATH=""
TEX_DIR=""
TEX_BASE=""
ARCHIVO_DIR=""
ARCHIVO_BASE=""

# Ruta final del PDF (poblada por mover_pdf en compilar())
PDF_FINAL=""

# ── Función principal de compilación ─────────────────────────────────────────
# compilar()
# Orquesta el ciclo completo: pasadas LaTeX + bibliografía + índices + resultado.
# Se llama desde main() o desde compilar_segura() en modo watch.
compilar() {
    # Limpiar / inicializar el log de esta sesión
    > "$LOG_FILE"

    titulo "Compilando: ${TEX_BASE}.tex  [engine: ${ENGINE}]"

    # Mostrar configuración activa para que el usuario sepa qué está ocurriendo
    info "Directorio : ${TEX_DIR}"
    info "Pasadas    : ${PASADAS}"
    $MODO_DRAFT          && info "Modo       : borrador (draft)"
    $USAR_BIBTEX         && info "Bibliografía: BibTeX"
    $USAR_BIBER          && info "Bibliografía: Biber"
    $USAR_MAKEINDEX      && info "Índice     : makeindex"
    $USAR_MAKEGLOSSARIES && info "Glosario   : makeglossaries"
    [ -n "$DIRECTORIO_SALIDA" ] && info "Salida PDF : ${DIRECTORIO_SALIDA}/"
    echo ""

    # ── Pasada 1: siempre obligatoria ─────────────────────────────────────
    ejecutar_latex 1

    # ── Bibliografía (requiere que la pasada 1 haya generado .aux) ────────
    if ( $USAR_BIBTEX || $USAR_BIBER ) && [ "$PASADAS" -ge 2 ]; then
        ejecutar_bibliografia
    fi

    # ── Índices / glosarios ───────────────────────────────────────────────
    if ( $USAR_MAKEINDEX || $USAR_MAKEGLOSSARIES ) && [ "$PASADAS" -ge 2 ]; then
        ejecutar_indices
    fi

    # ── Pasadas adicionales (para resolver referencias cruzadas) ──────────
    local p
    for (( p=2; p<=PASADAS; p++ )); do
        ejecutar_latex "$p"
    done

    # ── Resultado final ───────────────────────────────────────────────────
    separador
    mostrar_info_pdf
    mover_pdf
    abrir_pdf
    separador
    ok "¡Compilación completada exitosamente!"
    separador
    sugerir_apertura
}

# ── main() ────────────────────────────────────────────────────────────────────
main() {
    banner

    # 1. Parsear argumentos de la CLI
    parsear_args "$@"

    # 2. Resolver la ruta completa del .tex indicado
    #    Se pasa el CWD original del usuario para resolver rutas relativas
    if ! resolver_ruta_tex "$ARCHIVO" "$USER_CWD"; then
        error "No se encontró el archivo: '${ARCHIVO}.tex'"
        sugerir_tex_cercanos "$ARCHIVO" "$USER_CWD"
        exit 1
    fi

    # 3. Modo solo-limpiar: no necesita verificar motor ni compilar
    if $SOLO_LIMPIAR; then
        titulo "Limpieza de archivos auxiliares en: ${TEX_DIR}"
        limpiar_auxiliares
        exit 0
    fi

    # 4. Detectar o validar el motor LaTeX
    #    (detectar_y_anunciar_engine puede cambiar ENGINE de "auto" al motor real)
    detectar_y_anunciar_engine "$TEX_PATH" "$ENGINE"

    # 5. Verificar que todos los binarios necesarios estén instalados
    verificar_dependencias

    # 6. Definir la ruta del log (ahora que TEX_DIR y TEX_BASE están resueltos)
    if [ -z "$LOG_FILE" ]; then
        LOG_FILE="${TEX_DIR}/${TEX_BASE}.log"
    fi

    # 7. Ejecutar
    if $MODO_WATCH; then
        modo_watch
    else
        compilar
        limpiar_auxiliares
    fi
}

main "$@"
