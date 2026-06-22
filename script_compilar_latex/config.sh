#!/usr/bin/env bash
# ==============================================================================
# config.sh — Configuración centralizada y valores por defecto
# Proyecto: compilar_latex
# Autor   : Edison Achalma
# Versión : 3.0.0
# ==============================================================================
# Todos los valores modificables del script viven aquí.
# Cambiar un default en este archivo afecta todo el proyecto.

# ── Versión ───────────────────────────────────────────────────────────────────
readonly VERSION="3.0.0"
readonly SCRIPT_NAME="compilar_latex"

# ── Defaults de compilación ───────────────────────────────────────────────────
# Nombre del .tex sin extensión, o ruta absoluta/relativa al .tex.
# Se sobreescribe por el argumento posicional de la CLI.
DEFAULT_ARCHIVO="index"

# Motor LaTeX: pdflatex | xelatex | lualatex
# "auto" → el script detecta automáticamente (ver lib/detector.sh)
DEFAULT_ENGINE="auto"

# Número mínimo de pasadas de compilación.
# Se incrementa automáticamente si se activa bibliografía o glosarios.
DEFAULT_PASADAS=2

# ── Extensiones de archivos auxiliares que se eliminan tras compilar ──────────
# Modificar aquí si tu flujo genera extensiones adicionales.
readonly EXTENSIONES_AUXILIARES=(
    aux bbl bcf blg fdb_latexmk fls glg glo gls
    idx ilg ind ist lof log lot nav out run.xml
    snm synctex.gz toc vrb xdv ptc
)

# ── Visores PDF detectados en orden de preferencia ───────────────────────────
# El primero disponible en el sistema es el que se usa.
readonly VISORES_PDF=(evince okular zathura atril xpdf mupdf xdg-open open)

# ── Colores ───────────────────────────────────────────────────────────────────
# Se inicializan aquí; se anulan a "" si el terminal no soporta colores
# o si NO_COLOR=1 está en el entorno (estándar https://no-color.org).
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Deshabilitar colores si el terminal no los soporta o NO_COLOR está activo
_init_colores() {
    if ! tput colors &>/dev/null 2>&1 || [ "${NO_COLOR:-}" = "1" ]; then
        RED='' GREEN='' YELLOW='' BLUE='' CYAN='' BOLD='' DIM='' NC=''
    fi
}
