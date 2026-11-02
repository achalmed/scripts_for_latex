"""latex_app/visor.py — el visor PDF integrado sin QtPdf (R10, R11) y SyncTeX (sin Qt, se prueba solo).

Las páginas se renderizan con `pdftoppm` (poppler) a PNG, por demanda y a la resolución del zoom, en una caché pequeña
bajo `$XDG_CACHE_HOME/latex-studio/paginas/<clave>/` donde la clave lleva la ruta, la fecha y el tamaño del PDF:
recompilar invalida solo ese documento. La caché tiene un límite (200 MB por omisión) y se poda por antigüedad.
SyncTeX: `synctex view` (del código al PDF) y `synctex edit` (del PDF al código), con el `.synctex.gz` que dejan el
motor y la CLI con `-k`.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

LIMITE_CACHE = 200 * 1024 * 1024
PUNTOS_POR_PULGADA = 72.0
_TAMANO = re.compile(r"^Page\s+(\d+)\s+size:\s+([\d.]+)\s+x\s+([\d.]+)", re.M)
_PAGINAS = re.compile(r"^Pages:\s+(\d+)", re.M)


def cache_paginas(base: Path | None = None) -> Path:
    raiz = base or Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "latex-studio"
    return raiz / "paginas"


def clave(pdf: Path) -> str:
    try:
        st = pdf.stat()
        firma = f"{pdf.resolve()}|{st.st_mtime_ns}|{st.st_size}"
    except OSError:
        firma = str(pdf)
    return hashlib.sha1(firma.encode("utf-8")).hexdigest()[:16]


def paginas(pdf: Path) -> list[tuple[float, float]]:
    """El tamaño en puntos de cada página (ancho, alto) según `pdfinfo`; [] si no hay PDF o poppler."""
    if not pdf.is_file() or not shutil.which("pdfinfo"):
        return []
    try:
        r = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, timeout=20)
        m = _PAGINAS.search(r.stdout)
        total = int(m.group(1)) if m else 0
        if total == 0:
            return []
        r = subprocess.run(["pdfinfo", "-f", "1", "-l", str(total), str(pdf)], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError, ValueError):
        return []
    tamanos = {int(n): (float(a), float(b)) for n, a, b in _TAMANO.findall(r.stdout)}
    defecto = next(iter(tamanos.values()), (595.0, 842.0))
    return [tamanos.get(i, defecto) for i in range(1, total + 1)]


def renderizar(pdf: Path, pagina: int, ppp: int, cache: Path | None = None) -> Path | None:
    """La página `pagina` (1-based) a `ppp` puntos por pulgada como PNG en la caché; la ruta, o None si falla. Si ya
    está, no se vuelve a renderizar (y se le actualiza la fecha de acceso para la poda)."""
    ppp = max(20, min(400, int(ppp)))
    carpeta = cache_paginas(cache) / clave(pdf)
    destino = carpeta / f"p{pagina}-{ppp}.png"
    if destino.is_file():
        try:
            os.utime(destino)
        except OSError:
            pass
        return destino
    if not shutil.which("pdftoppm") or not pdf.is_file():
        return None
    carpeta.mkdir(parents=True, exist_ok=True)
    tmp = carpeta / f".p{pagina}-{ppp}-{os.getpid()}-{time.monotonic_ns()}"
    try:
        r = subprocess.run(["pdftoppm", "-f", str(pagina), "-l", str(pagina), "-r", str(ppp), "-png", "-singlefile",
                            "-aa", "yes", "-aaVector", "yes", str(pdf), str(tmp)], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    hecho = Path(str(tmp) + ".png")            # pdftoppm -singlefile añade la extensión
    if r.returncode != 0 or not hecho.is_file():
        return None
    os.replace(hecho, destino)
    return destino


def tamano_cache(cache: Path | None = None) -> int:
    total = 0
    for raiz, _d, archivos in os.walk(cache_paginas(cache)):
        for a in archivos:
            try:
                total += os.stat(os.path.join(raiz, a)).st_size
            except OSError:
                pass
    return total


def podar(cache: Path | None = None, limite: int = LIMITE_CACHE, conservar: str = "") -> int:
    """Borra las carpetas de PDF más antiguas (por último acceso) hasta quedar bajo `limite`; nunca la de `conservar`
    (la clave del PDF abierto). Devuelve los bytes liberados. Solo toca la caché del visor."""
    raiz = cache_paginas(cache)
    if not raiz.is_dir():
        return 0
    carpetas = []
    for d in raiz.iterdir():
        if not d.is_dir():
            continue
        archivos = [f for f in d.iterdir() if f.is_file()]
        bytes_ = sum(f.stat().st_size for f in archivos)
        ultimo = max((f.stat().st_mtime for f in archivos), default=0.0)
        carpetas.append((ultimo, bytes_, d))
    total = sum(b for _u, b, _d in carpetas)
    liberado = 0
    for _ultimo, bytes_, d in sorted(carpetas):
        if total <= limite:
            break
        if d.name == conservar:
            continue
        shutil.rmtree(d, ignore_errors=True)
        total -= bytes_
        liberado += bytes_
    return liberado


# ======================================================================================================================
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
