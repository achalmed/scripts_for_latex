#!/usr/bin/env python3
"""
main.py — Punto de entrada de LaTeX Studio.

Orquestación mínima: crea la QApplication, aplica el tema guardado y abre la ventana. La lógica vive en latex_app/ y en
gui_comun (el repo gui-comun); la compilación, en ../script_compilar_latex (la misma CLI del alias `compilar`).

Uso:
    python3 studio/main.py [archivo.tex]   # desde latex-studio/
    python3 studio/main.py --smoke         # construye la interfaz y sale (prueba de humo)
"""

import sys
from pathlib import Path

_AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(_AQUI))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import latex_app  # noqa: F401  encuentra gui_comun
from gui_comun.diseno import preparar_plataforma


APP_ID = "latex-studio"


def datos_lanzador() -> dict:
    """El acceso directo en el menú de aplicaciones (gui_comun.lanzador); abre los .tex que se le den."""
    from latex_app.ventana import ACENTO, LOGO
    return dict(app_id=APP_ID, nombre="LaTeX Studio", comentario="Compilar documentos LaTeX: errores con su línea y el PDF",
                orden=[sys.executable, str(_AQUI / "main.py")], logo_svg=LOGO, acento=ACENTO,
                categorias="Office;Publishing;", palabras="latex;lualatex;biber;pdf;compilar;tex;",
                archivos=True, mimetypes="text/x-tex;")


def main() -> int:
    from gui_comun import lanzador
    atendido = lanzador.desde_main(sys.argv[1:], **datos_lanzador())   # --instalar-lanzador / --quitar-lanzador
    if atendido is not None:
        return atendido
    preparar_plataforma()                 # sin el plugin de Wayland, XWayland sin aviso
    QApplication.setOrganizationName("EdisonAchalma")
    QApplication.setApplicationName("LatexStudio")
    QApplication.setDesktopFileName(APP_ID)    # la ventana se agrupa con su acceso directo (Wayland)
    app = QApplication(sys.argv)
    from latex_app.ventana import Ventana
    ventana = Ventana()
    ventana.show()
    archivos = [a for a in sys.argv[1:] if a.endswith(".tex")]
    if archivos:
        ventana.cargar(archivos[0])
    if "--smoke" in sys.argv:
        QTimer.singleShot(0, app.quit)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
