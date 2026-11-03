"""latex_app/visor.py — SyncTeX del proyecto (sin Qt, se prueba solo): `synctex view` (del código al PDF) y `synctex edit`
(del PDF al código), con el `.synctex.gz` que dejan el motor, el compilador del marco y la CLI con `-k`. Las páginas,
el zoom, la selección, los enlaces y la búsqueda son del visor de `gui-comun` 3.2 (`gui_comun.visor_pdf`, `VistaPdf`);
hasta el 2026-11-03 este módulo también renderizaba las páginas con `pdftoppm`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


# SyncTeX

def _synctex(argv: list[str], cwd: str) -> str:
    if not shutil.which("synctex"):
        return ""
    try:
        return subprocess.run(["synctex", *argv], cwd=cwd, capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def hacia_pdf(pdf: Path, fuente: Path, linea: int, columna: int = 0, carpeta_synctex: str = "") -> dict | None:
    """Código → PDF: {pagina, x, y, ancho, alto} en puntos (origen arriba a la izquierda) del primer recuadro que SyncTeX
    da para esa línea; None si no hay `.synctex.gz` o no casa."""
    argv = ["view", "-i", f"{max(1, linea)}:{max(0, columna)}:{fuente}", "-o", str(pdf)]
    if carpeta_synctex:
        argv += ["-d", carpeta_synctex]
    salida = _synctex(argv, str(pdf.parent))
    campos: dict = {}
    for l in salida.splitlines():
        if ":" not in l:
            continue
        k, v = l.split(":", 1)
        if k in ("Page", "x", "y", "h", "v", "W", "H") and k not in campos:
            campos[k] = v.strip()
        if k == "H" and "Page" in campos:
            break
    try:
        h, v, ancho, alto = float(campos["h"]), float(campos["v"]), float(campos["W"]), float(campos["H"])
        return {"pagina": int(campos["Page"]), "x": h, "y": v - alto, "ancho": ancho, "alto": alto}
    except (KeyError, ValueError):
        return None


def hacia_codigo(pdf: Path, pagina: int, x: float, y: float, carpeta_synctex: str = "") -> dict | None:
    """PDF → código: {archivo, linea, columna} del punto (x, y) en puntos de la página `pagina`; None si no casa."""
    argv = ["edit", "-o", f"{pagina}:{x:.2f}:{y:.2f}:{pdf}"]
    if carpeta_synctex:
        argv += ["-d", carpeta_synctex]
    salida = _synctex(argv, str(pdf.parent))
    archivo, linea, columna = "", 0, 0
    for l in salida.splitlines():
        if l.startswith("Input:") and not archivo:
            archivo = l[6:].strip()
        elif l.startswith("Line:") and not linea:
            linea = int(l[5:].strip() or 0)
        elif l.startswith("Column:") and not columna:
            try:
                columna = max(0, int(l[7:].strip()))
            except ValueError:
                columna = 0
    if not archivo or linea <= 0:
        return None
    ruta = Path(archivo)
    if not ruta.is_absolute():
        ruta = (pdf.parent / ruta)
    return {"archivo": str(os.path.normpath(ruta)), "linea": linea, "columna": columna}
