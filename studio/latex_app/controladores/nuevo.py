"""latex_app/controladores/nuevo.py — «Nuevo documento»: crear un documento del marco (un informe, una tesis, un artículo…) con botones y un formulario, sin la terminal.

Objetivo: que el autor empiece un documento desde la ventana con la estructura que su marco exige (decisiones §1.20).
Método: corre las dos órdenes de la sección `nuevo:` del `latex-studio.yml` del marco (contrato §11;
  latex_app/datos.py::declaracion_nuevo), buscada en cada carpeta de trabajo y en los marcos de los proyectos detectados:
  `tipos` (devuelve los tipos, sus variantes y su formulario) y `crear` en dos tiempos: «Revisar» la corre sin aplicar
  (el marco crea en un temporal y devuelve la carpeta, los archivos y el principal) y «Crear y abrir», con `--aplicar`;
  luego la ventana abre el principal en el editor. Todo en hilos (`Tareas.funcion`).
Límite: la ventana no sabe qué es una tesis ni dónde va: lo dice el marco. Con varios marcos que declaran `nuevo:`, se
  elige el marco primero; sin ninguno, el diálogo lo explica.
"""
from __future__ import annotations

import json

from gui_comun.qt import QObject, Property, Signal, Slot

from latex_app import datos


class NuevoDocumento(QObject):
    cambiado = Signal()
    revisionCambiada = Signal()
    creado = Signal(str)                             # el principal del documento recién creado

    def __init__(self, ajustes, proyectos, tareas, consola, parent=None):
        super().__init__(parent)
        self.ajustes, self.proyectos, self.tareas, self.consola = ajustes, proyectos, tareas, consola
        self._decls: list[dict] = []
        self._marco = -1
        self._tipos: list = []
        self._cargando = False
        self._trabajando = False
        self._error = ""
        self._revision: dict = {}
        self._pedido = 0                                 # el último pedido manda (revisar dos veces seguidas)

    # ------------------------------------------------------------------ propiedades
    def _get_marcos(self): return [{"nombre": d["nombre"], "carpeta": d["carpeta"], "esquema": d["esquema"]} for d in self._decls]
    marcos = Property("QVariantList", _get_marcos, notify=cambiado)

    def _get_marco(self): return self._marco
    marco = Property(int, _get_marco, notify=cambiado)

    def _get_nombre(self): return self._decls[self._marco]["nombre"] if 0 <= self._marco < len(self._decls) else ""
    nombreMarco = Property(str, _get_nombre, notify=cambiado)

    def _get_tipos(self): return self._tipos
    tipos = Property("QVariantList", _get_tipos, notify=cambiado)

    def _get_cargando(self): return self._cargando
    cargando = Property(bool, _get_cargando, notify=cambiado)

    def _get_trabajando(self): return self._trabajando
    trabajando = Property(bool, _get_trabajando, notify=revisionCambiada)

    def _get_error(self): return self._error
    error = Property(str, _get_error, notify=cambiado)

    def _get_revision(self): return self._revision
    revision = Property("QVariantMap", _get_revision, notify=revisionCambiada)

    def _get_disponible(self): return bool(self._decls)
    disponible = Property(bool, _get_disponible, notify=cambiado)

    # ------------------------------------------------------------------ marcos y tipos
    def carpetas(self) -> list[str]:
        """Dónde se busca la sección `nuevo:`: las carpetas de trabajo y los marcos de los proyectos detectados."""
        return [str(r) for _n, r in self.ajustes.raices()] + sorted({p.marco for p in self.proyectos.todos() if p.marco})

    @Slot()
    def recargar(self) -> None:
        """Vuelve a leer qué marcos declaran `nuevo:`; con uno solo, lo elige (y pide sus tipos)."""
        previo = self._decls[self._marco]["esquema"] if 0 <= self._marco < len(self._decls) else ""
        self._decls = datos.declaraciones_nuevo(self.carpetas())
        esquemas = [d["esquema"] for d in self._decls]
        if previo and previo in esquemas:
            self._marco = esquemas.index(previo)         # el elegido sigue: sus tipos valen
        else:
            self._marco, self._tipos, self._error = (0 if len(self._decls) == 1 else -1), [], ""
        self.cambiado.emit()
        if self._marco >= 0 and not self._tipos:
            self._pedir_tipos()

    @Slot(int)
    def elegirMarco(self, indice: int) -> None:
        if not 0 <= indice < len(self._decls):
            self._marco, self._tipos = -1, []
            self.cambiado.emit()
            return
        if indice != self._marco or not self._tipos:
            self._marco, self._tipos, self._error = indice, [], ""
            self.olvidar()
            self.cambiado.emit()
            self._pedir_tipos()

    def _pedir_tipos(self) -> None:
        decl = dict(self._decls[self._marco])
        self._cargando = True
        self.cambiado.emit()

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(decl["tipos"], decl["carpeta"])

        def fin(r):
            dato, error = r
            if not (0 <= self._marco < len(self._decls)) or self._decls[self._marco]["esquema"] != decl["esquema"]:
                return                                   # ya se eligió otro marco
            self._cargando = False
            if isinstance(dato, dict) and isinstance(dato.get("tipos"), list) and not dato.get("error"):
                self._tipos, self._error = dato["tipos"], ""
            else:
                self._tipos = []
                self._error = (dato.get("error") if isinstance(dato, dict) else "") or error or "la orden no devolvió los tipos"
                self.consola.registrar("warn", f"Nuevo documento: {self._error}")
            self.cambiado.emit()
        self.tareas.funcion("Tipos de documento", trabajo, silenciosa=True, operacion="lectura", error=False, al_terminar=fin)

    # ------------------------------------------------------------------ revisar y crear
    @Slot()
    def olvidar(self) -> None:
        """Lo revisado ya no vale (cambió el formulario)."""
        if self._revision:
            self._revision = {}
            self.revisionCambiada.emit()

    def _crear(self, campos: dict, aplicar: bool) -> None:
        if not 0 <= self._marco < len(self._decls):
            return
        decl = dict(self._decls[self._marco])
        argv = datos.con(decl["crear"], datos=json.dumps(dict(campos), ensure_ascii=False)) + (["--aplicar"] if aplicar else [])
        self._pedido += 1
        pedido = self._pedido
        self._trabajando = True
        self.revisionCambiada.emit()

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["carpeta"], tope=180)

        def fin(r):
            if pedido != self._pedido:
                return
            dato, error = r
            dato = dato if isinstance(dato, dict) else {"error": error or "la orden no devolvió nada"}
            self._trabajando = False
            self._revision = {**dato, "aplicar": aplicar}
            self.revisionCambiada.emit()
            if aplicar and dato.get("escrito") and dato.get("principal"):
                self.consola.registrar("ok", f"Documento creado: {dato.get('destino', dato['principal'])}")
                self.creado.emit(str(dato["principal"]))
                self.proyectos.detectar()
            elif dato.get("error"):
                self.consola.registrar("warn", f"Nuevo documento: {dato['error']}")
        self.tareas.funcion("Crear el documento" if aplicar else "Revisar el documento", trabajo, silenciosa=not aplicar,
                            operacion="escritura" if aplicar else "simulacion", error=False, al_terminar=fin)

    @Slot("QVariantMap")
    def revisar(self, campos: dict) -> None:
        """Simula: el marco crea el documento en un temporal y dice dónde iría y con qué archivos (`revision`)."""
        self._crear(campos, False)

    @Slot("QVariantMap")
    def crear(self, campos: dict) -> None:
        """Lo crea de verdad (tras «Revisar»); al terminar, `creado` lleva el principal para abrirlo."""
        self._crear(campos, True)
