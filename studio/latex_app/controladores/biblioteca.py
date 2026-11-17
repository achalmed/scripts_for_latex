"""latex_app/controladores/biblioteca.py — la biblioteca del marco en la vista Escritura (pestaña «Citas»): buscar cualquier libro y citarlo (si aún no es fuente del proyecto, el marco lo añade tras confirmar), las fichas del proyecto para insertarlas con su página, y abrir el libro o su PDF.

Objetivo: escribir citando la biblioteca entera, no solo el `.bib` del proyecto, y usar las fichas sin salir del
  editor (decisiones §1.18).
Método: corre las órdenes de la sección `biblioteca:` del `latex-studio.yml` del marco (contrato §9; latex_app/datos.py)
  en hilos: `buscar` con una pausa al teclear, `fichas` al abrir el proyecto, y `citar` en dos tiempos: primero sin
  aplicar (si el libro ya es fuente, se inserta su cita en el acto) y, si es nuevo, con `--aplicar` tras la
  confirmación de la ventana (escribe solo la ficha de fuentes y el .bib del proyecto, nunca el texto).
Fichar (§1.19): si el marco declara `formulario`, `ficha`, `nueva_ficha` y `guardar_ficha`, la pestaña crea y corrige
  fichas: el formulario lo describe el marco (tipos, secciones, rótulos), cada guardado se simula primero (el nombre, el
  cotejo contra el PDF, lo que la norma objeta) y escribe solo con `--aplicar` tras la confirmación del diálogo; una
  ficha que cambió fuera desde que se abrió no se pisa (`ficha_cambiada`: se recarga).
Límite: la ventana no sabe qué es Calibre ni Zotero: corre lo que el marco declara. Sin la sección, la pestaña ofrece
  solo las entradas de los .bib (como antes).
"""
from __future__ import annotations

import json
import subprocess

from gui_comun.qt import QObject, Property, Signal, Slot

from latex_app import datos


class BibliotecaProyecto(QObject):
    cambiado = Signal()
    resultadosCambiados = Signal()
    pedirConfirmacion = Signal(int, str, str)        # calibre_id, título, clave: el libro aún no es fuente del proyecto
    citado = Signal(str)                             # lo que se inserta en el cursor
    formularioCambiado = Signal()
    fichaAbierta = Signal("QVariantMap")             # la ficha leída para editarla (con su huella)
    fichaRevisada = Signal("QVariantMap")            # lo que escribiría (simulación) o lo que escribió

    def __init__(self, proyectos, tareas, consola, parent=None):
        super().__init__(parent)
        self.proyectos, self.tareas, self.consola = proyectos, tareas, consola
        self._decl: dict | None = None
        self._resultados: list = []
        self._fichas: list = []
        self._buscando = False
        self._pedido = ""
        self._error = ""
        self._formulario: dict = {}
        proyectos.abiertoCambiado.connect(self.recargar)

    def _get_disponible(self): return self._decl is not None
    disponible = Property(bool, _get_disponible, notify=cambiado)

    def _get_nombre(self): return self._decl["nombre"] if self._decl else "Biblioteca"
    nombre = Property(str, _get_nombre, notify=cambiado)

    def _get_resultados(self): return self._resultados
    resultados = Property("QVariantList", _get_resultados, notify=resultadosCambiados)

    def _get_fichas(self): return self._fichas
    fichas = Property("QVariantList", _get_fichas, notify=cambiado)

    def _get_buscando(self): return self._buscando
    buscando = Property(bool, _get_buscando, notify=resultadosCambiados)

    def _get_error(self): return self._error
    error = Property(str, _get_error, notify=cambiado)

    def _get_puede_fichar(self): return bool(self._decl and self._decl.get("nueva_ficha") and self._decl.get("formulario"))
    puedeFichar = Property(bool, _get_puede_fichar, notify=cambiado)

    def _get_puede_editar(self): return bool(self._decl and self._decl.get("ficha") and self._decl.get("guardar_ficha"))
    puedeEditar = Property(bool, _get_puede_editar, notify=cambiado)

    def _get_formulario(self): return self._formulario
    formulario = Property("QVariantMap", _get_formulario, notify=formularioCambiado)

    @Slot()
    def recargar(self) -> None:
        """Lee la declaración del marco para el proyecto abierto y sus fichas (en un hilo)."""
        self._decl = datos.declaracion_biblioteca(self.proyectos.principal) if self.proyectos.hayAbierto else None
        self._resultados, self._fichas, self._error = [], [], ""
        self.cambiado.emit()
        self.resultadosCambiados.emit()
        if self._decl and self._decl.get("formulario") and not self._formulario:
            self._pedir_formulario()
        if not self._decl or not self._decl["fichas"]:
            return
        decl = dict(self._decl)

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(decl["fichas"], decl["proyecto"])

        def fin(r):
            dato, error = r
            if self._decl and self._decl["proyecto"] == decl["proyecto"]:
                self._fichas, self._error = dato or [], error
                self.cambiado.emit()
        self.tareas.funcion("Fichas del proyecto", trabajo, silenciosa=True, operacion="lectura", error=False, al_terminar=fin)

    @Slot(str)
    def buscar(self, texto: str) -> None:
        """Los libros de la biblioteca que coinciden con `texto` (el último pedido manda)."""
        if not self._decl:
            return
        self._pedido = texto
        self._buscando = True
        self.resultadosCambiados.emit()
        decl = dict(self._decl)

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return texto, datos._json(datos.con(decl["buscar"], texto=texto), decl["proyecto"])

        def fin(r):
            pedido, (dato, error) = r
            if pedido != self._pedido:
                return                                   # ya se pidió otra cosa
            self._resultados, self._buscando = dato or [], False
            if error:
                self.consola.registrar("warn", f"Biblioteca: {error}")
            self.resultadosCambiados.emit()
        self.tareas.funcion("Buscar en la biblioteca", trabajo, silenciosa=True, operacion="lectura", error=False, al_terminar=fin)

    def _citar(self, calibre_id: int, aplicar: bool, titulo: str = "") -> None:
        decl = dict(self._decl)
        argv = datos.con(decl["citar"], id=str(int(calibre_id))) + (["--aplicar"] if aplicar else [])

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["proyecto"])

        def fin(r):
            dato, error = r
            if error or not dato:
                self.consola.registrar("error", f"Citar: {error}")
                return
            if dato.get("nueva") and not aplicar:
                self.pedirConfirmacion.emit(int(calibre_id), titulo, str(dato.get("clave", "")))
                return
            if aplicar:
                self.consola.registrar("ok", f"Fuente añadida al proyecto: {dato.get('clave')} ({dato.get('bib', '')})")
                self.recargar()
            self.citado.emit(str(dato.get("insertar", "")))
        self.tareas.funcion("Citar", trabajo, silenciosa=not aplicar, operacion="escritura" if aplicar else "lectura",
                            error=False, al_terminar=fin)

    @Slot(int, str)
    def citar(self, calibre_id: int, titulo: str) -> None:
        """Cita el libro: si ya es fuente del proyecto, en el acto; si no, pide confirmación (`pedirConfirmacion`)."""
        if self._decl and self._decl["citar"]:
            self._citar(calibre_id, False, titulo)

    @Slot(int)
    def citarAplicando(self, calibre_id: int) -> None:
        """Tras confirmar: añade el libro a las fuentes del proyecto (fuentes.yml y su .bib) y cita."""
        if self._decl and self._decl["citar"]:
            self._citar(calibre_id, True)

    # ------------------------------------------------------------------ fichar (§1.19)
    def _pedir_formulario(self) -> None:
        decl = dict(self._decl)

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(decl["formulario"], decl["proyecto"])

        def fin(r):
            dato, error = r
            if isinstance(dato, dict):
                self._formulario = dato
                self.formularioCambiado.emit()
            elif error:
                self.consola.registrar("warn", f"Formulario de fichas: {error}")
        self.tareas.funcion("Formulario de fichas", trabajo, silenciosa=True, operacion="lectura", error=False, al_terminar=fin)

    @Slot(str)
    def abrirFicha(self, archivo: str) -> None:
        """Lee la ficha para editarla (`fichaAbierta`, con su huella y sus secciones)."""
        if not self.puedeEditar:
            return
        decl = dict(self._decl)
        argv = datos.con(decl["ficha"], archivo=archivo)

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["proyecto"])

        def fin(r):
            dato, error = r
            if error or not isinstance(dato, dict) or dato.get("error") and not dato.get("secciones"):
                self.consola.registrar("error", f"Abrir la ficha: {error or (dato or {}).get('error', '')}")
                self.fichaAbierta.emit({"error": error or (dato or {}).get("error", "no se pudo leer")})
                return
            self.fichaAbierta.emit(dato)
        self.tareas.funcion("Abrir la ficha", trabajo, silenciosa=True, operacion="lectura", error=False, al_terminar=fin)

    @Slot("QVariantMap", str, str, bool)
    def revisarFicha(self, campos: dict, archivo: str, huella: str, aplicar: bool) -> None:
        """Una ficha nueva (`archivo` vacío) o la corrección de una (con la huella con que se abrió): sin `aplicar`
        simula; con él escribe. El resultado llega por `fichaRevisada` ({archivo, verificacion, problemas, diff,
        escrito, error, codigo})."""
        if not self.puedeFichar and not archivo or archivo and not self.puedeEditar:
            return
        decl = dict(self._decl)
        carga = json.dumps(dict(campos), ensure_ascii=False)
        if archivo:
            argv = datos.con(decl["guardar_ficha"], archivo=archivo, huella=huella, datos=carga)
        else:
            argv = datos.con(decl["nueva_ficha"], datos=carga)
        argv += ["--aplicar"] if aplicar else []

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["proyecto"])

        def fin(r):
            dato, error = r
            dato = dato if isinstance(dato, dict) else {"error": error or "la orden no devolvió nada"}
            if dato.get("escrito"):
                self.consola.registrar("ok", f"Ficha guardada: {dato.get('archivo')}")
                self.recargar()
            elif dato.get("error"):
                self.consola.registrar("warn", f"Ficha: {dato['error']}")
            self.fichaRevisada.emit({**dato, "aplicar": aplicar})
        self.tareas.funcion("Guardar la ficha" if aplicar else "Revisar la ficha", trabajo, silenciosa=not aplicar,
                            operacion="escritura" if aplicar else "lectura", error=False, al_terminar=fin)

    @Slot(int)
    def abrirLibro(self, calibre_id: int) -> None:
        """El libro en el programa de la biblioteca que declara el marco."""
        if not self._decl or not self._decl["abrir"]:
            return
        try:
            subprocess.Popen(datos.con(self._decl["abrir"], id=str(int(calibre_id))), start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as e:
            self.consola.registrar("error", f"Abrir el libro: {e}")
