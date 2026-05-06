#!/bin/bash
# ==============================================================================
#  compilar_latex.sh — Script universal de compilación LaTeX
#  Soporta: pdflatex · xelatex · lualatex
#  Autor  : generado como plantilla reutilizable
#  Versión: 2.0.0
# ==============================================================================
#
#  USO RÁPIDO
#  ----------
#  ./compilar_latex.sh [OPCIONES] [ARCHIVO]
#
#  EJEMPLOS
#  --------
#  ./compilar_latex.sh                          # compila index.tex con pdflatex
#  ./compilar_latex.sh tesis                    # compila tesis.tex con pdflatex
#  ./compilar_latex.sh -e xelatex documento     # usa XeLaTeX
#  ./compilar_latex.sh -e lualatex -b main      # usa LuaLaTeX
#  ./compilar_latex.sh -e pdflatex -p 3 reporte # 3 pasadas (refs complejas)
#  ./compilar_latex.sh -s slides                # modo silencioso
#  ./compilar_latex.sh -c                       # solo limpiar auxiliares
#  ./compilar_latex.sh -o ./build tesis         # directorio de salida custom
#  ./compilar_latex.sh -w tesis                 # modo watch (recompila al guardar)
#  ./compilar_latex.sh --draft tesis            # modo borrador (rápido)
#  ./compilar_latex.sh --help                   # muestra esta ayuda
#
# ==============================================================================

set -euo pipefail

# ──────────────────────────────────────────────────────────────────────────────
# COLORES Y FORMATO
# ──────────────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# Detectar si el terminal soporta colores
if ! tput colors &>/dev/null 2>&1 || [ "${NO_COLOR:-}" = "1" ]; then
    RED='' GREEN='' YELLOW='' BLUE='' CYAN='' BOLD='' DIM='' NC=''
fi

# ──────────────────────────────────────────────────────────────────────────────
# VALORES POR DEFECTO
# ──────────────────────────────────────────────────────────────────────────────
ARCHIVO="index"                # nombre del .tex sin extensión
ENGINE="pdflatex"              # motor: pdflatex | xelatex | lualatex
PASADAS=2                      # número de compilaciones (mínimo 2 para refs)
MODO_SILENCIOSO=false          # -s : suprime salida del compilador
SOLO_LIMPIAR=false             # -c : solo elimina auxiliares
MODO_WATCH=false               # -w : recompila al detectar cambios
MODO_DRAFT=false               # --draft : compilación rápida sin imágenes
DIRECTORIO_SALIDA=""           # -o DIR : mueve el PDF al directorio indicado
USAR_BIBTEX=false              # -b : ejecuta bibtex/biber
USAR_BIBER=false               # --biber : usa biber en vez de bibtex
USAR_MAKEINDEX=false           # -i : ejecuta makeindex
USAR_MAKEGLOSSARIES=false      # -g : ejecuta makeglossaries
ABRIR_PDF=false                # -a : abre el PDF al terminar
VERBOSE=false                  # -v : muestra salida completa del compilador
LOG_FILE=""                    # ruta al log (por defecto: ARCHIVO.log)
TIEMPO_INICIO=$(date +%s)

# ──────────────────────────────────────────────────────────────────────────────
# FUNCIONES DE UTILIDAD
# ──────────────────────────────────────────────────────────────────────────────

# Imprime una línea divisoria
separador() {
    printf '%s\n' "$(printf '─%.0s' {1..62})"
}

# Imprime mensajes con prefijo y color
info()    { echo -e "${BLUE}ℹ${NC}  $*"; }
ok()      { echo -e "${GREEN}✔${NC}  $*"; }
warn()    { echo -e "${YELLOW}⚠${NC}  $*"; }
error()   { echo -e "${RED}✖${NC}  $*" >&2; }
paso()    { echo -e "${CYAN}→${NC}  $*"; }
titulo()  { echo -e "\n${BOLD}$*${NC}"; separador; }

# Tiempo transcurrido en segundos
elapsed() {
    echo $(( $(date +%s) - TIEMPO_INICIO ))
}

# ──────────────────────────────────────────────────────────────────────────────
# AYUDA
# ──────────────────────────────────────────────────────────────────────────────
mostrar_ayuda() {
    cat <<EOF

${BOLD}compilar_latex.sh${NC} — Script universal de compilación LaTeX v2.0.0

${BOLD}USO${NC}
  ./compilar_latex.sh [OPCIONES] [ARCHIVO]

${BOLD}ARGUMENTOS${NC}
  ARCHIVO          Nombre del archivo .tex sin extensión (por defecto: index)

${BOLD}OPCIONES DE COMPILACIÓN${NC}
  -e, --engine ENGINE   Motor LaTeX a usar:
                          pdflatex  (por defecto, el más compatible)
                          xelatex   (Unicode nativo, fuentes del sistema)
                          lualatex  (Lua integrado, máxima flexibilidad)
  -p, --pasadas N       Número de compilaciones (por defecto: 2)
                        Use 3 si tiene referencias cruzadas complejas
  --draft               Modo borrador: omite imágenes, más rápido

${BOLD}OPCIONES DE BIBLIOGRAFÍA E ÍNDICES${NC}
  -b, --bibtex          Ejecuta BibTeX entre compilaciones
  --biber               Ejecuta Biber (para biblatex) entre compilaciones
  -i, --makeindex       Ejecuta makeindex para índices temáticos
  -g, --makeglossaries  Ejecuta makeglossaries para glosarios

${BOLD}OPCIONES DE SALIDA${NC}
  -o, --output DIR      Mueve el PDF generado al directorio indicado
  -s, --silencioso      Suprime la salida del compilador (solo errores)
  -v, --verbose         Muestra la salida completa del compilador
  -a, --abrir           Abre el PDF automáticamente al terminar
  --log FILE            Guarda el log completo en FILE

${BOLD}UTILIDADES${NC}
  -c, --limpiar         Elimina archivos auxiliares y sale
  -w, --watch           Modo vigilancia: recompila cuando cambia el .tex
  -h, --help            Muestra esta ayuda

${BOLD}EJEMPLOS${NC}
  # Compilar index.tex con pdflatex (mínimo para empezar)
  ./compilar_latex.sh

  # Documento con fuentes del sistema y bibliografía (biblatex+biber)
  ./compilar_latex.sh -e xelatex --biber -p 3 tesis

  # Presentación Beamer con XeLaTeX
  ./compilar_latex.sh -e xelatex slides

  # LuaLaTeX con índice y glosario, abrir el resultado
  ./compilar_latex.sh -e lualatex -i -g -a libro

  # Modo watch para edición continua
  ./compilar_latex.sh -w -e pdflatex articulo

  # Compilar y guardar PDF en carpeta build/
  ./compilar_latex.sh -o build informe

${BOLD}ARCHIVOS AUXILIARES QUE SE LIMPIAN${NC}
  .aux .bbl .bcf .blg .fdb_latexmk .fls .glg .glo .gls
  .idx .ilg .ind .ist .lof .log .lot .nav .out .run.xml
  .snm .synctex.gz .toc .vrb .xdv

EOF
}

# ──────────────────────────────────────────────────────────────────────────────
# PARSEO DE ARGUMENTOS
# ──────────────────────────────────────────────────────────────────────────────
parsear_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -e|--engine)
                ENGINE="${2:?'--engine requiere un argumento: pdflatex|xelatex|lualatex'}"
                shift 2
                ;;
            -p|--pasadas)
                PASADAS="${2:?'--pasadas requiere un número'}"
                if ! [[ "$PASADAS" =~ ^[1-9][0-9]*$ ]]; then
                    error "--pasadas debe ser un entero positivo"
                    exit 1
                fi
                shift 2
                ;;
            -o|--output)
                DIRECTORIO_SALIDA="${2:?'--output requiere una ruta de directorio'}"
                shift 2
                ;;
            --log)
                LOG_FILE="${2:?'--log requiere una ruta de archivo'}"
                shift 2
                ;;
            -s|--silencioso)  MODO_SILENCIOSO=true;     shift ;;
            -v|--verbose)     VERBOSE=true;              shift ;;
            -c|--limpiar)     SOLO_LIMPIAR=true;         shift ;;
            -w|--watch)       MODO_WATCH=true;           shift ;;
            --draft)          MODO_DRAFT=true;           shift ;;
            -b|--bibtex)      USAR_BIBTEX=true;          shift ;;
            --biber)          USAR_BIBER=true;           shift ;;
            -i|--makeindex)   USAR_MAKEINDEX=true;       shift ;;
            -g|--makeglossaries) USAR_MAKEGLOSSARIES=true; shift ;;
            -a|--abrir)       ABRIR_PDF=true;            shift ;;
            -h|--help)        mostrar_ayuda; exit 0      ;;
            -*)
                error "Opción desconocida: $1"
                echo "  Usa --help para ver las opciones disponibles."
                exit 1
                ;;
            *)
                # Argumento posicional → nombre del archivo
                ARCHIVO="$1"
                shift
                ;;
        esac
    done

    # Validar motor
    case "$ENGINE" in
        pdflatex|xelatex|lualatex) ;;
        *)
            error "Motor no válido: '$ENGINE'. Usa pdflatex, xelatex o lualatex."
            exit 1
            ;;
    esac

    # Bibtex y biber son mutuamente excluyentes
    if $USAR_BIBTEX && $USAR_BIBER; then
        error "--bibtex y --biber son mutuamente excluyentes."
        exit 1
    fi

    # Ajustar pasadas automáticamente si se usa bibliografía/glosarios
    if ( $USAR_BIBTEX || $USAR_BIBER ) && [ "$PASADAS" -lt 3 ]; then
        PASADAS=3
        warn "Pasadas ajustadas a 3 para procesar bibliografía correctamente."
    fi

    # Log por defecto
    if [ -z "$LOG_FILE" ]; then
        LOG_FILE="${ARCHIVO}.log"
    fi
}

# ──────────────────────────────────────────────────────────────────────────────
# VERIFICAR DEPENDENCIAS
# ──────────────────────────────────────────────────────────────────────────────
verificar_dependencias() {
    local faltan=()

    # Motor principal
    if ! command -v "$ENGINE" &>/dev/null; then
        faltan+=("$ENGINE")
    fi

    # BibTeX / Biber
    $USAR_BIBTEX && ! command -v bibtex  &>/dev/null && faltan+=("bibtex")
    $USAR_BIBER  && ! command -v biber   &>/dev/null && faltan+=("biber")

    # makeindex / makeglossaries
    $USAR_MAKEINDEX      && ! command -v makeindex      &>/dev/null && faltan+=("makeindex")
    $USAR_MAKEGLOSSARIES && ! command -v makeglossaries &>/dev/null && faltan+=("makeglossaries")

    # pdfinfo (opcional, para mostrar metadata)
    if ! command -v pdfinfo &>/dev/null; then
        warn "pdfinfo no encontrado (poppler-utils). No se mostrará metadata del PDF."
    fi

    # inotifywait (solo en modo watch)
    if $MODO_WATCH && ! command -v inotifywait &>/dev/null; then
        error "inotifywait no encontrado. Instala inotify-tools:"
        echo "  sudo apt install inotify-tools   # Debian/Ubuntu"
        echo "  sudo dnf install inotify-tools   # Fedora"
        echo "  brew install fswatch             # macOS (usando fswatch)"
        exit 1
    fi

    if [ ${#faltan[@]} -gt 0 ]; then
        error "Las siguientes herramientas no están instaladas: ${faltan[*]}"
        echo ""
        echo "  Instala una distribución TeX completa:"
        echo "  sudo apt install texlive-full      # Debian/Ubuntu"
        echo "  sudo dnf install texlive-scheme-full  # Fedora"
        echo "  brew install --cask mactex         # macOS"
        exit 1
    fi
}

# ──────────────────────────────────────────────────────────────────────────────
# VERIFICAR QUE EXISTE EL ARCHIVO .tex
# ──────────────────────────────────────────────────────────────────────────────
verificar_archivo() {
    if [ ! -f "${ARCHIVO}.tex" ]; then
        error "No se encontró el archivo: ${ARCHIVO}.tex"
        echo ""
        echo "  Archivos .tex en el directorio actual:"
        local encontrados
        encontrados=$(find . -maxdepth 1 -name '*.tex' -printf '    %f\n' 2>/dev/null || true)
        if [ -n "$encontrados" ]; then
            echo "$encontrados"
        else
            echo "    (ninguno)"
        fi
        exit 1
    fi
}

# ──────────────────────────────────────────────────────────────────────────────
# CONSTRUIR FLAGS DEL COMPILADOR
# ──────────────────────────────────────────────────────────────────────────────
construir_flags() {
    FLAGS=(-interaction=nonstopmode -halt-on-error)

    # Modo draft (más rápido, sin imágenes embebidas)
    $MODO_DRAFT && FLAGS+=(-draftmode)

    # XeLaTeX puede generar .xdv intermedio; con -no-pdf lo evitamos en draft
    if [ "$ENGINE" = "xelatex" ] && $MODO_DRAFT; then
        FLAGS+=(-no-pdf)
    fi

    # SyncTeX para editores con previsualización (evitar en draft para rapidez)
    if ! $MODO_DRAFT; then
        FLAGS+=(-synctex=1)
    fi

    echo "${FLAGS[@]}"
}

# ──────────────────────────────────────────────────────────────────────────────
# EJECUTAR MOTOR LATEX
# ──────────────────────────────────────────────────────────────────────────────
ejecutar_latex() {
    local num_pasada="$1"
    local flags
    read -ra flags <<< "$(construir_flags)"

    paso "Pasada ${num_pasada}/${PASADAS} con ${ENGINE}..."

    local cmd=("$ENGINE" "${flags[@]}" "${ARCHIVO}.tex")

    if $VERBOSE; then
        # Salida completa del compilador
        "${cmd[@]}" 2>&1 | tee -a "$LOG_FILE"
        local status=${PIPESTATUS[0]}
    elif $MODO_SILENCIOSO; then
        # Solo guardar en log, nada en pantalla
        "${cmd[@]}" >> "$LOG_FILE" 2>&1
        local status=$?
    else
        # Filtrar líneas relevantes (errores y advertencias)
        "${cmd[@]}" 2>&1 | tee -a "$LOG_FILE" | \
            grep -E --color=never \
                '(^!|Warning|Error|Overfull|Underfull|LaTeX Font|Package|Class)' \
            || true
        local status=${PIPESTATUS[0]}
    fi

    if [ "$status" -ne 0 ]; then
        error "El compilador terminó con errores en la pasada ${num_pasada}."
        mostrar_errores_log
        exit 1
    fi
}

# ──────────────────────────────────────────────────────────────────────────────
# EJECUTAR BIBTEX / BIBER
# ──────────────────────────────────────────────────────────────────────────────
ejecutar_bibliografia() {
    if $USAR_BIBTEX; then
        paso "Ejecutando BibTeX..."
        if $MODO_SILENCIOSO; then
            bibtex "$ARCHIVO" >> "$LOG_FILE" 2>&1 || {
                warn "BibTeX reportó advertencias (revisa ${ARCHIVO}.blg)"
            }
        else
            bibtex "$ARCHIVO" 2>&1 | tee -a "$LOG_FILE" || {
                warn "BibTeX reportó advertencias (revisa ${ARCHIVO}.blg)"
            }
        fi
    fi

    if $USAR_BIBER; then
        paso "Ejecutando Biber..."
        if $MODO_SILENCIOSO; then
            biber "$ARCHIVO" >> "$LOG_FILE" 2>&1 || {
                warn "Biber reportó advertencias (revisa ${ARCHIVO}.blg)"
            }
        else
            biber "$ARCHIVO" 2>&1 | tee -a "$LOG_FILE" || {
                warn "Biber reportó advertencias (revisa ${ARCHIVO}.blg)"
            }
        fi
    fi
}

# ──────────────────────────────────────────────────────────────────────────────
# EJECUTAR MAKEINDEX
# ──────────────────────────────────────────────────────────────────────────────
ejecutar_indices() {
    if $USAR_MAKEINDEX; then
        paso "Ejecutando makeindex..."
        makeindex "$ARCHIVO" >> "$LOG_FILE" 2>&1 || \
            warn "makeindex reportó advertencias."
    fi

    if $USAR_MAKEGLOSSARIES; then
        paso "Ejecutando makeglossaries..."
        makeglossaries "$ARCHIVO" >> "$LOG_FILE" 2>&1 || \
            warn "makeglossaries reportó advertencias."
    fi
}

# ──────────────────────────────────────────────────────────────────────────────
# MOSTRAR ERRORES DEL LOG
# ──────────────────────────────────────────────────────────────────────────────
mostrar_errores_log() {
    echo ""
    warn "Extracto de errores del log (${ARCHIVO}.log):"
    separador
    # Mostrar bloques de error con contexto
    grep -n -A 3 '^!' "${ARCHIVO}.log" 2>/dev/null | head -40 || \
        echo "  (No se pudo leer el log)"
    separador
    echo "  Log completo: ${ARCHIVO}.log"
}

# ──────────────────────────────────────────────────────────────────────────────
# LIMPIAR ARCHIVOS AUXILIARES
# ──────────────────────────────────────────────────────────────────────────────
limpiar_auxiliares() {
    local extensiones=(
        aux bbl bcf blg fdb_latexmk fls glg glo gls
        idx ilg ind ist lof log lot nav out run.xml
        snm synctex.gz toc vrb xdv
    )

    paso "Eliminando archivos auxiliares..."
    local eliminados=0
    for ext in "${extensiones[@]}"; do
        local archivo="${ARCHIVO}.${ext}"
        if [ -f "$archivo" ]; then
            rm -f "$archivo"
            (( eliminados++ )) || true
        fi
    done

    # Limpiar también *.aux de subdirectorios (para proyectos con \include)
    find . -name '*.aux' -not -path './.git/*' -delete 2>/dev/null || true

    ok "Eliminados ${eliminados} archivo(s) auxiliar(es)."
}

# ──────────────────────────────────────────────────────────────────────────────
# MOSTRAR INFORMACIÓN DEL PDF GENERADO
# ──────────────────────────────────────────────────────────────────────────────
mostrar_info_pdf() {
    local pdf="${ARCHIVO}.pdf"

    if [ ! -f "$pdf" ]; then
        error "No se encontró ${pdf} después de la compilación."
        exit 1
    fi

    ok "PDF generado: ${BOLD}${pdf}${NC}"

    # Tamaño del archivo
    local tamanio
    tamanio=$(du -h "$pdf" | cut -f1)
    info "Tamaño: ${tamanio}"

    # Número de páginas (requiere poppler-utils)
    if command -v pdfinfo &>/dev/null; then
        local paginas
        paginas=$(pdfinfo "$pdf" 2>/dev/null | grep -i '^Pages:' | awk '{print $2}' || echo "?")
        info "Páginas: ${paginas}"

        # Otras propiedades útiles
        local titulo autor
        titulo=$(pdfinfo "$pdf" 2>/dev/null | grep -i '^Title:' | sed 's/^Title:\s*//' || echo "")
        autor=$(pdfinfo "$pdf"  2>/dev/null | grep -i '^Author:'| sed 's/^Author:\s*//'  || echo "")
        [ -n "$titulo" ] && info "Título: ${titulo}"
        [ -n "$autor"  ] && info "Autor : ${autor}"
    fi

    # Tiempo total
    info "Tiempo: $(elapsed) segundo(s)"
}

# ──────────────────────────────────────────────────────────────────────────────
# MOVER PDF A DIRECTORIO DE SALIDA
# ──────────────────────────────────────────────────────────────────────────────
mover_pdf() {
    if [ -n "$DIRECTORIO_SALIDA" ]; then
        mkdir -p "$DIRECTORIO_SALIDA"
        mv "${ARCHIVO}.pdf" "${DIRECTORIO_SALIDA}/${ARCHIVO}.pdf"
        ok "PDF movido a: ${DIRECTORIO_SALIDA}/${ARCHIVO}.pdf"
    fi
}

# ──────────────────────────────────────────────────────────────────────────────
# ABRIR PDF
# ──────────────────────────────────────────────────────────────────────────────
abrir_pdf() {
    if ! $ABRIR_PDF; then return; fi

    local pdf
    if [ -n "$DIRECTORIO_SALIDA" ]; then
        pdf="${DIRECTORIO_SALIDA}/${ARCHIVO}.pdf"
    else
        pdf="${ARCHIVO}.pdf"
    fi

    paso "Abriendo ${pdf}..."

    # Detectar visor disponible (Linux / macOS)
    local visor=""
    for v in evince okular zathura atril xpdf mupdf xdg-open open; do
        if command -v "$v" &>/dev/null; then
            visor="$v"
            break
        fi
    done

    if [ -n "$visor" ]; then
        "$visor" "$pdf" &
        ok "PDF abierto con ${visor}."
    else
        warn "No se encontró un visor de PDF. Abre manualmente: ${pdf}"
    fi
}

# ──────────────────────────────────────────────────────────────────────────────
# FLUJO PRINCIPAL DE COMPILACIÓN
# ──────────────────────────────────────────────────────────────────────────────
compilar() {
    # Limpiar log anterior
    > "$LOG_FILE"

    titulo "Compilando: ${ARCHIVO}.tex  [engine: ${ENGINE}]"

    # Mostrar configuración activa
    info "Pasadas     : ${PASADAS}"
    $MODO_DRAFT         && info "Modo        : borrador (draft)"
    $USAR_BIBTEX        && info "Bibliografía: BibTeX"
    $USAR_BIBER         && info "Bibliografía: Biber"
    $USAR_MAKEINDEX     && info "Índice      : makeindex"
    $USAR_MAKEGLOSSARIES && info "Glosario    : makeglossaries"
    [ -n "$DIRECTORIO_SALIDA" ] && info "Salida      : ${DIRECTORIO_SALIDA}/"
    echo ""

    # ── Pasada 1: siempre primera compilación ──────────────────────────────
    ejecutar_latex 1

    # ── Bibliografía (después de la primera pasada) ────────────────────────
    if ( $USAR_BIBTEX || $USAR_BIBER ) && [ "$PASADAS" -ge 2 ]; then
        ejecutar_bibliografia
    fi

    # ── Índices / glosarios (después de la primera pasada) ────────────────
    if ( $USAR_MAKEINDEX || $USAR_MAKEGLOSSARIES ) && [ "$PASADAS" -ge 2 ]; then
        ejecutar_indices
    fi

    # ── Pasadas adicionales ────────────────────────────────────────────────
    for (( p=2; p<=PASADAS; p++ )); do
        ejecutar_latex "$p"
    done

    # ── Resultado ─────────────────────────────────────────────────────────
    separador
    mostrar_info_pdf
    mover_pdf
    abrir_pdf

    separador
    ok "¡Compilación completada exitosamente!"
    separador

    # Sugerencia de visores
    if ! $ABRIR_PDF; then
        local pdf="${DIRECTORIO_SALIDA:+${DIRECTORIO_SALIDA}/}${ARCHIVO}.pdf"
        echo -e "\n${DIM}Para abrir el PDF:${NC}"
        echo -e "  ${DIM}evince ${pdf} &${NC}"
        echo -e "  ${DIM}okular ${pdf} &${NC}"
        echo -e "  ${DIM}zathura ${pdf} &${NC}"
    fi
    echo ""
}

# ──────────────────────────────────────────────────────────────────────────────
# MODO WATCH (recompila cuando cambia el .tex o archivos .bib/.sty incluidos)
# ──────────────────────────────────────────────────────────────────────────────
modo_watch() {
    info "Modo watch activado. Vigilando cambios en *.tex *.bib *.sty *.cls"
    info "Presiona Ctrl+C para salir."
    echo ""

    # Primera compilación inmediata
    compilar_segura

    # Detectar sistema operativo para usar la herramienta correcta
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS: usar fswatch
        if ! command -v fswatch &>/dev/null; then
            error "fswatch no encontrado en macOS."
            echo "  brew install fswatch"
            exit 1
        fi
        fswatch -0 --event Updated --include '.*\.(tex|bib|sty|cls)$' . | \
        while IFS= read -r -d '' _; do
            echo ""
            info "Cambio detectado. Recompilando..."
            TIEMPO_INICIO=$(date +%s)
            compilar_segura
        done
    else
        # Linux: usar inotifywait
        while inotifywait -q -e close_write,moved_to \
            --include '.*\.(tex|bib|sty|cls)$' . 2>/dev/null; do
            echo ""
            info "Cambio detectado. Recompilando..."
            TIEMPO_INICIO=$(date +%s)
            compilar_segura
        done
    fi
}

# Compilación sin salir ante error (para modo watch)
compilar_segura() {
    compilar || {
        error "La compilación falló. Esperando cambios para reintentar..."
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# BANNER
# ──────────────────────────────────────────────────────────────────────────────
banner() {
    echo -e "${BOLD}"
    echo "  ██╗      █████╗ ████████╗███████╗██╗  ██╗"
    echo "  ██║     ██╔══██╗╚══██╔══╝██╔════╝╚██╗██╔╝"
    echo "  ██║     ███████║   ██║   █████╗   ╚███╔╝ "
    echo "  ██║     ██╔══██║   ██║   ██╔══╝   ██╔██╗ "
    echo "  ███████╗██║  ██║   ██║   ███████╗██╔╝ ██╗"
    echo "  ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝"
    echo -e "  ${DIM}compilar_latex.sh v2.0.0 — Universal LaTeX Builder${NC}"
    echo ""
}

# ──────────────────────────────────────────────────────────────────────────────
# PUNTO DE ENTRADA
# ──────────────────────────────────────────────────────────────────────────────
main() {
    banner
    parsear_args "$@"
    verificar_dependencias

    # Modo solo-limpiar: no necesita verificar el .tex
    if $SOLO_LIMPIAR; then
        titulo "Limpieza de archivos auxiliares"
        limpiar_auxiliares
        exit 0
    fi

    verificar_archivo

    if $MODO_WATCH; then
        modo_watch
    else
        compilar
        limpiar_auxiliares
    fi
}

main "$@"
