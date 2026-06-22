#!/usr/bin/env bash
# ==============================================================================
# lib/logger.sh — Sistema de logging centralizado
# Proyecto: compilar_latex
# ==============================================================================
# Todas las salidas al usuario pasan por estas funciones para garantizar
# formato consistente y poder redirigirlas o silenciarlas desde un solo lugar.
#
# Niveles disponibles:
#   info  → información general del proceso        (azul)
#   ok    → confirmación de paso exitoso           (verde)
#   warn  → advertencia no fatal                   (amarillo)
#   error → error que detiene la ejecución         (rojo, stderr)
#   paso  → acción puntual en curso                (cyan)
#   titulo → encabezado de sección                 (negrita)
#   separador → línea divisoria visual
#   dim   → texto secundario / sugerencias         (atenuado)

separador() {
    printf '%s\n' "$(printf '─%.0s' {1..64})"
}

info()      { echo -e "${BLUE}ℹ${NC}  $*"; }
ok()        { echo -e "${GREEN}✔${NC}  $*"; }
warn()      { echo -e "${YELLOW}⚠${NC}  $*" >&2; }
error()     { echo -e "${RED}✖${NC}  $*" >&2; }
paso()      { echo -e "${CYAN}→${NC}  $*"; }
titulo()    { echo -e "\n${BOLD}$*${NC}"; separador; }
dim()       { echo -e "${DIM}  $*${NC}"; }
