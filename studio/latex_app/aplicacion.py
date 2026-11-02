"""latex_app/aplicacion.py — arma LaTeX Studio (reingeniería del 2026-11-02, `docs/reingenieria.md`): la aplicación
(gui_comun.nucleo), los controladores, el registro de acciones (menú, barra de compilación, paleta, atajos de editor
LaTeX) y carga `qml/Main.qml`.

Dos vistas sobre la misma ventana: **Proyectos** (los detectados en las carpetas de trabajo, por categoría, con su
estado; la cola de compilación) y **Escritura** (archivos y estructura del proyecto abierto a la izquierda, el editor
en el centro, el PDF a la derecha, Problemas y el registro abajo). Toda operación existe una sola vez, aquí, en
`Acciones`; lo que necesita un diálogo lo pide a QML por `Interfaz.pedir`. Python no construye interfaz; la ventana no
compila por su cuenta: cada proyecto con su compilador (`compilador.receta`).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from gui_comun.acciones import Acciones, StandardKey
from gui_comun.consola import Consola
from gui_comun.nucleo import Aplicacion
from gui_comun.qt import QGuiApplication, QObject, Property, Signal, Slot
from gui_comun.tareas import Tareas

from latex_app import compilador as svc
from latex_app.controladores.ajustes import Ajustes
from latex_app.controladores.compilacion import Compilacion
from latex_app.controladores.editor import Editor
from latex_app.controladores.historial import Historial
from latex_app.controladores.proyectos import Proyectos, cache_del_studio
from latex_app.controladores.visor import Visor

APP_DIR = Path(__file__).resolve().parent
QML_DIR = APP_DIR / "qml"
RECURSOS_DIR = APP_DIR / "recursos"
REPO = svc.REPO
APP_ID = "latex-studio"
NOMBRE = "LaTeX Studio"
APP_VERSION = "3.0.0"
ORG_NAME = "EdisonAchalma"
APP_NAME = "LatexStudio"              # el applicationName de QSettings de 1.x y 2.x: historial y recientes se conservan
DESCRIPCION = ("El entorno de escritura científica del espacio de trabajo: detecta los proyectos LaTeX de las carpetas de "
               "trabajo (un proyecto es su documento principal con sus \\input, sus .bib y su configuración), los compila "
               "con su compilador y su motor (el que declaran; si no, LuaLaTeX + Biber), y los edita con resaltado, "
               "estructura, autocompletado de \\ref y \\cite, el PDF integrado con SyncTeX y los problemas explicados.")
ACENTO = "rosa"                           # el icono del lanzador: la única marca del studio
VISTAS = (("proyectos", "Proyectos", "view-list-details"), ("escritura", "Escritura", "document-edit"))


def datos_lanzador() -> dict:
    return dict(app_id=APP_ID, nombre=NOMBRE, comentario="Escribir y compilar proyectos LaTeX con el PDF y SyncTeX",
                orden=["/usr/bin/python3", str(APP_DIR.parent / "main.py")],
                logo_svg=(RECURSOS_DIR / "marca.svg").read_text(encoding="utf-8"), acento=ACENTO,
                categorias="Office;Publishing;", palabras="latex;lualatex;biber;pdf;compilar;tex;synctex;tesis;",
                archivos=True, mimetypes="text/x-tex;")


class Interfaz(QObject):
    """Lo que Python pide a QML (abrir un diálogo, ir a una vista, enfocar la búsqueda…) y la vista activa."""

    pedir = Signal(str, "QVariantMap")
    vistaCambiada = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._vista = "proyectos"

    @Property(str, notify=vistaCambiada)
    def vista(self) -> str:
        return self._vista

    @Slot(str)
    def fijarVista(self, vista: str) -> None:
        if vista in dict((v[0], v) for v in VISTAS) and vista != self._vista:
            self._vista = vista
            self.vistaCambiada.emit()

    @Slot(str)
    def abrir(self, nombre: str) -> None:
        self.pedir.emit(nombre, {})


class Sistema(QObject):
    """Lo del sistema que no es de `gui_comun.escritorio`: la terminal en una carpeta, el portapapeles y el editor externo.
    Abrir con su aplicación, mostrar en Dolphin y abrir carpeta son de la base (`app.escritorio`, gui-comun 3.0)."""

    aviso = Signal(str, str)

    def __init__(self, ajustes, consola, parent=None):
        super().__init__(parent)
        self.ajustes, self.consola = ajustes, consola

    @Slot(str)
    def abrirTerminal(self, ruta: str) -> None:
        carpeta = str(Path(ruta).parent if Path(ruta).is_file() else Path(ruta))
        preferido = self.ajustes.terminal or "konsole"
        terminal = next((t for t in (preferido, "konsole", "x-terminal-emulator") if shutil.which(t)), "")
        if not terminal:
            self.aviso.emit("No se encontró un emulador de terminal (konsole).", "aviso")
            return
        argv = ["konsole", "--workdir", carpeta] if terminal == "konsole" else [terminal]
        subprocess.Popen(argv, cwd=carpeta, start_new_session=True)

    @Slot(str)
    def copiarRuta(self, ruta: str) -> None:
        QGuiApplication.clipboard().setText(ruta)
        self.consola.registrar("info", f"Ruta copiada: {ruta}")

    def orden_editor(self, ruta: str, linea: int = 0) -> list[str]:
        preferido = self.ajustes.editor or "kate"
        for editor in (preferido, "kate", "kwrite", "code"):
            if shutil.which(editor):
                if editor in ("kate", "kwrite"):
                    return [editor, "--line", str(linea or 1), ruta]
                if editor == "code":
                    return [editor, "-g", f"{ruta}:{linea or 1}"]
                return [editor, ruta]
        return ["xdg-open", ruta]

    @Slot(str, int)
    def abrirEnEditorExterno(self, ruta: str, linea: int = 0) -> None:
        if not Path(ruta).is_file():
            return
        orden = self.orden_editor(ruta, linea)
        try:
            subprocess.Popen(orden, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            self.consola.registrar("info", "Editor externo: " + " ".join(orden))
        except OSError as e:
            self.aviso.emit(f"No se pudo abrir el editor externo ({orden[0]}): {e.strerror}", "error")


def construir(app: Aplicacion, cache: Path | None = None) -> dict:
    """Crea controladores y acciones, y los expone al QML. Devuelve lo creado (para las pruebas y las capturas)."""
    cache = cache or cache_del_studio()
    consola = Consola()
    tareas = Tareas(consola)
    interfaz = Interfaz()
    ajustes = Ajustes()
    historial = Historial(consola)
    proyectos = Proyectos(ajustes, historial, consola, tareas, cache=cache)
    editor = Editor(consola)
    compilacion = Compilacion(proyectos, historial, ajustes, consola, tareas)
    visor = Visor(cache=cache)
    sistema = Sistema(ajustes, consola)
    escritorio = app.escritorio                 # gui-comun 3.0: abrir con su aplicación, mostrar en Dolphin, abrir carpeta
    acciones = Acciones()
    acciones.estandar(NOMBRE)
    pedir = lambda que, **datos: (lambda *_: interfaz.pedir.emit(que, datos))

    def objetivo() -> str:
        """Sobre qué actúan Dolphin, la terminal y copiar: el archivo del editor, el proyecto abierto o nada."""
        return editor.actual or proyectos.principal

    def pdf_abierto() -> str:
        p = proyectos.proyecto_abierto()
        return p.pdf if p is not None else ""

    # --- Archivo
    acciones.registrar("archivo.abrir", "&Abrir un .tex…", "document-open", StandardKey.Open, "Archivo", al_disparar=pedir("abrir_tex"),
                       descripcion="Abre el proyecto de ese .tex (un capítulo abre su documento principal); con el diálogo de archivos de KDE")
    acciones.registrar("archivo.carpetas", "Carpetas de &trabajo…", "folder-open", "Ctrl+Shift+O", "Archivo", al_disparar=pedir("carpetas"),
                       descripcion="Las carpetas donde se buscan proyectos y su profundidad")
    acciones.registrar("archivo.anadir_carpeta", "Añadir una carpeta de trabajo…", "folder-new", None, "Archivo", al_disparar=pedir("anadir_carpeta"))
    acciones.registrar("proyectos.detectar", "&Buscar proyectos de nuevo", "view-refresh", "Ctrl+Shift+R", "Archivo", al_disparar=proyectos.detectar, operacion="lectura",
                       descripcion="Vuelve a recorrer las carpetas de trabajo (solo se relee lo que cambió)")
    acciones.registrar("archivo.guardar", "&Guardar", "document-save", StandardKey.Save, "Archivo", habilitada=False, al_disparar=pedir("guardar"),
                       operacion="escritura")
    acciones.registrar("archivo.guardar_como", "Guardar &como…", "document-save-as", "Ctrl+Shift+S", "Archivo", habilitada=False,
                       al_disparar=pedir("guardar_como"), operacion="escritura",
                       descripcion="El archivo actual con otro nombre (diálogo de KDE, que pregunta antes de sobrescribir); el original no se toca")
    acciones.registrar("archivo.guardar_todo", "Guardar &todo", "document-save-all", "Ctrl+L", "Archivo", habilitada=False, al_disparar=pedir("guardar_todo"),
                       operacion="escritura")
    acciones.registrar("archivo.cerrar", "&Cerrar el archivo", "document-close", StandardKey.Close, "Archivo", habilitada=False, al_disparar=pedir("cerrar_archivo"))
    acciones.registrar("proyecto.cerrar", "Cerrar el &proyecto", "project-development-close", None, "Archivo", habilitada=False, al_disparar=pedir("cerrar_proyecto"))
    acciones.registrar("escritorio.pdf", "Abrir el PDF con su &aplicación", "application-pdf", "Ctrl+Shift+P", "Archivo", habilitada=False,
                       al_disparar=lambda *_: escritorio.abrirConAplicacion(pdf_abierto()), descripcion="El PDF en Okular (o la aplicación de KDE para PDF)")
    acciones.registrar("escritorio.dolphin", "&Mostrar en Dolphin", "system-file-manager", None, "Archivo", habilitada=False,
                       al_disparar=lambda *_: escritorio.mostrarEnDolphin(objetivo()), descripcion="Dolphin en la carpeta, con el archivo señalado")
    acciones.registrar("escritorio.carpeta", "Abrir la &carpeta", "folder", None, "Archivo", habilitada=False,
                       al_disparar=lambda *_: escritorio.abrirCarpeta(objetivo()))
    acciones.registrar("escritorio.terminal", "Abrir t&erminal aquí", "utilities-terminal", "Shift+F4", "Archivo", habilitada=False,
                       al_disparar=lambda *_: sistema.abrirTerminal(objetivo()))
    acciones.registrar("escritorio.copiar", "Copiar la &ruta", "edit-copy", "Ctrl+Shift+C", "Archivo", habilitada=False,
                       al_disparar=lambda *_: sistema.copiarRuta(objetivo()))
    acciones.registrar("escritorio.editor", "Abrir en el editor e&xterno", "document-edit", None, "Archivo", habilitada=False,
                       al_disparar=pedir("editor_externo"), descripcion="El archivo actual en Kate (Ajustes), en la línea del cursor")
    acciones.registrar("archivo.salir", "&Salir", "application-exit", StandardKey.Quit, "Archivo", al_disparar=pedir("salir"),
                       descripcion="Cierra la ventana (pregunta si hay cambios sin guardar)")
    # --- Editar
    acciones.registrar("editar.buscar", "&Buscar…", "edit-find", StandardKey.Find, "Editar", habilitada=False, al_disparar=pedir("buscar"))
    acciones.registrar("editar.reemplazar", "&Reemplazar…", "edit-find-replace", "Ctrl+R", "Editar", habilitada=False, al_disparar=pedir("reemplazar"),
                       descripcion="Buscar y reemplazar, con expresiones regulares si se marcan")
    acciones.registrar("editar.ir_linea", "&Ir a la línea…", "go-jump", "Ctrl+G", "Editar", habilitada=False, al_disparar=pedir("ir_linea"))
    acciones.registrar("editar.completar", "&Completar", "code-context", "Ctrl+Space", "Editar", habilitada=False, al_disparar=pedir("completar"),
                       descripcion="Órdenes, entornos, \\ref de las \\label y \\cite de los .bib del proyecto")
    acciones.registrar("editar.comentar", "C&omentar o descomentar", "format-text-code", "Ctrl+T", "Editar", habilitada=False, al_disparar=pedir("comentar"))
    # --- Ver
    for i, (nombre, texto, icono) in enumerate(VISTAS, start=1):
        acciones.registrar(f"ver.{nombre}", f"&{i} {texto}", icono, f"Ctrl+{i}", "Ver", marcable=True,
                           al_disparar=lambda *_, n=nombre: interfaz.fijarVista(n))
    acciones.registrar("ver.pdf", "&Visor PDF", "view-pdf", "F7", "Ver", marcable=True, marcada=True, al_disparar=pedir("alternar_pdf"))
    acciones.registrar("ver.acercar", "A&cercar el PDF", "zoom-in", None, "Ver", al_disparar=visor.acercar)
    acciones.registrar("ver.alejar", "Ale&jar el PDF", "zoom-out", None, "Ver", al_disparar=visor.alejar)
    acciones.registrar("ver.ajustar", "Ajustar el PDF al &ancho", "zoom-fit-width", None, "Ver", marcable=True, marcada=True,
                       al_disparar=lambda marcada: setattr(visor, "ajustarAncho", bool(marcada)))
    # --- Compilar
    acciones.registrar("compilar.compilar", "&Compilar", "run-build", "F5", "Compilar", habilitada=False, al_disparar=compilacion.compilar, operacion="escritura",
                       descripcion="El proyecto abierto con su compilador y su motor (también Ctrl+B)")
    acciones.registrar("compilar.reconstruir", "&Reconstruir todo", "run-build-clean", "F6", "Compilar", habilitada=False, al_disparar=compilacion.reconstruir, operacion="escritura",
                       descripcion="Limpia los auxiliares y compila de nuevo (bibliografía incluida)")
    acciones.registrar("compilar.borrador", "Comprobar sin PDF (&borrador)", "document-preview", None, "Compilar", habilitada=False,
                       al_disparar=compilacion.borrador, operacion="escritura", descripcion="main.sh --draft: comprueba que compila sin escribir el PDF")
    acciones.registrar("compilar.simular", "&Simular", "system-run", "Shift+F5", "Compilar", habilitada=False, al_disparar=compilacion.simular, operacion="simulacion",
                       descripcion="Las órdenes que correría, sin escribir nada")
    acciones.registrar("compilar.cancelar", "&Detener", "process-stop", None, "Compilar", habilitada=False, al_disparar=compilacion.cancelar,
                       descripcion="Detiene la compilación en curso y vacía la cola (también Esc en la barra de estado)")
    acciones.registrar("compilar.seleccion", "Compilar los &marcados", "run-build-configure", "Ctrl+Shift+F5", "Compilar", habilitada=False,
                       al_disparar=pedir("compilar_marcados"), descripcion="Los proyectos marcados en la página de proyectos, en cola")
    def consecuencias_limpiar() -> str:
        lista = compilacion.auxiliaresParaLimpiar("")
        if not lista:
            return "No hay auxiliares que borrar."
        carpeta = proyectos.proyecto_abierto().carpeta if proyectos.hayAbierto else ""
        return (f"Se borrarán {len(lista)} archivo" + ("" if len(lista) == 1 else "s") + f" de {carpeta}:\n\n" + "\n".join(lista[:30])
                + (f"\n… y {len(lista) - 30} más" if len(lista) > 30 else "")
                + "\n\nLas fuentes (.tex, .bib) y el PDF no se tocan. SyncTeX deja de funcionar hasta la próxima compilación.")
    acciones.registrar("compilar.limpiar", "&Limpiar auxiliares…", "edit-clear", "Ctrl+Shift+L", "Compilar", habilitada=False,
                       al_disparar=lambda *_: compilacion.limpiar(""), operacion="eliminacion", consecuencias=consecuencias_limpiar,
                       descripcion="Muestra lo que se borraría y, si confirmas, lo borra; las fuentes y el PDF no se tocan")
    acciones.registrar("compilar.dependencias", "Revisar &dependencias", "tools-check-spelling", "Ctrl+Shift+D", "Compilar", habilitada=False,
                       al_disparar=lambda *_: compilacion.revisarDependencias(""), operacion="lectura", descripcion="Clase, paquetes, archivos y programas que faltan (solo lee)")
    acciones.registrar("compilar.siguiente", "Siguiente &problema", "go-next", "F8", "Compilar", habilitada=False, al_disparar=compilacion.siguiente)
    acciones.registrar("compilar.al_guardar", "Compilar al &guardar", "view-refresh", None, "Compilar", marcable=True, marcada=ajustes.compilarAlGuardar,
                       al_disparar=lambda marcada: setattr(ajustes, "compilarAlGuardar", bool(marcada)))
    acciones.registrar("synctex.pdf", "Ir al &PDF (SyncTeX)", "go-next-view", "Ctrl+Alt+J", "Compilar", habilitada=False, al_disparar=pedir("synctex"),
                       descripcion="La línea del cursor en el PDF (también Ctrl+clic en el editor); doble clic en el PDF vuelve al código")
    acciones.registrar("historial.vaciar", "&Vaciar el historial de compilaciones", "edit-clear-history", None, "Compilar",
                       al_disparar=lambda *_: historial.vaciar(), operacion="eliminacion",
                       consecuencias=lambda: f"Se quitarán las {historial.total} compilaciones del historial. Los proyectos y sus PDF no se tocan.",
                       descripcion="Solo la lista; los proyectos no se tocan")
    # --- Ayuda
    acciones.registrar("ayuda.atajos", "&Atajos de teclado", "input-keyboard", None, "Ayuda", al_disparar=pedir("atajos"))
    acciones.registrar("ayuda.manual", "&Manual del compilador", "help-contents", StandardKey.HelpContents, "Ayuda",
                       al_disparar=lambda *_: escritorio.abrirConAplicacion(str(REPO / "script_compilar_latex" / "README.md")))

    acciones.definir_menus([
        ("&Archivo", ["archivo.abrir", "archivo.carpetas", "archivo.anadir_carpeta", "proyectos.detectar", "|", "archivo.guardar", "archivo.guardar_como", "archivo.guardar_todo",
                      "archivo.cerrar", "proyecto.cerrar", "|", "escritorio.pdf", "escritorio.dolphin", "escritorio.carpeta", "escritorio.terminal",
                      "escritorio.copiar", "escritorio.editor", "|", "archivo.salir"]),
        ("&Editar", ["editar.buscar", "editar.reemplazar", "editar.ir_linea", "|", "editar.completar", "editar.comentar"]),
        ("&Ver", ["ver.proyectos", "ver.escritura", "|", "ventana.navegacion", "ver.pdf", "ventana.inferior", "|",
                  "ver.acercar", "ver.alejar", "ver.ajustar", "|", "ventana.pantalla_completa"]),
        ("&Compilar", ["compilar.compilar", "compilar.reconstruir", "compilar.borrador", "compilar.simular", "compilar.cancelar", "|", "compilar.seleccion", "|",
                       "compilar.siguiente", "synctex.pdf", "|", "compilar.dependencias", "compilar.limpiar", "|", "compilar.al_guardar", "historial.vaciar"]),
        ("&Herramientas", ["ventana.paleta"]),
        ("A&justes", ["app.ajustes"]),
        ("Ay&uda", ["ayuda.atajos", "ayuda.manual", "app.acerca"]),
    ])
    acciones.definir_barra(["compilar.compilar", "compilar.cancelar", "compilar.reconstruir", "|", "archivo.guardar", "editar.buscar", "|",
                            "synctex.pdf", "escritorio.pdf"])

    # la paleta: las vistas, las categorías y cada proyecto detectado
    def entradas_paleta(texto: str) -> list[dict]:
        salida = [{"nombre": f"ir.{n}", "texto": f"Ir a {t}", "grupo": "Vistas", "icono": i, "ejecutar": lambda n=n: interfaz.fijarVista(n)}
                  for n, t, i in VISTAS]
        if texto.strip():
            salida += [{"nombre": f"proyecto.{p.principal}", "texto": f"Proyecto: {Path(p.carpeta).name} · {p.nombre}", "grupo": "Proyectos",
                        "icono": "text-x-tex", "ejecutar": lambda r=p.principal: interfaz.pedir.emit("abrir_proyecto", {"ruta": r})}
                       for p in proyectos.todos()]
        return salida
    acciones.anadir_fuente(entradas_paleta)

    # ------------------------------------------------- disponibilidad
    def disponibilidad():
        hay_proyecto, hay_archivo = proyectos.hayAbierto, bool(editor.actual)
        ocupado = compilacion.enCurso
        p = proyectos.proyecto_abierto()
        for nombre in ("compilar.compilar", "compilar.reconstruir", "compilar.simular", "compilar.dependencias"):
            acciones.habilitar(nombre, hay_proyecto)
        acciones.habilitar("compilar.limpiar", hay_proyecto and not ocupado)
        acciones.habilitar("compilar.borrador", bool(p and p.compilador == "main.sh"))
        acciones.habilitar("historial.vaciar", historial.total > 0)
        acciones.habilitar("compilar.cancelar", ocupado or compilacion.enCola > 0)
        acciones.habilitar("compilar.seleccion", proyectos.total > 0)
        acciones.habilitar("compilar.siguiente", compilacion.nProblemas > 0)
        acciones.habilitar("synctex.pdf", hay_archivo and bool(p and p.pdf))
        acciones.habilitar("escritorio.pdf", bool(p and p.pdf))
        for nombre in ("escritorio.dolphin", "escritorio.carpeta", "escritorio.terminal", "escritorio.copiar"):
            acciones.habilitar(nombre, hay_proyecto or hay_archivo)
        acciones.habilitar("escritorio.editor", hay_archivo)
        for nombre in ("archivo.cerrar", "editar.buscar", "editar.reemplazar", "editar.ir_linea", "editar.completar", "editar.comentar"):
            acciones.habilitar(nombre, hay_archivo)
        acciones.habilitar("archivo.guardar", hay_archivo)
        acciones.habilitar("archivo.guardar_como", hay_archivo)
        acciones.habilitar("archivo.guardar_todo", editor.hayModificados)
        acciones.habilitar("proyecto.cerrar", hay_proyecto)
        acciones.habilitar("proyectos.detectar", not proyectos.enDeteccion)
        acciones.marcar("compilar.al_guardar", ajustes.compilarAlGuardar)
        acciones.marcar("ver.ajustar", visor.ajustarAncho)
        for n, *_r in VISTAS:
            acciones.marcar(f"ver.{n}", interfaz.vista == n)

    for senal in (proyectos.cambiado, proyectos.abiertoCambiado, editor.cambiado, editor.actualCambiado, compilacion.cambiado,
                  compilacion.problemasCambiados, interfaz.vistaCambiada, ajustes.cambiado, visor.zoomCambiado, historial.cambiado):
        senal.connect(disponibilidad)

    # ------------------------------------------------- lo que encadena a los controladores
    def abierto_cambiado():
        p = proyectos.proyecto_abierto()
        if p is None:
            visor.abrir("", "")
            return
        carpeta_synctex = str(Path(p.carpeta) / p.carpeta_aux) if p.carpeta_aux else ""
        visor.abrir(p.pdf, carpeta_synctex)
        if compilacion._ruta_problemas != p.principal:
            compilacion.leerProblemas(p.principal)

    def terminada(ruta: str, ok: bool):
        if ruta == proyectos.principal:
            abierto_cambiado()

    def guardado(ruta: str):
        if proyectos.hayAbierto and ruta in proyectos.proyecto_abierto().fuentes():
            proyectos.releerEstructura()
            if ajustes.compilarAlGuardar and not compilacion.enCurso:
                compilacion.compilar()

    proyectos.abiertoCambiado.connect(abierto_cambiado)
    compilacion.terminada.connect(terminada)
    editor.guardadoArchivo.connect(guardado)
    disponibilidad()

    piezas = dict(consola=consola, tareas=tareas, interfaz=interfaz, ajustes=ajustes, historial=historial, proyectos=proyectos,
                  editor=editor, compilacion=compilacion, visor=visor, sistema=sistema, acciones=acciones)
    for nombre, objeto in piezas.items():
        app.exponer(nombre, objeto)
    app.exponer("descripcionStudio", DESCRIPCION)
    app._piezas = piezas           # que vivan lo que la aplicación
    return piezas


def main(argv: list[str]) -> int:
    from gui_comun import lanzador
    atendido = lanzador.desde_main(argv, **datos_lanzador())         # --instalar-lanzador / --quitar-lanzador
    if atendido is not None:
        return atendido
    app = Aplicacion(APP_ID, NOMBRE, version=APP_VERSION, organizacion=ORG_NAME, nombre_ajustes=APP_NAME)
    piezas = construir(app)
    humo = "--smoke" in argv
    archivos = [a for a in argv if a.endswith(".tex")]
    if archivos:
        error = piezas["proyectos"].abrir(archivos[0])
        if error:
            piezas["consola"].registrar("warn", error)
        else:
            piezas["interfaz"].fijarVista("escritura")
    elif not humo:
        ultimo = piezas["proyectos"].ultimo_abierto()
        if ultimo and Path(ultimo).is_file() and not piezas["proyectos"].abrir(ultimo):
            piezas["interfaz"].fijarVista("escritura")
    if not humo:
        piezas["proyectos"].detectar()
    try:
        return app.ejecutar(QML_DIR / "Main.qml", humo=humo)
    finally:
        piezas["visor"].apagar()
        piezas["editor"].soltar()
