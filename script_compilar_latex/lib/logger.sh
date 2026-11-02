#!/usr/bin/env bash
# latex-studio/script_compilar_latex/lib/logger.sh — envoltorio (FS2, 2026-09-07): el logger vive en core/shell-lib/logger.sh; aquí solo lo propio de esta suite.
_core_d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; while [ "$_core_d" != / ] && [ ! -f "$_core_d/core/shell-lib/logger.sh" ]; do _core_d="$(dirname "$_core_d")"; done
# fuera del espacio de trabajo (un worktree, una copia de pruebas) vale CORE_DIR de core/env.sh, si se exportó
[ -f "$_core_d/core/shell-lib/logger.sh" ] || { [ -n "${CORE_DIR:-}" ] && [ -f "$CORE_DIR/shell-lib/logger.sh" ] && _core_d="$(dirname "$CORE_DIR")"; }
[ -f "$_core_d/core/shell-lib/logger.sh" ] || { echo "[ERROR] no encuentro core/shell-lib/logger.sh subiendo desde ${BASH_SOURCE[0]}" >&2; exit 1; }
LOG_FORMATO="${LOG_FORMATO:-corto}"   # herramienta interactiva: icono + mensaje, sin hora
source "$_core_d/core/shell-lib/logger.sh"; unset _core_d

# propio de compilar_latex: nombres cortos en español (los colores RED…NC los define config.sh; si están vacíos, sin color)
[ -z "${NC:-}" ] && desactivar_colores
separador() { log_separator "─" 64; }
info()      { log_info "$@"; }
ok()        { log_ok "$@"; }
warn()      { log_warn "$@"; }
error()     { log_error "$@"; }
paso()      { log_step "$@"; }
titulo()    { echo -e "\n${BOLD}$*${NC}"; separador; }
dim()       { echo -e "${DIM}  $*${NC}"; }
