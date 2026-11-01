#!/usr/bin/env bash
# install.sh — instala LaTeX Studio: su acceso directo en el menú de aplicaciones, con su icono (gui_comun.lanzador).
# Uso: ./install.sh [-n]        instala (con -n, solo dice qué escribiría)
#      ./install.sh --quitar    quita el acceso directo y su icono
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-$(command -v python3)}"
if [[ "${1:-}" == "--quitar" ]]; then
    shift
    exec "$PYTHON" "$DIR/studio/main.py" --quitar-lanzador "$@"
fi
exec "$PYTHON" "$DIR/studio/main.py" --instalar-lanzador "$@"
