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
from latex_app.controladores.configuracion import ConfiguracionDocumento
from latex_app.controladores.ayuda import AyudaParte
from latex_app.controladores.entrega import AntesDeEntregar
from latex_app.controladores.biblioteca import BibliotecaProyecto
from latex_app.controladores.datos import DatosProyecto
from latex_app.controladores.miniaturas import Miniaturas
from latex_app.controladores.nuevo import NuevoDocumento
from latex_app.controladores.sincronizacion import Sincronizacion
from gui_comun.editor import ControladorEditor
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

    @Slot(str)
    def copiarTexto(self, texto: str) -> None:
        """Un texto al portapapeles (el prompt de la ayuda de la IA, §1.19)."""
        QGuiApplication.clipboard().setText(texto)

    @staticmethod
    def orden_texstudio(ruta: str, linea: int = 0, principal: str = "") -> list[str]:
        """La orden de TeXstudio: el archivo en su línea; si es el principal del proyecto, como documento maestro."""
        orden = ["texstudio"]
        if principal and Path(principal).resolve() == Path(ruta).resolve():
            orden.append("--master")
        return orden + ["--line", str(linea or 1), ruta]

    @Property(bool, constant=True)
    def hayTexstudio(self) -> bool:
        return shutil.which("texstudio") is not None

    @Slot(str, int, str)
    def abrirEnTexstudio(self, ruta: str, linea: int = 0, principal: str = "") -> None:
        if not Path(ruta).is_file():
            return
        if not shutil.which("texstudio"):
            self.aviso.emit("TeXstudio no está instalado (paquete texstudio).", "error")
            return
        orden = self.orden_texstudio(ruta, linea, principal)
        try:
            subprocess.Popen(orden, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            self.consola.registrar("info", "TeXstudio: " + " ".join(orden))
        except OSError as e:
            self.aviso.emit(f"No se pudo abrir TeXstudio: {e.strerror}", "error")

    @Property(bool, constant=True)
    def hayOkular(self) -> bool:
        return shutil.which("okular") is not None

    @Slot(str, str, int)
    def abrirEnOkular(self, pdf: str, tex: str = "", linea: int = 0) -> None:
        """El PDF en Okular (`--unique`: si ya está abierto, el mismo; Okular lo recarga solo al compilar); con `tex` y
        `linea`, en ese punto (SyncTeX)."""
        from latex_app import okular
        if not pdf or not Path(pdf).is_file():
            self.aviso.emit("Todavía no hay PDF: compila primero (F5).", "informacion")
            return
        if not shutil.which("okular"):
            self.aviso.emit("Okular no está instalado (paquete okular).", "error")
            return
        orden = okular.orden_abrir(pdf, tex, linea)
        try:
            subprocess.Popen(orden, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            self.consola.registrar("info", "Okular: " + " ".join(orden))
        except OSError as e:
            self.aviso.emit(f"No se pudo abrir Okular: {e.strerror}", "error")

    @Slot(result="QVariantMap")
    def estadoOkular(self) -> dict:
        from latex_app import okular
        ruta = okular.ruta_config()
        return {"instalado": shutil.which("okular") is not None, "abierto": okular.okular_abierto(), "existe": True,
                "configurado": okular.configurado(), "ini": str(ruta), "orden": okular.deseado()["ExternalEditorCommand"],
                "enlace": str(ruta.resolve()) if ruta.is_symlink() else "",
                "cambios": [{"clave": k, "actual": a, "nuevo": n} for k, a, n in okular.cambios()]}

    @Slot(result=str)
    def configurarOkular(self) -> str:
        from latex_app import okular
        error = okular.aplicar()
        if not error:
            self.consola.registrar("info", f"Okular: Mayús+clic vuelve al código en LaTeX Studio ({okular.ruta_config()})")
        return error

    @Slot(result=str)
    def deshacerOkular(self) -> str:
        from latex_app import okular
        error = okular.deshacer()
        if not error:
            self.consola.registrar("info", "Okular: restaurada la configuración anterior")
        return error

    @Slot(result="QVariantMap")
    def estadoTexstudio(self) -> dict:
        from latex_app import texstudio as txs
        ini = txs.ruta_ini()
        return {"instalado": shutil.which("texstudio") is not None, "abierto": txs.texstudio_abierto(),
                "existe": ini.is_file(), "configurado": txs.configurado(), "ini": str(ini), "orden": str(txs.COMPILAR),
                "enlace": str(ini.resolve()) if ini.is_symlink() else "",
                "cambios": [{"clave": k.replace("%20", " "), "actual": a, "nuevo": n} for k, a, n in txs.cambios()]}

    @Slot(result=str)
    def configurarTexstudio(self) -> str:
        from latex_app import texstudio as txs
        error = txs.aplicar()
        if not error:
            self.consola.registrar("info", f"TeXstudio compila ahora con LaTeX Studio ({txs.ruta_ini()}; respaldo al lado)")
        return error

    @Slot(result=str)
    def deshacerTexstudio(self) -> str:
        from latex_app import texstudio as txs
        error = txs.deshacer()
        if not error:
            self.consola.registrar("info", "TeXstudio: restaurada la configuración anterior")
        return error

    def orden_editor(self, ruta: str, linea: int = 0) -> list[str]:
        preferido = self.ajustes.editor or "kate"
        for editor in (preferido, "kate", "kwrite", "code"):
            if shutil.which(editor):
                if editor == "texstudio":
                    return self.orden_texstudio(ruta, linea)
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
    editor = ControladorEditor(consola)
    compilacion = Compilacion(proyectos, historial, ajustes, consola, tareas)
    datos = DatosProyecto(proyectos, tareas, consola)   # la pestaña «Datos» (lo que declara el marco, §8 del contrato)
    biblioteca = BibliotecaProyecto(proyectos, tareas, consola)   # la pestaña «Citas»: la biblioteca del marco (§9)
    ayuda = AyudaParte(proyectos, tareas, consola)               # la ayuda de la IA de la parte abierta (§10 del contrato)
    entrega = AntesDeEntregar(proyectos, tareas, consola)        # «Antes de entregar»: los controles del marco (§12, §1.21)
    nuevo = NuevoDocumento(ajustes, proyectos, tareas, consola)  # «Nuevo documento»: lo que el marco sabe crear (§11, §1.20)
    miniaturas = Miniaturas(cache or cache_del_studio())   # la primera página de cada PDF (tarjetas y figuras, §1.17)
    visor = Visor(cache=cache)
    sistema = Sistema(ajustes, consola)
    sincronizacion = Sincronizacion()
    configuracion = ConfiguracionDocumento(
        consola, editor, rutas=lambda: list(ajustes.rutasTex) + sorted({p.marco for p in proyectos.todos() if p.marco}))
    escritorio = app.escritorio                 # gui-comun 3.0: abrir con su aplicación, mostrar en Dolphin, abrir carpeta
    acciones = Acciones()
    # Ctrl+Q es de «Salir» del menú Archivo (pregunta si hay cambios sin guardar): la estándar app.salir lo cede, porque
    # un atajo en dos acciones es ambiguo y Qt no ejecuta ninguna (prueba en la sesión real, 2026-11-02)
    acciones.estandar(NOMBRE, atajos={"app.salir": ""})
    pedir = lambda que, **datos: (lambda *_: interfaz.pedir.emit(que, datos))

    def objetivo() -> str:
        """Sobre qué actúan Dolphin, la terminal y copiar: el archivo del editor, el proyecto abierto o nada."""
        return editor.actual or proyectos.principal

    def pdf_abierto() -> str:
        p = proyectos.proyecto_abierto()
        return p.pdf if p is not None else ""

    # --- Archivo
    acciones.registrar("archivo.nuevo", "&Nuevo documento…", "document-new", StandardKey.New, "Archivo", al_disparar=pedir("nuevo_documento"),
                       descripcion="Un informe, una tesis, una monografía, un artículo, un ensayo o un libro con la estructura de su "
                                   "marco: eliges el tipo y llenas el formulario; «Revisar» muestra lo que se creará")
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
    def okular_ahora(*_):
        p = proyectos.proyecto_abierto()
        if p is not None:
            sistema.abrirEnOkular(p.pdf, "", 0)

    acciones.registrar("ver.okular", "Ver el PDF en &Okular", "okular", "Ctrl+Alt+O", "Ver", habilitada=False,
                       al_disparar=okular_ahora,
                       descripcion="El PDF del proyecto (o de la versión elegida) en Okular, que lo recarga solo al compilar; "
                                   "Ctrl+clic en el editor lleva ahí y Mayús+clic en Okular vuelve aquí")
    acciones.registrar("okular.configurar", "Volver del PDF al código desde Okular…", "okular", None, "Herramientas",
                       al_disparar=pedir("configurar_okular"),
                       descripcion="Que Mayús+clic en Okular abra el código en esta ventana (su editor externo); muestra el "
                                   "cambio y guarda respaldo")
    acciones.registrar("archivo.texstudio", "Abrir en &TeXstudio", "texstudio", "Ctrl+Shift+E", "Archivo", habilitada=False,
                       al_disparar=pedir("texstudio"),
                       descripcion="El archivo actual en TeXstudio, en la línea del cursor (o el principal del proyecto como "
                                   "documento maestro); lo que se guarde allí se recarga aquí y el PDF que compile se ve aquí")
    acciones.registrar("texstudio.configurar", "Compilar desde TeXstudio con LaTeX Studio…", "configure", None, "Herramientas",
                       al_disparar=pedir("configurar_texstudio"),
                       descripcion="Que «Compilar» de TeXstudio use la misma receta que esta ventana (studio/compilar.py: el "
                                   "compilador del marco, latexmk o LuaLaTeX + Biber); muestra el cambio y guarda respaldo")
    acciones.registrar("documento.configurar", "Configurar el &documento…", "document-properties", "Ctrl+Alt+D", "Archivo",
                       habilitada=False, al_disparar=lambda *_: interfaz.pedir.emit("configurar_documento", {"ruta": proyectos.principal}),
                       descripcion="Metadatos, elementos visibles y opciones del documento, según el latex-studio.yml de su marco; "
                                   "muestra la diferencia y escribe solo al confirmar")
    acciones.registrar("escritura.ayuda_ia", "&Ayuda de la IA para esta parte…", "tools-wizard", "Ctrl+Alt+I", "Herramientas",
                       habilitada=False, al_disparar=pedir("ayuda_ia"),
                       descripcion="Copia el prompt que el marco arma para la parte abierta (con su entrada rellena) y lee la "
                                   "respuesta del chat que pegues: la muestra como cambio sugerido y la pone en el editor si la aceptas")
    acciones.registrar("escritura.entrega", "Antes de &entregar…", "checkmark", "Ctrl+Alt+E", "Herramientas",
                       habilitada=False, al_disparar=pedir("antes_de_entregar"),
                       descripcion="Los controles que el marco revisa antes de entregar: cifras vivas, la lista de control del "
                                   "tipo, referencias y citas cotejadas, y el uso de la IA declarado; un clic en un hallazgo "
                                   "lleva a su línea")
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
    acciones.registrar("ver.buscar_pdf", "&Buscar en el PDF…", "edit-find", "Ctrl+Alt+F", "Ver", habilitada=False, al_disparar=pedir("buscar_pdf"),
                       descripcion="Busca un texto en el PDF y salta de un resultado a otro (con QtPdf)")
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
        ("&Archivo", ["archivo.nuevo", "archivo.abrir", "archivo.carpetas", "archivo.anadir_carpeta", "proyectos.detectar", "|", "archivo.guardar", "archivo.guardar_como", "archivo.guardar_todo",
                      "archivo.cerrar", "proyecto.cerrar", "|", "escritorio.pdf", "escritorio.dolphin", "escritorio.carpeta", "escritorio.terminal",
                      "escritorio.copiar", "escritorio.editor", "archivo.texstudio", "|", "archivo.salir"]),
        ("&Editar", ["editar.buscar", "editar.reemplazar", "editar.ir_linea", "|", "editar.completar", "editar.comentar"]),
        ("&Ver", ["ver.proyectos", "ver.escritura", "|", "ventana.navegacion", "ver.okular", "ver.pdf", "ventana.inferior", "|",
                  "ver.acercar", "ver.alejar", "ver.ajustar", "|", "ventana.pantalla_completa"]),
        ("&Compilar", ["compilar.compilar", "compilar.reconstruir", "compilar.borrador", "compilar.simular", "compilar.cancelar", "|", "compilar.seleccion", "|",
                       "compilar.siguiente", "synctex.pdf", "|", "compilar.dependencias", "compilar.limpiar", "|", "compilar.al_guardar", "historial.vaciar"]),
        ("&Herramientas", ["documento.configurar", "escritura.ayuda_ia", "escritura.entrega", "|", "texstudio.configurar", "okular.configurar", "|", "ventana.paleta"]),
        ("A&justes", ["app.ajustes"]),
        ("Ay&uda", ["ayuda.atajos", "ayuda.manual", "app.acerca"]),
    ])
    acciones.definir_barra(["compilar.compilar", "compilar.cancelar", "compilar.reconstruir", "|", "archivo.guardar", "editar.buscar", "|",
                            "synctex.pdf", "ver.okular", "|", "documento.configurar", "archivo.texstudio"])

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
        acciones.habilitar("ver.okular", bool(p and p.pdf) and sistema.hayOkular)
        acciones.habilitar("ver.buscar_pdf", bool(p and p.pdf) and visor.motor == "qtpdf")
        for nombre in ("escritorio.dolphin", "escritorio.carpeta", "escritorio.terminal", "escritorio.copiar"):
            acciones.habilitar(nombre, hay_proyecto or hay_archivo)
        acciones.habilitar("escritorio.editor", hay_archivo)
        for nombre in ("archivo.cerrar", "editar.buscar", "editar.reemplazar", "editar.ir_linea", "editar.completar", "editar.comentar"):
            acciones.habilitar(nombre, hay_archivo)
        acciones.habilitar("archivo.guardar", hay_archivo)
        acciones.habilitar("archivo.guardar_como", hay_archivo)
        acciones.habilitar("archivo.guardar_todo", editor.hayModificados)
        acciones.habilitar("proyecto.cerrar", hay_proyecto)
        acciones.habilitar("documento.configurar", hay_proyecto)
        acciones.habilitar("escritura.ayuda_ia", hay_archivo and ayuda.disponible)
        acciones.habilitar("escritura.entrega", hay_proyecto and entrega.disponible)
        acciones.habilitar("archivo.texstudio", (hay_proyecto or hay_archivo) and sistema.hayTexstudio)
        acciones.habilitar("proyectos.detectar", not proyectos.enDeteccion)
        acciones.marcar("compilar.al_guardar", ajustes.compilarAlGuardar)
        acciones.marcar("ver.ajustar", visor.ajustarAncho)
        for n, *_r in VISTAS:
            acciones.marcar(f"ver.{n}", interfaz.vista == n)

    for senal in (proyectos.cambiado, proyectos.abiertoCambiado, editor.cambiado, editor.actualCambiado, compilacion.cambiado,
                  compilacion.problemasCambiados, interfaz.vistaCambiada, ajustes.cambiado, visor.zoomCambiado, historial.cambiado,
                  ayuda.cambiado, entrega.cambiado):
        senal.connect(disponibilidad)

    # ------------------------------------------------- lo que encadena a los controladores
    ultimo_job: dict[str, str] = {}
    en_okular = {"pdf": ""}                      # el PDF que la ventana ya abrió en Okular (lo recarga él)

    def a_okular(forzar: bool = False):
        """Con el visor Okular: abre el PDF del proyecto si es otro que el ya abierto, o si Okular se cerró y se pide."""
        p = proyectos.proyecto_abierto()
        if not ajustes.visorOkular or p is None or not p.pdf or not sistema.hayOkular:
            return
        from latex_app import okular
        if p.pdf != en_okular["pdf"] or (forzar and not okular.okular_abierto()):
            en_okular["pdf"] = p.pdf
            sistema.abrirEnOkular(p.pdf, "", 0)

    def abierto_cambiado():
        p = proyectos.proyecto_abierto()
        if p is None:
            visor.abrir("", "")
            sincronizacion.olvidar()
            return
        sincronizacion.vigilar(p.fuentes(), p.pdf or str(Path(p.principal).with_suffix(".pdf")))
        carpeta_synctex = str(Path(p.carpeta) / p.carpeta_aux) if p.carpeta_aux else ""
        visor.abrir(p.pdf, carpeta_synctex)
        if compilacion._ruta_problemas != p.principal or ultimo_job.get(p.principal) != p.job:
            ultimo_job[p.principal] = p.job              # otra versión: su .log tiene otros problemas
            compilacion.leerProblemas(p.principal)
        a_okular()

    def terminada(ruta: str, ok: bool):
        if ruta == proyectos.principal:
            abierto_cambiado()
            sincronizacion.anotar_pdf_propio()
            if ok:
                a_okular(forzar=True)                    # si cerraste Okular, vuelve con el PDF nuevo

    # --- junto a TeXstudio (u otro editor): lo que cambia fuera de la ventana
    def fuentes_de_fuera(rutas: list):
        propias = set(editor.modificados)            # con cambios aquí sin guardar: el editor pregunta
        abiertas = set(editor.rutasAbiertas)
        de_fuera = [r for r in rutas if r not in propias and (r not in abiertas or editor.cambioEnDisco(r))]
        if not de_fuera or not proyectos.hayAbierto:
            return
        consola.registrar("info", "Cambiaron fuera de la ventana: " + ", ".join(Path(r).name for r in de_fuera))
        proyectos.releerEstructura()
        if ajustes.compilarAlCambiarFuera and not compilacion.enCurso:
            compilacion.compilar()

    def pdf_de_fuera(_pdf: str):
        if not compilacion.enCurso:
            consola.registrar("info", "El PDF cambió fuera de la ventana (TeXstudio u otro): recargado.")
            abierto_cambiado()
            if proyectos.hayAbierto:
                compilacion.leerProblemas(proyectos.principal)      # los problemas de esa compilación, aquí

    sincronizacion.fuentesCambiadas.connect(fuentes_de_fuera)
    sincronizacion.pdfCambiado.connect(pdf_de_fuera)

    def guardado(ruta: str):
        if proyectos.hayAbierto and ruta in proyectos.proyecto_abierto().fuentes():
            proyectos.releerEstructura()
            if ajustes.compilarAlGuardar and not compilacion.enCurso:
                compilacion.compilar()

    def configurado(ruta: str):
        if proyectos.hayAbierto and ruta == proyectos.principal:
            proyectos.olvidar_version(ruta)          # si cambió «% !MODO», manda lo que dice el documento
            proyectos.refrescar(ruta)
            proyectos.releerEstructura()

    proyectos.abiertoCambiado.connect(abierto_cambiado)
    ajustes.carpetasCambiadas.connect(nuevo.recargar)
    proyectos.detectando.connect(lambda en_curso: None if en_curso else nuevo.recargar())
    configuracion.aplicado.connect(configurado)
    compilacion.terminada.connect(terminada)
    editor.guardadoArchivo.connect(guardado)
    disponibilidad()

    from latex_app import instancia
    servidor = instancia.Servidor()                  # Mayús+clic en Okular → aquí (main.py --ir)

    def ir_desde_fuera(archivo: str, linea: int):
        if not Path(archivo).is_file():
            return
        if not proyectos.hayAbierto or (archivo != proyectos.principal and archivo not in proyectos.proyecto_abierto().archivos):
            proyectos.abrir(archivo)
        interfaz.fijarVista("escritura")
        interfaz.pedir.emit("ir_a_fuera", {"archivo": archivo, "linea": linea})

    servidor.irA.connect(ir_desde_fuera)
    piezas = dict(consola=consola, tareas=tareas, interfaz=interfaz, ajustes=ajustes, historial=historial, proyectos=proyectos,
                  editor=editor, compilacion=compilacion, visor=visor, sistema=sistema, acciones=acciones, nuevo=nuevo,
                  configuracion=configuracion, sincronizacion=sincronizacion, servidor=servidor, datos=datos, miniaturas=miniaturas, biblioteca=biblioteca,
                  ayuda=ayuda, entrega=entrega)
    for nombre, objeto in piezas.items():
        app.exponer(nombre, objeto)
    app.exponer("descripcionStudio", DESCRIPCION)
    app._piezas = piezas           # que vivan lo que la aplicación
    return piezas


def main(argv: list[str]) -> int:
    from gui_comun import lanzador
    from latex_app import instancia
    ir = instancia.argumentos_ir(argv)                                # Mayús+clic en Okular: main.py --ir ARCHIVO LÍNEA
    if ir and instancia.enviar(*ir):
        return 0                                                     # la ventana abierta va ahí
    atendido = lanzador.desde_main(argv, **datos_lanzador())         # --instalar-lanzador / --quitar-lanzador
    if atendido is not None:
        return atendido
    app = Aplicacion(APP_ID, NOMBRE, version=APP_VERSION, organizacion=ORG_NAME, nombre_ajustes=APP_NAME)
    piezas = construir(app)
    humo = "--smoke" in argv
    archivos = [a for a in argv if a.endswith(".tex")]
    if ir:
        archivos = [ir[0]]
    if archivos:
        error = piezas["proyectos"].abrir(archivos[0])
        if error:
            piezas["consola"].registrar("warn", error)
        else:
            piezas["interfaz"].fijarVista("escritura")
            if ir:
                piezas["interfaz"].pedir.emit("ir_a", {"archivo": ir[0], "linea": ir[1]})
    elif not humo:
        # sin archivo pedido, la ventana arranca en la página de proyectos (2026-11-10): el último abierto no se reabre,
        # queda marcado en la tabla en cuanto termina la detección (Intro lo abre)
        ultimo = piezas["proyectos"].ultimo_abierto()
        if ultimo:
            def marcar_ultimo(en_curso: bool) -> None:
                if en_curso:
                    return
                piezas["proyectos"].detectando.disconnect(marcar_ultimo)
                fila = piezas["proyectos"].filaDe(ultimo)
                if fila >= 0 and piezas["interfaz"].vista == "proyectos":
                    piezas["interfaz"].pedir.emit("seleccionar_proyecto", {"fila": fila})
            piezas["proyectos"].detectando.connect(marcar_ultimo)
    if not humo:
        piezas["proyectos"].detectar()
    try:
        return app.ejecutar(QML_DIR / "Main.qml", humo=humo)
    finally:
        piezas["visor"].apagar()
        piezas["editor"].soltar()
        piezas["sincronizacion"].soltar()
        piezas["servidor"].cerrar()
