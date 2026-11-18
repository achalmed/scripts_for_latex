#!/usr/bin/python3
"""studio/capturar.py — una captura de LaTeX Studio para la documentación, sobre los PROYECTOS DE MUESTRA del repo
(`studio/ejemplo/proyectos/`: nunca documentos reales ni del despacho) copiados a una carpeta de trabajo temporal y
compilados ahí de verdad, con HOME, configuración y caché temporales (ninguna ruta de la máquina en pantalla), el
esquema de color que se pida, la vista y el proyecto y archivo abiertos.

    /usr/bin/python3 studio/capturar.py docs/figuras/latex-studio-proyectos.png --esquema …/LliphiOscuro.colors --vista proyectos
    /usr/bin/python3 studio/capturar.py docs/figuras/latex-studio-escritura.png --esquema …/LliphiOscuro.colors --vista escritura \\
        --proyecto tesis-multiarchivo/principal.tex --archivo capitulos/metodo.tex --linea 18
    /usr/bin/python3 studio/capturar.py salida.png --paleta "compilar"
    /usr/bin/python3 studio/capturar.py salida.png --nuevo memoria --sin-compilar     # «Nuevo documento», ya revisado
    /usr/bin/python3 studio/capturar.py salida.png --vista escritura --proyecto marco/informes/informe-anual/informe.tex \\
        --entrega --sin-compilar                                                      # «Antes de entregar», revisado

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


def arbol_de_muestra(documentos: Path) -> None:
    """Expedientes inventados (sin compilar) en el despacho y un curso de docencia temporales, para que la barra lateral
    muestre categoría › tipo › grupo y la tabla nombres largos en varias líneas."""
    doc = "\\documentclass{%s}\n\\begin{document}\nMuestra.\n\\end{document}\n"
    expedientes = {
        "despacho/documentos/oficios": ["OF-2026-0001-solicitud-de-informacion-sobre-el-presupuesto-institucional",
                                        "OF-2026-0002-invitacion", "OF-2025-0140-respuesta-a-la-consulta"],
        "despacho/documentos/cartas": ["CARTA-2026-0001-agradecimiento", "CARTA-2025-0007-saludo"],
        "despacho/documentos/memorandos": ["MEM-2026-0003-coordinacion"],
        "despacho/representacion": ["2026-11_SR-04_semana-de-representacion-en-la-provincia", "2026-10_SR-03_semana"],
    }
    for carpeta, nombres in expedientes.items():
        for nombre in nombres:
            destino = documentos / carpeta / nombre
            destino.mkdir(parents=True, exist_ok=True)
            (destino / "main.tex").write_text(doc % ("informe-sr" if "representacion" in carpeta else "oficio"))
    for curso, titulo in (("econometria-i", "Econometría I"), ("estadistica-para-economistas", "Estadística para economistas")):
        base = documentos / "docencia" / "contenido" / "cursos" / curso
        for sub, exp in (("examen_parcial", "2025_ep"), ("practicas", "2026_pr_01"), ("practicas", "2026_pr_02")):
            destino = base / "04-evaluaciones" / sub / exp
            destino.mkdir(parents=True, exist_ok=True)
            (destino / f"{exp}.tex").write_text(doc % "academic-exam")
        (base / "curso.yml").write_text(f"version: 1\ntitulo: {titulo}\n")


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
    parser.add_argument("--configurar", action="store_true", help="abre «Configurar el documento» del proyecto")
    parser.add_argument("--modulo", type=int, default=0, help="la sección del diálogo de configuración que se muestra")
    parser.add_argument("--version", default="", help="elige esta versión del proyecto abierto (si su marco declara versiones)")
    parser.add_argument("--compilar-abierto", action="store_true", help="compila el proyecto abierto (tras elegir --version)")
    parser.add_argument("--texstudio", action="store_true", help="abre «Compilar desde TeXstudio con LaTeX Studio…» (sobre el .ini del HOME temporal)")
    parser.add_argument("--arbol", action="store_true",
                        help="añade expedientes de muestra (oficios, cartas, cursos) para ver las subcategorías del árbol")
    parser.add_argument("--categoria", default="", help="la rama elegida a la izquierda (p. ej. «Documentos institucionales › Oficios»)")
    parser.add_argument("--lateral", type=int, default=-1, help="pestaña de la barra lateral de Escritura (0 Archivos · 1 Estructura · 2 Bibliografía · 3 Datos)")
    parser.add_argument("--citas", type=int, default=-1, help="en la pestaña Citas: 0 del proyecto · 1 biblioteca · 2 fichas")
    parser.add_argument("--ficha", action="store_true", help="abre «Nueva ficha» con una textual de muestra ya revisada (Citas › Fichas)")
    parser.add_argument("--ayuda-ia", default=None, help="abre «Ayuda de la IA» de la parte abierta; con texto, lo pega y lo comprueba")
    parser.add_argument("--nuevo", default="", help="abre «Nuevo documento» con este tipo del marco de muestra, lleno y revisado")
    parser.add_argument("--entrega", action="store_true",
                        help="abre «Antes de entregar» del proyecto abierto, con un punto manual ya marcado y otro sin marcar")
    parser.add_argument("--insertar", default="", help="abre el diálogo de insertar de este tipo (seccion, figura, tabla, cita, ecuacion, referencia, lista)")
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
        if args.arbol:
            arbol_de_muestra(casa / "Documentos")
        datos = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
        env.update(HOME=str(casa), XDG_CACHE_HOME=str(casa / ".cache"), XDG_DATA_HOME=str(datos),
                   WRITING_DIR=str(trabajo), DESPACHO_DIR=str(casa / "Documentos" / "despacho"),
                   LATEX_STUDIO_DOCUMENTOS=str(casa / "Documentos"),
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
    from gui_comun.qt import QObject, QTimer

    trabajo = Path(os.environ["LATEX_STUDIO_CAPTURA"])
    app = Aplicacion(aplicacion.APP_ID, aplicacion.NOMBRE, version=aplicacion.APP_VERSION, nombre_ajustes=aplicacion.APP_NAME)
    piezas = aplicacion.construir(app)
    proyectos, compilacion, tareas, interfaz, visor = (piezas[k] for k in ("proyectos", "compilacion", "tareas", "interfaz", "visor"))
    proyectos.detectar_ya()
    if args.categoria:
        proyectos.fijarCategoria(args.categoria)
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
            if args.version:
                QTimer.singleShot(500, lambda: proyectos.elegirVersion(args.version))
            if args.compilar_abierto:
                QTimer.singleShot(900, lambda: compilacion.lanzar(principal, "compilar"))
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
        if args.configurar:
            QTimer.singleShot(900, lambda: interfaz.pedir.emit("configurar_documento", {"ruta": principal}))
            if args.modulo:
                def modulo():
                    for hijo in raiz.findChildren(QObject):
                        if hijo.property("moduloActual") is not None and hijo.property("c") is not None:
                            hijo.setProperty("moduloActual", args.modulo)
                QTimer.singleShot(1500, modulo)
        if args.texstudio:
            QTimer.singleShot(900, lambda: interfaz.pedir.emit("configurar_texstudio", {}))
        if args.lateral >= 0:
            def lateral():
                pestanas = raiz.findChild(QObject, "pestanasLaterales")
                if pestanas is not None:
                    pestanas.setProperty("currentIndex", args.lateral)
            QTimer.singleShot(1200, lateral)
        if args.citas >= 0:
            def citas():
                pestana = raiz.findChild(QObject, "pestanaCitas")
                if pestana is not None:
                    pestana.setProperty("modo", args.citas)
                if args.citas == 1:
                    piezas["biblioteca"].buscar("")
            QTimer.singleShot(1800, citas)
        if args.ficha:
            libro = {"calibre_id": 1, "clave": "quispe2021ciudades", "titulo": "Economía de las ciudades pequeñas", "autores": ["Rosa Quispe"]}
            valores = {"pagina": "12", "tema": "escala urbana", "categoria": "Idea principal", "uso": "introduccion", "revisar": True,
                       "textos": {"Cita exacta": "Las ciudades pequeñas crecen cuando se integran a su región.",
                                  "Análisis": "La tesis del capítulo: la escala importa menos que la integración regional."}}
            QTimer.singleShot(2200, lambda: interfaz.pedir.emit("nueva_ficha", {"libro": libro, **valores}))
        if args.ayuda_ia is not None:
            QTimer.singleShot(2200, lambda: interfaz.pedir.emit("ayuda_ia", {"pegado": args.ayuda_ia.replace("\\n", "\n")}))
        if args.entrega:
            proyecto = Path(principal).parent                 # la muestra guarda lo marcado en <proyecto>/entrega.yml
            (proyecto / "entrega.yml").write_text(
                "puntos:\n  revision: {estado: hecho, fecha: '2026-11-18', nota: La leyó Tomás Arango}\n", encoding="utf-8")
            QTimer.singleShot(1600, lambda: interfaz.pedir.emit("antes_de_entregar", {}))
        if args.insertar:
            def insertar():
                interfaz.pedir.emit("insertar", {"tipo": args.insertar})
            QTimer.singleShot(1500, insertar)
        if args.nuevo:
            valores = {"titulo": "Memoria institucional 2026", "subtitulo": "Lo hecho en el año", "autores": "Rosa Quispe\nTomás Arango",
                       "profundidad": "completo"}
            QTimer.singleShot(1200, lambda: interfaz.pedir.emit("nuevo_documento", {"tipo": args.nuevo, "valores": valores, "revisar": True}))
        if args.paleta is not None:
            QTimer.singleShot(900, lambda: raiz.property("paleta").abrir(args.paleta))
        app.capturar(args.salida, espera_ms=9000 if args.compilar_abierto else 3500)

    QTimer.singleShot(300, compilar)
    codigo = app.app.exec()
    visor.apagar()
    app.cerrar()
    print("CAPTURA", args.salida)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
