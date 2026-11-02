#!/usr/bin/env bash
# scripts/build.sh — el compilador del marco de muestra: LuaLaTeX con las clases del marco en TEXINPUTS y los
# auxiliares en <proyecto>/.build/ (como el de un marco real); --clean los borra.
set -euo pipefail
CFG_TEX_ENGINE="${CFG_TEX_ENGINE:-lualatex}"
CFG_BUILD_DIR=".build"
fw="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ "${1:-}" = "--clean" ] && { shift; rm -rf -- "$(dirname "$1")/$CFG_BUILD_DIR"; exit 0; }
maestro="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
cd "$(dirname "$maestro")"; job="$(basename "$maestro" .tex)"
mkdir -p "$CFG_BUILD_DIR"
export TEXINPUTS=".:$fw/classes//:${TEXINPUTS:-}"
for i in 1 2; do
  echo "lualatex ($i/2)"
  "$CFG_TEX_ENGINE" -interaction=nonstopmode -halt-on-error -synctex=1 -output-directory="$CFG_BUILD_DIR" "$job.tex" >/dev/null || { echo "error: $CFG_BUILD_DIR/$job.log"; exit 1; }
done
cp -f "$CFG_BUILD_DIR/$job.pdf" "./$job.pdf"
echo "Listo: $job.pdf"
