#!/usr/bin/python3
"""
main.py — Punto de entrada de LaTeX Studio. Sin lógica: la aplicación se arma en latex_app/aplicacion.py.

Corre con el Python del sistema (/usr/bin/python3), cuyo Qt es el que trae Kirigami; el PySide6 de un entorno de
pip o de Anaconda no puede cargar los módulos QML de KDE. La compilación es ../script_compilar_latex/main.sh (la
misma CLI del alias `compilar`).

Uso:
    /usr/bin/python3 main.py [documento.tex]      # ejecución normal; con un .tex, lo abre (su carpeta pasa a ser la de trabajo)
    /usr/bin/python3 main.py --smoke              # construye la interfaz y sale (prueba de humo)
    /usr/bin/python3 main.py --instalar-lanzador  # el acceso directo del menú de aplicaciones (-n simula)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))      # el paquete del studio

from latex_app.aplicacion import main                           # noqa: E402  (latex_app localiza gui_comun al importarse)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
