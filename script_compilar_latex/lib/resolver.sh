#!/usr/bin/env bash
# ==============================================================================
# lib/resolver.sh — Resolución de rutas del archivo .tex de entrada
# Proyecto: compilar_latex
# ==============================================================================
# El script siempre vive en:
#   /home/achalmaedison/Documents/scripts_for_latex/script_compilar_latex/
#
# Los archivos .tex pueden estar en cualquier ruta bajo ~/Documents:
#   pub_dialectica-y-mercado/capitulo1.tex
#   /home/achalmaedison/Documents/03 writing/articulo.tex
#   tesis                                          ← relativo al CWD del usuario
#
# Esta función resuelve la ruta y expone tres variables globales:
#   TEX_DIR   → directorio absoluto donde vive el .tex
#   TEX_BASE  → nombre sin extensión (ej: "capitulo1")
#   TEX_PATH  → ruta absoluta completa al .tex (ej: /home/.../capitulo1.tex)
#
# Estrategia de resolución (en orden):
#   1. Ruta absoluta o relativa con .tex explícito → usar tal cual
#   2. Ruta sin .tex → intentar añadir .tex
#   3. Solo nombre base → buscar desde el CWD del usuario (PWD al invocar main.sh)
#
# Variables globales que debe exponer:
#   TEX_DIR   TEX_BASE   TEX_PATH
#   ARCHIVO_BASE  (alias de TEX_BASE, para compatibilidad con el resto del código)
#   ARCHIVO_DIR   (alias de TEX_DIR)

# resolver_ruta_tex()
# Recibe el argumento tal como lo escribió el usuario y resuelve la ruta real.
#
# Arguments:
#   $1 - Valor de ARCHIVO (puede ser ruta absoluta, relativa, o solo el nombre base)
#   $2 - CWD original del usuario (guardado antes de cualquier cd)
#
# Sets (global):
#   TEX_PATH TEX_DIR TEX_BASE ARCHIVO_BASE ARCHIVO_DIR
#
# Returns:
#   0 si el archivo se encontró
#   1 si no se encontró (el llamador debe hacer exit)
resolver_ruta_tex() {
    local input="$1"
    local user_cwd="$2"
    local candidato=""

    # Quitar extensión .tex si el usuario la escribió (normalizamos internamente)
    input="${input%.tex}"

    # Caso 1: la entrada ya contiene un separador → tiene estructura de ruta
    if [[ "$input" == */* ]]; then
        # Puede ser absoluta (/home/...) o relativa (../pub_dialectica/capitulo)
        if [[ "$input" == /* ]]; then
            # Absoluta: usar directamente
            candidato="${input}.tex"
        else
            # Relativa: resolver desde el CWD del usuario
            candidato="${user_cwd}/${input}.tex"
        fi
    else
        # Caso 2: solo nombre base → buscar primero en el CWD del usuario
        candidato="${user_cwd}/${input}.tex"
    fi

    # Resolver .. y symlinks para obtener una ruta canónica
    # realpath -m: resuelve sin requerir que el archivo exista aún
    # (el error lo lanzamos nosotros con mensaje claro)
    local ruta_absoluta
    if command -v realpath &>/dev/null; then
        ruta_absoluta="$(realpath -m "$candidato" 2>/dev/null || echo "$candidato")"
    else
        # Fallback para sistemas sin realpath (macOS sin coreutils)
        ruta_absoluta="$(cd "$(dirname "$candidato")" 2>/dev/null && \
                         pwd)/$(basename "$candidato")" || ruta_absoluta="$candidato"
    fi

    # Verificar existencia
    if [ ! -f "$ruta_absoluta" ]; then
        return 1
    fi

    # Exportar las tres variables que usa el resto del script
    TEX_PATH="$ruta_absoluta"
    TEX_DIR="$(dirname "$ruta_absoluta")"
    TEX_BASE="$(basename "$ruta_absoluta" .tex)"

    # Alias de compatibilidad
    ARCHIVO_DIR="$TEX_DIR"
    ARCHIVO_BASE="$TEX_BASE"

    return 0
}

# sugerir_tex_cercanos()
# Cuando el archivo no se encuentra, muestra candidatos .tex cercanos
# para ayudar al usuario a identificar el problema.
#
# Arguments:
#   $1 - input original del usuario
#   $2 - CWD del usuario
#
# Returns: siempre 0 (solo imprime sugerencias)
sugerir_tex_cercanos() {
    local input="$1"
    local user_cwd="$2"

    echo ""
    echo "  Archivos .tex encontrados en el directorio indicado:"

    local dir_busqueda
    if [[ "$input" == */* ]]; then
        dir_busqueda="$(dirname "${user_cwd}/${input}")"
    else
        dir_busqueda="$user_cwd"
    fi

    local encontrados
    encontrados=$(find "$dir_busqueda" -maxdepth 2 -name '*.tex' 2>/dev/null \
                  | head -10 \
                  | sed "s|^|    |")

    if [ -n "$encontrados" ]; then
        echo "$encontrados"
    else
        echo "    (ninguno en ${dir_busqueda})"
    fi
    echo ""
    echo "  Uso con ruta completa:"
    echo "    ./compilar_latex.sh /ruta/absoluta/al/archivo"
    echo "    ./compilar_latex.sh ../pub_dialectica-y-mercado/capitulo1"
    echo "    ./compilar_latex.sh ~/Documents/03\ writing/articulo"
}
