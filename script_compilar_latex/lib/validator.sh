#!/usr/bin/env bash
# ==============================================================================
# lib/validator.sh — Validación de argumentos y dependencias del sistema
# Proyecto: compilar_latex
# ==============================================================================

# validar_engine()
# Verifica que el motor indicado sea uno de los valores permitidos.
#
# Arguments:
#   $1 - Nombre del motor a validar
#
# Returns:
#   0 si es válido
#   1 si no lo es (imprime mensaje de error)
validar_engine() {
    local engine="$1"
    case "$engine" in
        pdflatex|xelatex|lualatex|auto) return 0 ;;
        *)
            error "Motor no válido: '${engine}'."
            echo "  Opciones válidas: pdflatex · xelatex · lualatex"
            echo "  Omite --engine para detección automática."
            return 1
            ;;
    esac
}

# validar_pasadas()
# Verifica que el número de pasadas sea un entero positivo.
#
# Arguments:
#   $1 - Valor a validar
#
# Returns:
#   0 si es válido, 1 si no
validar_pasadas() {
    local n="$1"
    if ! [[ "$n" =~ ^[1-9][0-9]*$ ]]; then
        error "--pasadas debe ser un entero positivo (recibido: '${n}')."
        return 1
    fi
    return 0
}

# verificar_dependencias()
# Comprueba que todos los binarios requeridos estén instalados.
# Los opcionales solo emiten warn, no detienen la ejecución.
#
# Globals leídas:
#   ENGINE USAR_BIBTEX USAR_BIBER USAR_MAKEINDEX USAR_MAKEGLOSSARIES MODO_WATCH
#
# Returns:
#   0 si todas las dependencias obligatorias están presentes
#   Exits 1 si falta alguna obligatoria
verificar_dependencias() {
    local faltan=()

    # Motor principal (puede ser "auto" aún si se llama antes de detectar)
    if [ "$ENGINE" != "auto" ] && ! command -v "$ENGINE" &>/dev/null; then
        faltan+=("$ENGINE")
    fi

    # Herramientas de bibliografía
    $USAR_BIBTEX && ! command -v bibtex  &>/dev/null && faltan+=("bibtex")
    $USAR_BIBER  && ! command -v biber   &>/dev/null && faltan+=("biber")

    # Herramientas de índices y glosarios
    $USAR_MAKEINDEX      && ! command -v makeindex      &>/dev/null \
        && faltan+=("makeindex")
    $USAR_MAKEGLOSSARIES && ! command -v makeglossaries &>/dev/null \
        && faltan+=("makeglossaries")

    # Opcionales — solo advertir
    if ! command -v pdfinfo &>/dev/null; then
        warn "pdfinfo no encontrado (instala poppler-utils). No se mostrará metadata del PDF."
    fi

    # inotifywait: solo requerido en modo watch en Linux
    if $MODO_WATCH && [[ "$OSTYPE" != "darwin"* ]]; then
        if ! command -v inotifywait &>/dev/null; then
            faltan+=("inotifywait (paquete: inotify-tools)")
        fi
    fi

    # fswatch: solo requerido en modo watch en macOS
    if $MODO_WATCH && [[ "$OSTYPE" == "darwin"* ]]; then
        if ! command -v fswatch &>/dev/null; then
            faltan+=("fswatch")
        fi
    fi

    if [ ${#faltan[@]} -gt 0 ]; then
        error "Herramientas no instaladas: ${faltan[*]}"
        echo ""
        echo "  Para instalar LaTeX completo:"
        echo "    sudo pacman -S texlive-most         # Arch / Archcraft / Manjaro"
        echo "    sudo apt install texlive-full        # Debian / Ubuntu / Kubuntu"
        echo "    sudo dnf install texlive-scheme-full # Fedora / RHEL"
        echo "    brew install --cask mactex           # macOS"
        echo ""
        echo "  Para modo watch:"
        echo "    sudo pacman -S inotify-tools         # Arch Linux"
        echo "    sudo apt install inotify-tools        # Debian/Ubuntu"
        echo "    brew install fswatch                  # macOS"
        exit 1
    fi
}
