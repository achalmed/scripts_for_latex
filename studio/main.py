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


def main() -> int:
    preparar_plataforma()                 # sin el plugin de Wayland, XWayland sin aviso
    QApplication.setOrganizationName("EdisonAchalma")
    QApplication.setApplicationName("LatexStudio")
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
