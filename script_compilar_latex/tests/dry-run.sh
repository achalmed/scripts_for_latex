#!/usr/bin/env bash
# tests/dry-run.sh — prueba de suite: --dry-run, -c --dry-run y --help no escriben nada; una opción desconocida sale ≠ 0 (RQ-COD-02, RQ-COD-03).
# Uso: script_compilar_latex/tests/dry-run.sh   (sale 0 si todo pasa; necesita lualatex y biber instalados)
# Método: un .tex mínimo y auxiliares falsos en una carpeta temporal; TMPDIR apunta dentro de ella para
# que un temporal creado por error también se vea; se compara la huella (ruta, tamaño, mtime) antes y después.
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN="$AQUI/../main.sh"
d="$(mktemp -d)"
limpiar() { rm -f -- "$d"/a.tex "$d"/a.aux "$d"/a.log; rmdir -- "$d/tmp" "$d" 2>/dev/null || true; }
trap limpiar EXIT
mkdir -- "$d/tmp"
printf '\\documentclass{article}\\begin{document}Hola\\end{document}\n' > "$d/a.tex"
printf '\\relax\n' > "$d/a.aux"
printf 'log anterior\n' > "$d/a.log"

huella() { (cd "$d" && find . -printf '%p %s %T@\n' | LC_ALL=C sort); }
fallos=0
casos=0
caso() {                                   # caso <nombre> <0|distinto> <argumentos…>
    local nombre="$1" espera="$2" antes despues rc=0
    shift 2
    casos=$((casos + 1))
    antes="$(huella)"
    TMPDIR="$d/tmp" NO_COLOR=1 "$MAIN" "$@" > /dev/null 2>&1 || rc=$?
    despues="$(huella)"
    if [ "$antes" != "$despues" ]; then
        echo "  ✗ $nombre: escribió o borró en la carpeta de prueba"; fallos=$((fallos + 1))
    elif [ "$espera" = 0 ] && [ "$rc" -ne 0 ]; then
        echo "  ✗ $nombre: salió con $rc"; fallos=$((fallos + 1))
    elif [ "$espera" = distinto ] && [ "$rc" -eq 0 ]; then
        echo "  ✗ $nombre: salió con 0"; fallos=$((fallos + 1))
    else
        echo "  ✓ $nombre (salida $rc, nada escrito)"
    fi
}

caso "--dry-run con Biber"   0        --dry-run -e lualatex --biber "$d/a"
caso "-c --dry-run"          0        -c --dry-run "$d/a"
caso "--help"                0        --help
caso "opción desconocida"    distinto --no-existe "$d/a"

[ "$fallos" -eq 0 ] && echo "[dry-run] $casos casos en verde" || { echo "[dry-run] $fallos caso(s) fallaron"; exit 1; }
