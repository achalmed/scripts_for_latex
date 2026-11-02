#!/usr/bin/python3
"""studio/capturar.py — una captura de LaTeX Studio para la documentación, sobre los PROYECTOS DE MUESTRA del repo
(`studio/ejemplo/proyectos/`: nunca documentos reales ni del despacho) copiados a una carpeta de trabajo temporal y
compilados ahí de verdad, con HOME, configuración y caché temporales (ninguna ruta de la máquina en pantalla), el
esquema de color que se pida, la vista y el proyecto y archivo abiertos.

    /usr/bin/python3 studio/capturar.py docs/figuras/latex-studio-proyectos.png --esquema …/LliphiOscuro.colors --vista proyectos
    /usr/bin/python3 studio/capturar.py docs/figuras/latex-studio-escritura.png --esquema …/LliphiOscuro.colors --vista escritura \\
        --proyecto tesis-multiarchivo/principal.tex --archivo capitulos/metodo.tex --linea 18
    /usr/bin/python3 studio/capturar.py salida.png --paleta "compilar"

Sin `--sin-compilar`, compila todos los proyectos de la muestra (en cola, cada uno con su compilador) antes de capturar:
el estado, los problemas, el registro y el PDF son reales.
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

MUESTRA = AQUI / "ejemplo" / "proyectos"


def main() -> int:
    parser = argparse.ArgumentParser(description="Captura de LaTeX Studio sobre los proyectos de muestra del repo")
    parser.add_argument("salida")
    parser.add_argument("--esquema", help="archivo .colors de KDE (relanza con XDG_CONFIG_HOME temporal)")
    parser.add_argument("--vista", default="proyectos", help="proyectos · escritura")
    parser.add_argument("--proyecto", default="tesis-multiarchivo/principal.tex", help="el proyecto seleccionado o abierto (relativo a la muestra)")
    parser.add_argument("--archivo", default="", help="el archivo abierto en el editor (relativo a la carpeta del proyecto)")
    parser.add_argument("--linea", type=int, default=0)
    parser.add_argument("--panel", type=int, default=0, help="pestaña del panel inferior (0 Problemas · 1 Registro · 2 Cola); −1 lo cierra")
    parser.add_argument("--sin-compilar", action="store_true")
    parser.add_argument("--synctex", action="store_true", help="marca en el PDF la línea del editor (SyncTeX)")
    parser.add_argument("--paleta", default=None, help="abre la paleta de órdenes con este texto")
    parser.add_argument("--ancho", type=int, default=1440)
    parser.add_argument("--alto", type=int, default=900)
    args = parser.parse_args()

    if "LATEX_STUDIO_CAPTURA" not in os.environ:      # primera pasada: el entorno temporal, la muestra y relanzar
        from latex_app import aplicacion  # noqa: F401  (localiza gui_comun)
        from gui_comun import rutas
        from gui_comun.galeria.esquema import entorno_con_esquema
        carpeta = Path(tempfile.mkdtemp(prefix="latex-studio-"))
        casa = carpeta / "home" / "autor"
        (casa / ".config").mkdir(parents=True, exist_ok=True)
        config_usuario = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        for nombre in ("kdeglobals", "kcminputrc", "Kvantum"):      # el aspecto del usuario, copiado; sus preferencias no
            origen = config_usuario / nombre
            if origen.is_dir():
                shutil.copytree(origen, casa / ".config" / nombre, dirs_exist_ok=True)
            elif origen.is_file():
                shutil.copy2(origen, casa / ".config" / nombre)
        if args.esquema:
            env = entorno_con_esquema(Path(args.esquema).expanduser(), casa / ".config")
        else:
            env = dict(os.environ, XDG_CONFIG_HOME=str(casa / ".config"))
        trabajo = casa / "Documentos" / "escritura"
        shutil.copytree(MUESTRA, trabajo)
        (casa / "Documentos" / "despacho").mkdir(parents=True)              # vacía: nunca la del autor
        datos = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
        env.update(HOME=str(casa), XDG_CACHE_HOME=str(casa / ".cache"), XDG_DATA_HOME=str(datos),
                   WRITING_DIR=str(trabajo), DESPACHO_DIR=str(casa / "Documentos" / "despacho"),
                   LATEX_STUDIO_CAPTURA=str(trabajo))
        # el mismo gui_comun que esta pasada: con HOME temporal no se ve el `pip install --user`, y subir carpetas
        # desde un worktree encontraría otro
        import gui_comun
        env["PYTHONPATH"] = os.pathsep.join(x for x in (str(Path(gui_comun.__file__).resolve().parents[1]), os.environ.get("PYTHONPATH", "")) if x)
        if rutas.CORE_DIR is not None:
            env.setdefault("CORE_DIR", str(rutas.CORE_DIR))                 # la CLI fuera del espacio de trabajo (un worktree)
        env.setdefault("QT_QPA_PLATFORMTHEME", "kde")
        orden = [sys.executable, str(AQUI / "capturar.py")] + [a for a in sys.argv[1:] if not a.startswith("--esquema") and a != args.esquema]
        codigo = subprocess.run(orden, env=env).returncode
        shutil.rmtree(carpeta, ignore_errors=True)
        return codigo

    from latex_app import aplicacion
    from gui_comun.nucleo import Aplicacion
    from gui_comun.qt import QTimer

    trabajo = Path(os.environ["LATEX_STUDIO_CAPTURA"])
    app = Aplicacion(aplicacion.APP_ID, aplicacion.NOMBRE, version=aplicacion.APP_VERSION, nombre_ajustes=aplicacion.APP_NAME)
    piezas = aplicacion.construir(app)
    proyectos, compilacion, tareas, interfaz, visor = (piezas[k] for k in ("proyectos", "compilacion", "tareas", "interfaz", "visor"))
    proyectos.detectar_ya()
    if not app.cargar(aplicacion.QML_DIR / "Main.qml"):
        return 1
    raiz = app.motor.rootObjects()[0]
    raiz.setProperty("width", args.ancho)
    raiz.setProperty("height", args.alto)
    principal = str((trabajo / args.proyecto).resolve())

    def esperar(despues, ms=200):
        def comprobar():
            if tareas.activa or compilacion.enCurso or compilacion.enCola:
                QTimer.singleShot(ms, comprobar)
            else:
                QTimer.singleShot(ms, despues)
        QTimer.singleShot(ms, comprobar)

    def compilar():
        if not args.sin_compilar and shutil.which("lualatex"):
            compilacion.encolar([p.principal for p in proyectos.todos() if p.categoria != "Pruebas y plantillas"])
        esperar(listo, 300)

    def listo():
        if args.vista == "escritura":
            interfaz.pedir.emit("abrir_proyecto", {"ruta": principal})
            if args.archivo:
                archivo = str(Path(principal).parent / args.archivo)
                QTimer.singleShot(600, lambda: interfaz.pedir.emit("ir_a", {"archivo": archivo, "linea": args.linea}))
            if args.synctex and args.archivo:
                QTimer.singleShot(1800, lambda: visor.desdeCodigo(str(Path(principal).parent / args.archivo), args.linea, 0))
        else:
            fila = proyectos.filaDe(principal)
            QTimer.singleShot(200, lambda: interfaz.pedir.emit("seleccionar_proyecto", {"fila": fila}))
        raiz.setProperty("mostrarInferior", args.panel >= 0)
        if args.panel >= 0:
            QTimer.singleShot(400, lambda: raiz.property("inferior").mostrarExtra(args.panel) if raiz.property("inferior") else None)
        if args.paleta is not None:
            QTimer.singleShot(900, lambda: raiz.property("paleta").abrir(args.paleta))
        app.capturar(args.salida, espera_ms=3500)

    QTimer.singleShot(300, compilar)
    codigo = app.app.exec()
    visor.apagar()
    app.cerrar()
    print("CAPTURA", args.salida)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
