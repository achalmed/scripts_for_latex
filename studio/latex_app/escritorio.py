"""latex_app/escritorio.py — las tres operaciones de escritorio que la instrucción separa (R14), sin Qt:

- abrir un archivo con su aplicación (`xdg-open`: el PDF en Okular, según las asociaciones de KDE);
- mostrarlo en Dolphin señalándolo (`dolphin --select <ruta>`; sin Dolphin, su carpeta con `xdg-open`);
- abrir una carpeta (`xdg-open`, que en Kubuntu es Dolphin).

Elegir archivos o carpetas no está aquí: es `FileDialog`/`FolderDialog` de QtQuick, que con la `QApplication` de
`gui-comun` 3.0 son los diálogos de KDE. Cuando `gui-comun` 3.0 traiga estas funciones, este módulo se sustituye.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def orden_abrir(ruta: str) -> list[str]:
    return ["xdg-open", ruta] if Path(ruta).exists() else []


def orden_mostrar(ruta: str) -> list[str]:
    p = Path(ruta)
    if not p.exists():
        return []
    if shutil.which("dolphin"):
        return ["dolphin", "--select", str(p)] if p.is_file() else ["dolphin", str(p)]
    return ["xdg-open", str(p.parent if p.is_file() else p)]


def orden_carpeta(ruta: str) -> list[str]:
    p = Path(ruta)
    carpeta = p if p.is_dir() else p.parent
    return ["xdg-open", str(carpeta)] if carpeta.is_dir() else []


def lanzar(argv: list[str]) -> bool:
    """Lanza la orden desligada de la ventana (no espera ni hereda su salida). False si no hay orden o falla."""
    if not argv:
        return False
    try:
        subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return True
    except OSError:
        return False
