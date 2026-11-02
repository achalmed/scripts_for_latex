#!/usr/bin/env bash
# tests/run.sh — corre las pruebas de latex-studio con pytest, con la carpeta temporal en disco y sin caché.
# Uso: tests/run.sh [opciones de pytest]   (p. ej. -k corrida)
# La carpeta temporal va a ~/.cache (no a /tmp, que es RAM). Todas compilan fuera de los repos: el documento de ejemplo
# (studio/ejemplo/) copiado a una carpeta temporal, con lualatex y biber de verdad si están instalados (si no, se saltan).
# Las pruebas en proceso usan el binding del Python que corre pytest; las de QML y la de humo abren un proceso hijo con el
# Python del sistema (/usr/bin/python3, el del Qt con Kirigami) sin pantalla (QT_QPA_PLATFORM=offscreen) y con
# XDG_CONFIG_HOME y XDG_CACHE_HOME temporales: ni las preferencias ni la caché del autor se tocan.
set -euo pipefail

DIR_PRUEBAS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_TMP="${XDG_CACHE_HOME:-$HOME/.cache}/pytest/latex-studio"
mkdir -p "$BASE_TMP"

export PYTHONDONTWRITEBYTECODE=1
export QT_QPA_PLATFORM=offscreen
exec python3 -m pytest "$DIR_PRUEBAS" --basetemp "$BASE_TMP" -p no:cacheprovider -q "$@"
