"""studio/latex_app/__init__.py — paquete de LaTeX Studio; al importarse encuentra gui_comun en core/py-common."""

import sys as _sys
from pathlib import Path as _Path

# core/py-common en sys.path: ahí vive gui_comun, lo común de los studios. Se sube desde aquí hasta hallar core/,
# como los envoltorios del logger; se añade al final para no tapar ningún módulo del studio.
_d = _Path(__file__).resolve().parent
while _d != _d.parent and not (_d / "core" / "py-common" / "gui_comun").is_dir():
    _d = _d.parent
if not (_d / "core" / "py-common" / "gui_comun").is_dir():
    raise ImportError(f"no encuentro core/py-common/gui_comun subiendo desde {__file__}")
if str(_d / "core" / "py-common") not in _sys.path:
    _sys.path.append(str(_d / "core" / "py-common"))
del _d
