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

# P9: --help y --version salen sin el banner
casos=$((casos + 1))
if NO_COLOR=1 "$MAIN" --help 2>&1 | grep -q "Universal LaTeX Builder" || NO_COLOR=1 "$MAIN" --version 2>&1 | grep -q "Universal LaTeX Builder"; then
    echo "  ✗ --help/--version: imprimen el banner"; fallos=$((fallos + 1))
else
    echo "  ✓ --help y --version sin banner"
fi

# P17: un archivo que no existe, con ruta absoluta: lista los .tex de SU carpeta (y no corta antes de listar)
casos=$((casos + 1))
salida="$(TMPDIR="$d/tmp" NO_COLOR=1 "$MAIN" "$d/no-existe" 2>&1)" && rc=0 || rc=$?
if [ "$rc" -eq 1 ] && grep -q "$d/a.tex" <<<"$salida"; then
    echo "  ✓ archivo inexistente con ruta absoluta: sugiere $d/a.tex (salida 1)"
else
    echo "  ✗ archivo inexistente: salida $rc, sin la sugerencia"; fallos=$((fallos + 1))
fi
casos=$((casos + 1))
salida="$(TMPDIR="$d/tmp" NO_COLOR=1 "$MAIN" "$d/carpeta-que-no-existe/doc" 2>&1)" && rc=0 || rc=$?
if [ "$rc" -eq 1 ] && grep -q "ninguno en" <<<"$salida"; then
    echo "  ✓ carpeta inexistente: dice que no hay ninguno (salida 1)"
else
    echo "  ✗ carpeta inexistente: salida $rc, sin la línea «ninguno en»"; fallos=$((fallos + 1))
fi

# P14: --log relativo se escribe respecto del directorio de invocación (una sola copia), no dentro de la del .tex
if command -v lualatex > /dev/null; then
    casos=$((casos + 1))
    otra="$(mktemp -d)"
    cp -- "$d/a.tex" "$otra/b.tex"
    mkdir -- "$otra/aqui"
    (cd "$otra/aqui" && NO_COLOR=1 "$MAIN" -s --log salida.log ../b > /dev/null 2>&1) && rc=0 || rc=$?
    if [ "$rc" -eq 0 ] && [ -s "$otra/aqui/salida.log" ] && [ ! -e "$otra/salida.log" ]; then
        echo "  ✓ --log relativo: una sola copia, en el directorio de invocación"
    else
        echo "  ✗ --log relativo: salida $rc; aquí $( [ -e "$otra/aqui/salida.log" ] && echo sí || echo no ), junto al .tex $( [ -e "$otra/salida.log" ] && echo sí || echo no )"
        fallos=$((fallos + 1))
    fi
    rm -f -- "$otra"/aqui/salida.log "$otra"/b.* "$otra"/salida.log
    rmdir -- "$otra/aqui" "$otra" 2>/dev/null || true
fi

[ "$fallos" -eq 0 ] && echo "[dry-run] $casos casos en verde" || { echo "[dry-run] $fallos caso(s) fallaron"; exit 1; }
