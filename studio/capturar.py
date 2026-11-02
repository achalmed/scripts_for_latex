#!/usr/bin/python3
"""studio/capturar.py — una captura de LaTeX Studio para la documentación sobre el DOCUMENTO DE EJEMPLO del repo
(`studio/ejemplo/`: ni documentos del despacho ni datos personales) copiado a una carpeta temporal y compilado ahí de
verdad con la CLI (regla del repo: nunca dentro de un repo), con configuración y caché en una carpeta temporal, el
esquema de color que se pida, la vista, el documento, la pestaña de detalles y, si se pide, la paleta de órdenes.

    /usr/bin/python3 studio/capturar.py docs/figuras/latex-studio-oscuro.png --esquema ~/Documents/lliphi/generado/esquema/LliphiOscuro.colors --pestana 2
    /usr/bin/python3 studio/capturar.py docs/figuras/latex-studio-claro.png --esquema ~/Documents/lliphi/generado/esquema/LliphiClaro.colors --pestana 0
    /usr/bin/python3 studio/capturar.py salida.png --paleta "compilar"

Sin `--sin-compilar`, compila los dos documentos del ejemplo antes de capturar (uno con avisos, otro con errores): el
estado de la tabla, los problemas y el registro son reales.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

EJEMPLO = AQUI / "ejemplo"


def preparar_ejemplo(destino: Path) -> Path:
    """El ejemplo del repo copiado a `destino` (los PDF y auxiliares que la compilación deje quedan ahí, nunca en el repo)."""
    destino.mkdir(parents=True, exist_ok=True)
    for p in EJEMPLO.iterdir():
        if p.is_file():
            shutil.copy2(p, destino / p.name)
    return destino


def main() -> int:
    parser = argparse.ArgumentParser(description="Captura de LaTeX Studio sobre el documento de ejemplo del repo")
    parser.add_argument("salida")
    parser.add_argument("--esquema", help="archivo .colors de KDE (relanza con XDG_CONFIG_HOME temporal)")
    parser.add_argument("--vista", default="carpeta", help="carpeta · recientes · historial")
    parser.add_argument("--documento", default="articulo.tex", help="el documento actual (del ejemplo)")
    parser.add_argument("--pestana", type=int, default=2, help="pestaña de detalles (0 Resumen · 1 Opciones · 2 Problemas · 3 Registro · 4 Salidas)")
    parser.add_argument("--sin-compilar", action="store_true", help="no compila el ejemplo antes de capturar")
    parser.add_argument("--paleta", default=None, help="abre la paleta de órdenes con este texto")
    parser.add_argument("--ancho", type=int, default=1280)
    parser.add_argument("--alto", type=int, default=800)
    args = parser.parse_args()

    if "LATEX_STUDIO_CAPTURA" not in os.environ:      # primera pasada: entorno temporal (y esquema), el ejemplo, y relanzar
        from latex_app import aplicacion  # noqa: F401  (localiza gui_comun)
        from gui_comun.galeria.esquema import entorno_con_esquema
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "latex-studio-captura"
        base.mkdir(parents=True, exist_ok=True)
        carpeta = Path(tempfile.mkdtemp(prefix="captura-", dir=base))         # en disco, no en /tmp (RAM)
        (carpeta / "config").mkdir(parents=True, exist_ok=True)
        config_usuario = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        for nombre in ("kdeglobals", "kcminputrc", "Kvantum"):      # el aspecto del usuario, copiado; sus preferencias no
            origen = config_usuario / nombre
            if origen.is_dir():
                shutil.copytree(origen, carpeta / "config" / nombre, dirs_exist_ok=True)
            elif origen.is_file():
                shutil.copy2(origen, carpeta / "config" / nombre)
        if args.esquema:
            env = entorno_con_esquema(Path(args.esquema).expanduser(), carpeta / "config")
        else:
            env = dict(os.environ, XDG_CONFIG_HOME=str(carpeta / "config"))
        env["XDG_CACHE_HOME"] = str(carpeta / "cache")
        env["LATEX_STUDIO_CAPTURA"] = str(preparar_ejemplo(carpeta / "ejemplo"))
        env.setdefault("QT_QPA_PLATFORMTHEME", "kde")     # sin pantalla, la paleta de Qt también lee el kdeglobals temporal
        orden = [sys.executable, str(AQUI / "capturar.py")] + [a for a in sys.argv[1:] if not a.startswith("--esquema") and a != args.esquema]
        codigo = subprocess.run(orden, env=env).returncode
        shutil.rmtree(carpeta, ignore_errors=True)
        return codigo

    from latex_app import aplicacion
    from gui_comun.nucleo import Aplicacion
    from gui_comun.qt import QTimer

    ejemplo = Path(os.environ["LATEX_STUDIO_CAPTURA"])
    app = Aplicacion(aplicacion.APP_ID, aplicacion.NOMBRE, version=aplicacion.APP_VERSION, nombre_ajustes=aplicacion.APP_NAME)
    piezas = aplicacion.construir(app)
    espacio, documentos, corrida, tareas, opciones = piezas["espacio"], piezas["documentos"], piezas["corrida"], piezas["tareas"], piezas["opciones"]
    opciones.fijarBibliografia("biber" if shutil.which("biber") else "ninguna")
    espacio.fijarCarpeta(str(ejemplo))
    if not app.cargar(aplicacion.QML_DIR / "Main.qml"):
        return 1
    raiz = app.motor.rootObjects()[0]
    raiz.setProperty("width", args.ancho)
    raiz.setProperty("height", args.alto)

    pendientes = [] if args.sin_compilar or not shutil.which("lualatex") else [p.name for p in sorted(ejemplo.glob("*.tex"), reverse=True)]

    def compilar_siguiente():
        if tareas.activa:
            QTimer.singleShot(150, compilar_siguiente)
            return
        if pendientes:
            documentos.fijarActual(str(ejemplo / pendientes.pop()))
            corrida.compilar()
            QTimer.singleShot(150, compilar_siguiente)
            return
        QTimer.singleShot(300, listo)

    def listo():
        espacio.fijarVista(args.vista)
        documentos.fijarActual(str(ejemplo / args.documento))
        raiz.setProperty("mostrarDetalles", True)
        raiz.setProperty("mostrarInferior", True)
        inferior = raiz.property("inferior")
        if inferior is not None:
            inferior.setProperty("pestanaActual", 0)
        QTimer.singleShot(300, lambda: piezas["interfaz"].pedir.emit("seleccionar_fila", {"fila": documentos.filaDe(documentos.actual)}))
        QTimer.singleShot(600, lambda: piezas["interfaz"].pedir.emit("pestana", {"indice": args.pestana}))
        if args.paleta is not None:
            QTimer.singleShot(900, lambda: piezas["interfaz"].pedir.emit("paleta", {"texto": args.paleta}))
        app.capturar(args.salida, espera_ms=2000)

    QTimer.singleShot(400, compilar_siguiente)
    codigo = app.app.exec()
    app.cerrar()
    print("CAPTURA", args.salida)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
