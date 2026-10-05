#!/usr/bin/env bash
# ==============================================================================
#  script_compilar_latex/main.sh — Punto de entrada
#  Script universal de compilación LaTeX
#
# ==============================================================================
#
#  INSTALACIÓN (una sola vez)
#  --------------------------
#  El script vive siempre en:
#    ~/Documents/scripts-latex/script_compilar_latex/
#
#  Para usarlo desde cualquier directorio, crea un alias en tu ~/.zshrc:
#
#    # zsh
#    alias compilar='~/Documents/scripts-latex/script_compilar_latex/main.sh'
#
#  Luego recargas: source ~/.zshrc  (o abre una nueva terminal)
#
#  USO (desde CUALQUIER directorio, o indicando la ruta exacta del .tex)
#  ----------------------------------------------------------------------
#  compilar                                          → compila index.tex en el CWD
#  compilar tesis                                    → compila tesis.tex en el CWD
#  compilar ~/Documents/04\ index/_pubs/pub_dialectica/articulo      → ruta con tilde
#  compilar ../pub_axiomata/paper                    → ruta relativa
#  compilar --biber ~/Documents/03\ writing/nota            → lualatex + biber
#  compilar --biber -p 3 ~/Documents/04\ index/_pubs/pub_numerus-scriptum/python_intro
#  compilar -w ~/Documents/02\ analysis/informe      → modo watch
#  compilar -c ~/Documents/04\ index/_pubs/pub_chaska/slides         → solo limpiar auxiliares
#
# ==============================================================================

# Salir inmediatamente si un comando falla, variable no definida, o pipe falla
set -euo pipefail

# --- Directorio del script (siempre fijo, independiente del CWD) -----------
# Guardar el CWD del usuario ANTES de cualquier cd, para resolver rutas relativas
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly USER_CWD="$(pwd)"

# --- Cargar módulos --------------------------------------------------------
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

# --- Variables de estado global --------------------------------------------
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
LATEX_LOG=""          # --log: copia de la salida del compilador (opcional)
SALIDA_LOG=""         # donde se anota la salida de esta corrida (LATEX_LOG o un temporal)
# No se llama LOG_FILE: ese nombre es del logger de core/, que escribiría sus mensajes en él.
TIEMPO_INICIO=$(date +%s)
INICIO_COMPILACION=0  # segundo en que empezó la compilación en curso (para saber si el PDF es nuevo)

# Rutas resueltas del .tex (pobladas por resolver_ruta_tex en main())
TEX_PATH=""
TEX_DIR=""
TEX_BASE=""
ARCHIVO_DIR=""
ARCHIVO_BASE=""

# Ruta final del PDF (poblada por mover_pdf en compilar())
PDF_FINAL=""

# --- Función principal de compilación --------------------------------------
# compilar()
# Orquesta el ciclo completo: pasadas LaTeX + bibliografía + índices + resultado.
# Se llama desde main() o desde compilar_segura() en modo watch.
# Returns: 0 si hay PDF nuevo (o, en --draft, si compiló); 1 en cuanto algo falla.
compilar() {
    # Limpiar / inicializar el registro de esta corrida
    > "$SALIDA_LOG"
    INICIO_COMPILACION=$(date +%s)

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

    # --- Pasada 1: siempre obligatoria -------------------------------------
    ejecutar_latex 1 || return 1

    # --- Bibliografía (requiere que la pasada 1 haya generado .aux) --------
    if ( $USAR_BIBTEX || $USAR_BIBER ) && [ "$PASADAS" -ge 2 ]; then
        ejecutar_bibliografia
    fi

    # --- Índices / glosarios -----------------------------------------------
    if ( $USAR_MAKEINDEX || $USAR_MAKEGLOSSARIES ) && [ "$PASADAS" -ge 2 ]; then
        ejecutar_indices
    fi

    # --- Pasadas adicionales (para resolver referencias cruzadas) ----------
    local p
    for (( p=2; p<=PASADAS; p++ )); do
        ejecutar_latex "$p" || return 1
    done

    # --- Resultado final ---------------------------------------------------
    separador
    if $MODO_DRAFT; then
        # -draftmode no escribe el PDF (lualatex lo deja en 0 bytes): se dice, no se anuncia uno.
        [ -f "${TEX_DIR}/${TEX_BASE}.pdf" ] && [ ! -s "${TEX_DIR}/${TEX_BASE}.pdf" ] \
            && rm -f "${TEX_DIR}/${TEX_BASE}.pdf"
        ok "Borrador: el documento compila. No se genera PDF en modo --draft."
        separador
        return 0
    fi
    mostrar_info_pdf || return 1
    mover_pdf
    abrir_pdf
    separador
    ok "¡Compilación completada exitosamente!"
    separador
    sugerir_apertura
}

# --- main() ----------------------------------------------------------------
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

    # 6. Dónde se anota la salida: --log o un temporal (nunca el .log que escribe el motor)
    if [ -n "$LATEX_LOG" ]; then
        SALIDA_LOG="$LATEX_LOG"
    else
        SALIDA_LOG="$(mktemp -t compilar-latex.XXXXXX)"
        trap 'rm -f "$SALIDA_LOG"' EXIT
    fi

    # 7. Ejecutar. Si falla, los auxiliares (y el .log del motor) se quedan para revisarlos.
    if $MODO_WATCH; then
        modo_watch
    elif compilar; then
        limpiar_auxiliares
    else
        exit 1
    fi
}

main "$@"
