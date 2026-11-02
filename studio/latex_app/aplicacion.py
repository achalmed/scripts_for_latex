"""latex_app/aplicacion.py — arma LaTeX Studio: la aplicación (gui_comun.nucleo), los controladores, el registro de
acciones (menú, barra, menú contextual, paleta, atajos) y carga `qml/Main.qml`.

Toda operación existe una sola vez, aquí, en `Acciones`, y actúa sobre el documento actual (`Documentos.actual`):
Compilar (F5), Compilar con Biber (Ctrl+B), Simular (Mayús+F5, `-n`), Limpiar auxiliares… (muestra la lista y confirma
en QML), Abrir el PDF, Abrir en el editor, Cancelar. Lo que necesita un diálogo lo pide a QML por `Interfaz.pedir`.
Python no construye interfaz; la ventana no compila por su cuenta: toda corrida es `script_compilar_latex/main.sh`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from gui_comun.acciones import Acciones, StandardKey
from gui_comun.consola import Consola
from gui_comun.nucleo import Aplicacion
from gui_comun.qt import QObject, Signal, Slot
from gui_comun.tareas import Tareas

from latex_app import compilador as svc
from latex_app import modelos as mod
from latex_app.controladores.ajustes import Ajustes
from latex_app.controladores.corrida import Corrida
from latex_app.controladores.documentos import Documentos
from latex_app.controladores.espacio import VISTAS, Espacio
from latex_app.controladores.historial import Historial
from latex_app.controladores.opciones import Opciones

APP_DIR = Path(__file__).resolve().parent
QML_DIR = APP_DIR / "qml"
RECURSOS_DIR = APP_DIR / "recursos"
REPO = svc.REPO
APP_ID = "latex-studio"
NOMBRE = "LaTeX Studio"
APP_VERSION = "2.0.0"
ORG_NAME = "EdisonAchalma"
APP_NAME = "LatexStudio"              # el applicationName de QSettings de 1.x: historial y recientes se conservan
DESCRIPCION = ("El compilador del .tex suelto del espacio de trabajo, con ventana: los documentos de una carpeta con su estado "
               "(compilado, con avisos, con errores, sin compilar), LuaLaTeX + Biber con pasadas fijas, cada error y aviso del "
               "registro con su línea (Intro abre el editor ahí), el registro íntegro, el PDF y los auxiliares, recompilar al "
               "guardar y el historial. No compila por su cuenta: toda corrida es script_compilar_latex/main.sh, la misma orden "
               "de terminal (alias compilar) que sigue funcionando sola.")
ACENTO = "rosa"                           # el icono del lanzador: la única marca del studio


def datos_lanzador() -> dict:
    return dict(app_id=APP_ID, nombre=NOMBRE, comentario="Compilar documentos LaTeX: errores con su línea y el PDF",
                orden=["/usr/bin/python3", str(APP_DIR.parent / "main.py")],
                logo_svg=(RECURSOS_DIR / "marca.svg").read_text(encoding="utf-8"), acento=ACENTO,
                categorias="Office;Publishing;", palabras="latex;lualatex;biber;pdf;compilar;tex;",
                archivos=True, mimetypes="text/x-tex;")


class Interfaz(QObject):
    """Lo que Python pide a QML (abrir un diálogo, enfocar el filtro, seleccionar una fila, ir a una pestaña)."""

    pedir = Signal(str, "QVariantMap")

    @Slot(str)
    def abrir(self, nombre: str) -> None:
        self.pedir.emit(nombre, {})


def construir(app: Aplicacion, cache: Path | None = None) -> dict:
    """Crea controladores y acciones, y los expone al QML. Devuelve lo creado (para las pruebas y las capturas)."""
    consola = Consola()
    tareas = Tareas(consola)
    interfaz = Interfaz()
    ajustes = Ajustes()
    opciones = Opciones()
    espacio = Espacio(consola, ajustes)
    historial = Historial(consola)
    documentos = Documentos(espacio, opciones, historial, consola, cache=cache)
    corrida = Corrida(espacio, opciones, documentos, historial, consola, tareas)
    acciones = Acciones()
    acciones.estandar(NOMBRE)
    pedir = lambda que, **datos: (lambda *_: interfaz.pedir.emit(que, datos))

    def objetivo() -> str:
        """La ruta sobre la que actúan Dolphin, terminal y copiar: el documento actual o, si no, la carpeta de trabajo."""
        return documentos.actual or espacio.carpeta

    # --- Archivo
    acciones.registrar("archivo.abrir", "&Abrir un .tex…", "document-open", StandardKey.Open, "Archivo", al_disparar=pedir("abrir_tex"),
                       descripcion="Su carpeta pasa a ser la de trabajo y el documento queda seleccionado (también soltándolo en la ventana)")
    acciones.registrar("archivo.carpeta", "Carpeta de &trabajo…", "folder-open", "Ctrl+Shift+O", "Archivo", al_disparar=pedir("carpeta"),
                       descripcion="La carpeta cuyos .tex llenan la tabla")
    acciones.registrar("archivo.subir", "Carpeta &superior", "go-up", "Alt+Up", "Archivo", al_disparar=espacio.subir)
    acciones.registrar("archivo.dolphin", "Abrir en &Dolphin", "system-file-manager", None, "Archivo", al_disparar=lambda *_: espacio.abrirDolphin(objetivo()),
                       descripcion="La carpeta del documento actual (si no, la de trabajo) en el gestor de archivos")
    acciones.registrar("archivo.terminal", "Abrir t&erminal aquí", "utilities-terminal", "Shift+F4", "Archivo", al_disparar=lambda *_: espacio.abrirTerminal(objetivo()))
    acciones.registrar("archivo.copiar", "&Copiar ruta", "edit-copy", "Ctrl+Shift+C", "Archivo", al_disparar=lambda *_: espacio.copiarRuta(objetivo()))
    # --- Editar
    acciones.registrar("editar.filtrar", "&Filtrar", "edit-find", StandardKey.Find, "Editar", al_disparar=pedir("filtrar"),
                       descripcion="Filtra la tabla de la vista activa")
    acciones.registrar("editar.todo", "Seleccionar &todo", "edit-select-all", StandardKey.SelectAll, "Editar", al_disparar=pedir("seleccionar_todo"))
    acciones.registrar("historial.quitar", "&Quitar del historial", "list-remove", StandardKey.Delete, "Editar", habilitada=False, al_disparar=pedir("historial_quitar"),
                       descripcion="Solo de la lista; el documento no se toca")
    acciones.registrar("historial.vaciar", "&Vaciar el historial", "edit-clear-history", None, "Editar", al_disparar=pedir("historial_vaciar"))
    # --- Ver
    for i, (nombre, texto, icono) in enumerate(VISTAS, start=1):
        acciones.registrar(f"ver.vista.{nombre}", f"&{i} {texto}", icono, f"Ctrl+{i}", "Ver › Vista", marcable=True,
                           al_disparar=lambda *_, n=nombre: espacio.fijarVista(n))
    acciones.registrar("ver.recargar", "&Releer la carpeta", "folder-sync", "Ctrl+R", "Ver", al_disparar=documentos.recargar,
                       descripcion="Vuelve a leer los .tex de la carpeta de trabajo y el estado de cada uno")
    # --- Documento
    acciones.registrar("doc.compilar", "&Compilar", "run-build", StandardKey.Refresh, "Documento", al_disparar=corrida.compilar,
                       descripcion="main.sh con las opciones de la sesión: el PDF y los auxiliares quedan junto al .tex; la salida, en el panel inferior")
    acciones.registrar("doc.compilar_biber", "Compilar con &Biber", "run-build-install", "Ctrl+B", "Documento", al_disparar=corrida.compilarConBiber,
                       descripcion="Fuerza Biber (3 pasadas) sin cambiar las opciones guardadas")
    acciones.registrar("doc.simular", "&Simular la compilación", "system-run", "Shift+F5", "Documento", al_disparar=corrida.simular,
                       descripcion="main.sh -n: las órdenes que correría, sin escribir nada")
    acciones.registrar("doc.cancelar", "Ca&ncelar la compilación", "process-stop", None, "Documento", habilitada=False, al_disparar=corrida.cancelar,
                       descripcion="Detiene la corrida en curso y el motor que lanzó")
    acciones.registrar("doc.limpiar", "&Limpiar auxiliares…", "run-build-clean", "Ctrl+Shift+L", "Documento", al_disparar=pedir("limpiar"),
                       descripcion="Muestra los auxiliares que main.sh -c borraría y, si confirmas, los borra; el .tex y el PDF no se tocan")
    acciones.registrar("doc.pdf", "Abrir el &PDF", "application-pdf", "Ctrl+Shift+P", "Documento", al_disparar=documentos.abrirPdf,
                       descripcion="El PDF del documento actual con el visor del sistema")
    acciones.registrar("doc.editor", "Abrir en el &editor", "document-edit", "Ctrl+E", "Documento", al_disparar=documentos.abrirEditor,
                       descripcion="El .tex en el editor preferido (Ajustes)")
    acciones.registrar("doc.vigilar", "&Recompilar al guardar", "view-refresh", "Ctrl+Shift+R", "Documento", marcable=True, marcada=opciones.vigilar,
                       al_disparar=lambda marcada: setattr(opciones, "vigilar", bool(marcada)),
                       descripcion="Vigila el documento actual y lo compila solo cuando se guarda")
    acciones.registrar("doc.abrir_al_terminar", "Abrir el PDF al &terminar", "document-preview", None, "Documento", marcable=True, marcada=opciones.abrirAlTerminar,
                       al_disparar=lambda marcada: setattr(opciones, "abrirAlTerminar", bool(marcada)))
    # --- Herramientas
    acciones.registrar("prob.ir", "&Ir a la línea", "go-jump", None, "Herramientas", habilitada=False, al_disparar=pedir("ir_a_linea"),
                       descripcion="El editor en el archivo y la línea del problema seleccionado (también Intro en la lista)")
    # --- Ayuda
    acciones.registrar("ayuda.manual", "&Manual del compilador", "help-contents", StandardKey.HelpContents, "Ayuda",
                       al_disparar=lambda *_: subprocess.Popen(["xdg-open", str(REPO / "script_compilar_latex" / "README.md")]))

    acciones.definir_menus([
        ("&Archivo", ["archivo.abrir", "archivo.carpeta", "archivo.subir", "|", "archivo.dolphin", "archivo.terminal", "archivo.copiar", "|", "app.salir"]),
        ("&Editar", ["editar.filtrar", "editar.todo", "|", "historial.quitar", "historial.vaciar"]),
        ("&Ver", ["ventana.navegacion", "ventana.detalles", "ventana.inferior", "|",
                  ("&Vista", [f"ver.vista.{n}" for n, *_r in VISTAS]), "|", "ver.recargar", "|", "ventana.pantalla_completa"]),
        ("&Documento", ["doc.compilar", "doc.compilar_biber", "doc.simular", "doc.cancelar", "|", "doc.limpiar", "|", "doc.pdf", "doc.editor", "|",
                        "doc.vigilar", "doc.abrir_al_terminar"]),
        ("&Herramientas", ["prob.ir", "|", "ventana.paleta"]),
        ("A&justes", ["app.ajustes"]),
        ("Ay&uda", ["ayuda.manual", "app.acerca"]),
    ])
    acciones.definir_barra(["doc.compilar", "doc.simular", "|", "doc.pdf", "doc.editor", "|", "doc.limpiar"])

    # la paleta: las vistas y las carpetas recientes (espacio) y cada documento de la carpeta
    def entradas_paleta(texto: str) -> list[dict]:
        salida = espacio.entradas_paleta(texto)
        salida += [{"nombre": f"doc.ir.{f['ruta']}", "texto": f"Documento: {f['nombre']}", "grupo": "Documentos", "icono": mod.ICONO_TEX,
                    "ejecutar": lambda r=f["ruta"]: (espacio.fijarVista("carpeta"), documentos.fijarActual(r),
                                                     interfaz.pedir.emit("seleccionar_fila", {"fila": documentos.filaDe(r)}))}
                   for f in documentos._tabla_carpeta.todas()]
        return salida
    acciones.anadir_fuente(entradas_paleta)

    # ------------------------------------------------- disponibilidad según el documento, la vista y la tarea
    def vista_cambiada():
        v = espacio.vista
        for nombre in acciones.nombres():
            if nombre.startswith("ver.vista."):
                acciones.marcar(nombre, nombre == f"ver.vista.{v}")
        acciones.habilitar("historial.quitar", v == "historial" and historial.haySeleccion)
        acciones.habilitar("historial.vaciar", historial.total > 0)
        acciones.habilitar("editar.todo", True)

    def disponibilidad():
        hay, activa = documentos.hayActual, tareas.activa
        for nombre in ("doc.compilar", "doc.compilar_biber", "doc.simular", "doc.limpiar"):
            acciones.habilitar(nombre, hay and not activa)
        acciones.habilitar("doc.cancelar", corrida.enCurso)
        acciones.habilitar("doc.pdf", hay and documentos.hayPdf)
        acciones.habilitar("doc.editor", hay)
        acciones.habilitar("ver.recargar", not activa)
        acciones.habilitar("prob.ir", hay and documentos.nProblemas > 0)
        acciones.habilitar("historial.quitar", espacio.vista == "historial" and historial.haySeleccion)
        acciones.habilitar("historial.vaciar", historial.total > 0)
        acciones.marcar("doc.vigilar", opciones.vigilar)
        acciones.marcar("doc.abrir_al_terminar", opciones.abrirAlTerminar)

    def barra_estado():
        espacio.fijarResumen(mod.resumen_contadores(documentos.contadores))

    espacio.vistaCambiada.connect(vista_cambiada)
    documentos.actualCambiado.connect(disponibilidad)
    documentos.cambiado.connect(lambda: (disponibilidad(), barra_estado()))
    historial.seleccionCambiada.connect(disponibilidad)
    historial.cambiado.connect(disponibilidad)
    historial.elegido.connect(documentos.fijarActual)
    opciones.cambiado.connect(disponibilidad)
    tareas.cambiada.connect(disponibilidad)
    corrida.cambiado.connect(disponibilidad)
    documentos.recompilar.connect(lambda: corrida.compilar() if not tareas.activa else None)
    vista_cambiada()
    disponibilidad()
    barra_estado()

    piezas = dict(consola=consola, tareas=tareas, interfaz=interfaz, ajustes=ajustes, opciones=opciones, espacio=espacio,
                  historial=historial, documentos=documentos, corrida=corrida, acciones=acciones)
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
    archivos = [a for a in argv if a.endswith(".tex")]
    if archivos:
        error = piezas["documentos"].abrir(archivos[0])
        if error:
            piezas["consola"].registrar("warn", error)
    return app.ejecutar(QML_DIR / "Main.qml", humo="--smoke" in argv)
