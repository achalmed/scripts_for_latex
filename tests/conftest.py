"""tests/conftest.py — utilidades de las pruebas de latex-studio (fase 5 QML, 2026-11-02).

El temporal va al disco (XDG_CACHE_HOME), no a /tmp (tmpfs: es RAM), y cada prueba compila FUERA de los repos: el
documento de ejemplo (studio/ejemplo/) copiado a una carpeta temporal (regla del CLAUDE.md: compilar dentro de otro repo
reescribe PDFs versionados). Compilar de verdad exige lualatex (y biber): sin ellos esas pruebas se saltan.

Dos clases de prueba:
- en proceso (servicio, modelos, controladores): con el binding del Python que corre pytest (basta QtCore y QtGui) y
  `QT_QPA_PLATFORM=offscreen`; QSettings apunta a una carpeta temporal;
- en un proceso hijo (cada QML, la ventana entera, `--smoke`): con el Python del sistema (/usr/bin/python3), el único
  cuyo Qt trae Kirigami, y `XDG_CONFIG_HOME` y `XDG_CACHE_HOME` temporales.

    tests/run.sh            # = python3 -m pytest tests --basetemp ~/.cache/pytest/latex-studio -p no:cacheprovider
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
STUDIO = REPO / "studio"
EJEMPLO = STUDIO / "ejemplo"
BASETEMP = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "pytest" / "latex-studio" / "basetemp"

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if str(STUDIO) not in sys.path:
    sys.path.insert(0, str(STUDIO))

HAY_BINDING = importlib.util.find_spec("PySide6") is not None or importlib.util.find_spec("PyQt6") is not None
requiere_binding = pytest.mark.skipif(not HAY_BINDING, reason="sin PySide6 ni PyQt6")
requiere_lualatex = pytest.mark.skipif(not shutil.which("lualatex"), reason="falta lualatex")
requiere_biber = pytest.mark.skipif(not (shutil.which("lualatex") and shutil.which("biber")), reason="faltan lualatex o biber")

_VARIABLES_CORE = ("DOCS_ROOT", "INDEX_DIR", "META_DIR", "RESPALDOS_DIR", "GIT_DIR", "GIT_WORK_TREE")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    if config.option.basetemp:
        return
    args = [Path(a.split("::")[0]).resolve() for a in (config.args or [])]
    if args and all(REPO in a.parents or a == REPO for a in args):
        BASETEMP.parent.mkdir(parents=True, exist_ok=True)
        config.option.basetemp = str(BASETEMP)


def _python_del_sistema() -> str | None:
    candidato = "/usr/bin/python3"
    if not Path(candidato).is_file():
        return None
    r = subprocess.run([candidato, "-c", "import importlib.util as u; print(bool(u.find_spec('PySide6') or u.find_spec('PyQt6')))"],
                       capture_output=True, text=True)
    return candidato if r.stdout.strip() == "True" else None


PYTHON_SISTEMA = _python_del_sistema()
requiere_sistema = pytest.mark.skipif(PYTHON_SISTEMA is None, reason="sin binding de Qt en /usr/bin/python3 (Kirigami)")


def _core_para_la_cli() -> None:
    """La CLI busca `core/` subiendo desde su carpeta; fuera del espacio de trabajo (un worktree en la caché) vale
    `CORE_DIR`, que se toma de gui_comun (encuentra core/env.py desde su propio repo)."""
    d = REPO
    while d != d.parent and not (d / "core" / "shell-lib" / "logger.sh").is_file():
        d = d.parent
    if (d / "core" / "shell-lib" / "logger.sh").is_file() or os.environ.get("CORE_DIR"):
        return
    try:
        from gui_comun import rutas
        if rutas.CORE_DIR is not None:
            os.environ["CORE_DIR"] = str(rutas.CORE_DIR)
    except ImportError:
        pass


_core_para_la_cli()


def copiar_ejemplo(destino: Path) -> Path:
    """El documento de ejemplo del repo (articulo.tex, referencias.bib, con-error.tex) copiado a una carpeta temporal."""
    destino.mkdir(parents=True, exist_ok=True)
    for p in EJEMPLO.iterdir():
        if p.is_file():
            shutil.copy2(p, destino / p.name)
    return destino


def copiar_muestra(destino: Path) -> Path:
    """El árbol de proyectos de muestra (studio/ejemplo/proyectos/) copiado a una carpeta temporal: nunca documentos reales."""
    shutil.copytree(EJEMPLO / "proyectos", destino, dirs_exist_ok=True)
    return destino


def entorno_gui(tmp_path: Path, **extra: str) -> dict:
    """Entorno de un proceso hijo con GUI: sin pantalla, QSettings y cachés en temporal."""
    env = {k: v for k, v in os.environ.items() if k not in _VARIABLES_CORE}
    env.update({
        "QT_QPA_PLATFORM": "offscreen",
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "XDG_STATE_HOME": str(tmp_path / "state"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "LC_ALL": "C.UTF-8",
    })
    env.update(extra)
    return env


def correr_python(guion: str, env: dict, *args: str, plazo: int = 120) -> subprocess.CompletedProcess:
    """Corre `guion` con el Python del sistema (el de Kirigami); argv[1] es la carpeta studio/."""
    return subprocess.run([PYTHON_SISTEMA or sys.executable, "-c", guion, str(STUDIO), *args], env=env, capture_output=True,
                          text=True, timeout=plazo)


@pytest.fixture(scope="session")
def app():
    """Una QGuiApplication offscreen para las pruebas en proceso."""
    from gui_comun.qt import QGuiApplication
    QGuiApplication.setOrganizationName("latex-studio-pruebas")
    QGuiApplication.setApplicationName("latex-studio-pruebas")
    instancia = QGuiApplication.instance() or QGuiApplication([sys.argv[0]])
    yield instancia


@pytest.fixture
def documentos(tmp_path, monkeypatch):
    """La carpeta temporal con el ejemplo, QSettings y la caché en temporal (nada del autor se toca)."""
    from gui_comun.qt import QSettings
    QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, str(tmp_path / "config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    return copiar_ejemplo(tmp_path / "doc")
