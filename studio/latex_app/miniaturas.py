"""latex_app/miniaturas.py — la primera página de un PDF como imagen pequeña, para las tarjetas de los proyectos y las figuras de la pestaña «Datos» (sin Qt).

Objetivo: que el autor reconozca su documento o su figura por cómo se ve, no por su ruta (rediseño del 2026-11-17).
Método: `pdftoppm` (poppler, el mismo del visor) dibuja la página 1 a 360 px de ancho en la caché del studio; el nombre
  lleva la ruta y la fecha del PDF, así un PDF recompilado da otra miniatura y la vieja se reemplaza.
Fundamento: decisiones §1.17; el visor ya usa pdftoppm como respaldo de QtPdf (§1.10).
Límite: sin pdftoppm no hay miniaturas (la tarjeta muestra el icono del estado); 20 s como mucho por PDF.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

ANCHO = 360
TOPE = 20


def destino(pdf: str | Path, cache: Path) -> Path | None:
    """Dónde va la miniatura de este PDF en su estado actual (None si el PDF no está)."""
    pdf = Path(pdf)
    try:
        st = pdf.stat()
    except OSError:
        return None
    clave = hashlib.sha1(f"{pdf.resolve()}|{st.st_mtime_ns}|{st.st_size}".encode()).hexdigest()[:20]
    return Path(cache) / "miniaturas" / f"{clave}.png"


def generar(pdf: str | Path, cache: Path) -> Path | None:
    """Dibuja la miniatura si no está; devuelve su ruta o None si no se pudo."""
    d = destino(pdf, cache)
    if d is None:
        return None
    if d.is_file():
        return d
    if not shutil.which("pdftoppm"):
        return None
    d.parent.mkdir(parents=True, exist_ok=True)
    for vieja in d.parent.glob("*.png"):                 # la de una versión anterior del mismo PDF ya no sirve
        if vieja.stem != d.stem and _de(vieja) == str(Path(pdf).resolve()):
            vieja.unlink(missing_ok=True)
            vieja.with_suffix(".origen").unlink(missing_ok=True)
    temporal = d.with_name(d.stem + "-parcial")             # pdftoppm añade .png; se renombra entera: QML nunca lee una a medias
    try:
        subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-singlefile", "-png", "-scale-to-x", str(ANCHO), "-scale-to-y", "-1",
                        str(pdf), str(temporal)], capture_output=True, timeout=TOPE, check=True)
        temporal.with_suffix(".png").replace(d)
    except (OSError, subprocess.SubprocessError):
        temporal.with_suffix(".png").unlink(missing_ok=True)
        return None
    (d.with_suffix(".origen")).write_text(str(Path(pdf).resolve()), encoding="utf-8")
    return d if d.is_file() else None


def _de(png: Path) -> str:
    try:
        return png.with_suffix(".origen").read_text(encoding="utf-8")
    except OSError:
        return ""
