"""tests/test_studio.py — LaTeX Studio (2026-10-31): la lectura del .log, la orden de la CLI y la ventana sin pantalla.

Se prueba fuera de los repos (regla de la guía): cada .tex vive en una carpeta temporal.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "studio"))

from latex_app.compilador import Opciones, leer_log, resumen  # noqa: E402

LOG = r"""This is LuaHBTeX, Version 1.18.0
(./prueba.tex
LaTeX Warning: Reference `nada' on page 1 undefined on input line 3.

! Undefined control sequence.
l.4 \comandoquenoexiste

Overfull \hbox (12.0pt too wide) in paragraph at lines 5--5
Package hyperref Warning: Token not allowed in a PDF string on input line 7.
)
"""


def test_lee_errores_y_avisos_con_su_linea():
    ps = leer_log(LOG)
    assert [(p.nivel, p.linea) for p in ps] == [("error", 4), ("aviso", 3), ("aviso", 7), ("tipografia", 5)]
    assert ps[0].mensaje == "Undefined control sequence." and ps[0].archivo == "./prueba.tex"
    assert ps[2].mensaje.startswith("hyperref:")
    assert resumen(ps) == "1 error(es) · 2 aviso(s) · 1 de tipografía"


def test_la_orden_es_la_de_la_cli(tmp_path):
    o = Opciones(tmp_path / "a.tex", motor="lualatex", pasadas=3, bibliografia="biber", indice=True,
                 salida=str(tmp_path / "pdf"), log=tmp_path / "a.log")
    argv = o.orden()
    assert argv[1].endswith("script_compilar_latex/main.sh") and argv[-1].endswith("a.tex")
    for parte in ("-e", "lualatex", "-p", "3", "--biber", "-i", "-o", "--log"):
        assert parte in argv
    assert "-n" in o.orden(simular=True) and "-c" in o.orden(limpiar=True)
    assert o.pdf() == tmp_path / "pdf" / "a.pdf"


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import latex_app  # noqa: F401
    from PySide6.QtWidgets import QApplication
    QApplication.setOrganizationName("latex-studio-pruebas")
    QApplication.setApplicationName("latex-studio-pruebas")
    return QApplication.instance() or QApplication([])


@pytest.mark.skipif(not shutil.which("lualatex"), reason="falta lualatex")
def test_compila_desde_la_ventana_y_muestra_los_errores(app, tmp_path):
    from latex_app.ventana import Ventana
    tex = tmp_path / "prueba.tex"
    tex.write_text("\\documentclass{article}\n\\begin{document}\nHola \\ref{nada}.\n\\end{document}\n",
                   encoding="utf-8")
    antes = tex.read_bytes()
    v = Ventana()
    v.show()
    v.cargar(str(tex))
    v.bib.setCurrentIndex(0)          # sin bibliografía
    v.compilar()
    inicio = time.monotonic()
    while v._en_curso is not None and time.monotonic() - inicio < 120:
        app.processEvents()
        time.sleep(0.05)
    assert (tmp_path / "prueba.pdf").is_file()
    assert tex.read_bytes() == antes
    textos = [v.problemas.lista.item(i).text() for i in range(v.problemas.lista.count())]
    assert any("nada" in t and "línea 3" in t for t in textos), textos
    v.ui.close()


def test_main_smoke(tmp_path):
    entorno = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "XDG_CONFIG_HOME": str(tmp_path)}
    r = subprocess.run([sys.executable, str(REPO / "studio" / "main.py"), "--smoke"], env=entorno, cwd=tmp_path,
                       capture_output=True, text=True, timeout=90)
    assert r.returncode == 0, r.stderr[-2000:]
