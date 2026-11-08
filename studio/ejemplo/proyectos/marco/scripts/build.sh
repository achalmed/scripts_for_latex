#!/usr/bin/env bash
# scripts/build.sh — el compilador del marco de muestra: LuaLaTeX con las clases del marco en TEXINPUTS y los
# auxiliares en <proyecto>/.build/ (como el de un marco real); --clean los borra. Produce dos versiones de un mismo
# .tex (como docencia): la completa (<job>.pdf) y el resumen (<job>-resumen.pdf, opción de clase «resumen»), la que pida
# --version o, sin ella, la que declare el documento («% !VERSION = resumen»).
set -euo pipefail
CFG_TEX_ENGINE="${CFG_TEX_ENGINE:-lualatex}"
CFG_BUILD_DIR=".build"
fw="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ "${1:-}" = "--clean" ] && { shift; rm -rf -- "$(dirname "$1")/$CFG_BUILD_DIR"; exit 0; }
maestro="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; shift
version=""
[ "${1:-}" = "--version" ] && version="${2:-}"
[ -n "$version" ] || version="$(head -n 30 "$maestro" | sed -nE 's/^[[:space:]]*%[[:space:]]*![[:space:]]*VERSION[[:space:]]*=[[:space:]]*([[:alnum:]]+).*/\1/Ip' | head -n 1)"
version="${version,,}"; version="${version:-completa}"
cd "$(dirname "$maestro")"; job="$(basename "$maestro" .tex)"; salida="$job"; previo=""
case "$version" in
  completa) ;;
  resumen) salida="$job-resumen"; previo="\\PassOptionsToClass{resumen}{memoria}" ;;
  *) echo "versión no válida: $version (completa|resumen)"; exit 2 ;;
esac
mkdir -p "$CFG_BUILD_DIR"
export TEXINPUTS=".:$fw/classes//:${TEXINPUTS:-}"
for i in 1 2; do
  echo "lualatex ($i/2) · $version"
  "$CFG_TEX_ENGINE" -interaction=nonstopmode -halt-on-error -synctex=1 -output-directory="$CFG_BUILD_DIR" \
    -jobname "$salida" "$previo\\input{$job.tex}" >/dev/null || { echo "error: $CFG_BUILD_DIR/$salida.log"; exit 1; }
done
cp -f "$CFG_BUILD_DIR/$salida.pdf" "./$salida.pdf"
echo "Listo: $salida.pdf"
