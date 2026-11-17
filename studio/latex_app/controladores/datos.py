"""latex_app/controladores/datos.py — la pestaña «Datos» de la vista Escritura: las figuras, tablas y cifras que el marco del proyecto abierto declara (latex_app/datos.py), para insertarlas en el cursor, traerlas a la última versión y abrir el programa que las produce.

Objetivo: que el informe y sus datos se trabajen juntos: el autor ve qué puede citar, si su paquete tiene una versión
  más nueva y la trae; la figura se rehace en el programa de datos (Datafw Studio, si el marco lo declara).
Método: se recarga al abrir otro proyecto, en un hilo (`Tareas.funcion`, silenciosa: la orden de recursos tarda uno o
  dos segundos); «Actualizar» corre la orden `actualizar` del marco como tarea de escritura (toca proyecto.yaml,
  figures/, tables/ y recursos/) y, al terminar, vuelve a leer. Nada se escribe en las fuentes del documento.
Fundamento: decisión de diseño (docs/decisiones.md §1.16; contrato §8 de docs/configuracion-de-documentos.md).
Límite: la confirmación de «Actualizar» la pide la ventana (escribe en el proyecto); un marco sin `datos:` deja la
  pestaña vacía con su explicación.
"""
from __future__ import annotations

import subprocess

from gui_comun.qt import QObject, Property, Signal, Slot

from latex_app import datos


class DatosProyecto(QObject):
    cambiado = Signal()
    actualizado = Signal(bool)                 # terminó «Actualizar» (True si salió bien)

    def __init__(self, proyectos, tareas, consola, parent=None):
        super().__init__(parent)
        self.proyectos, self.tareas, self.consola = proyectos, tareas, consola
        self._decl: dict | None = None
        self._rec: dict = {"paquetes": [], "figuras": [], "tablas": [], "cifras": []}
        self._cargando = False
        self._error = ""
        proyectos.abiertoCambiado.connect(self.recargar)

    # ------------------------------------------------------------------ propiedades
    def _get_disponible(self): return self._decl is not None
    disponible = Property(bool, _get_disponible, notify=cambiado)

    def _get_nombre(self): return self._decl["nombre"] if self._decl else "Datos"
    nombre = Property(str, _get_nombre, notify=cambiado)

    def _get_productor(self): return self._decl["productor"]["nombre"] if self._decl and self._decl["productor"]["orden"] else ""
    productor = Property(str, _get_productor, notify=cambiado)

    def _get_paquetes(self): return self._rec["paquetes"]
    paquetes = Property("QVariantList", _get_paquetes, notify=cambiado)

    def _get_elementos(self):
        """Figuras, tablas y cifras en una lista (tipo, id, titulo, insertar, existe), en ese orden."""
        carpeta = self._decl["proyecto"] if self._decl else ""
        f = [{"tipo": "Figuras", "id": x["id"], "titulo": x.get("titulo", ""), "insertar": x.get("insertar", ""),
              "existe": bool(x.get("existe", True)), "detalle": x.get("paquete", ""),
              "archivo": f"{carpeta}/{x['archivo']}" if carpeta and x.get("archivo") else ""} for x in self._rec["figuras"]]
        t = [{"tipo": "Tablas", "id": x["id"], "titulo": x.get("titulo", ""), "insertar": x.get("insertar", ""),
              "existe": bool(x.get("existe", True)), "detalle": ", ".join(x.get("variantes") or []) or x.get("paquete", ""), "archivo": ""}
             for x in self._rec["tablas"]]
        c = [{"tipo": "Cifras", "id": x["macro"], "titulo": x.get("valor", ""), "insertar": x["macro"], "existe": True, "detalle": "", "archivo": ""}
             for x in self._rec["cifras"]]
        return f + t + c
    elementos = Property("QVariantList", _get_elementos, notify=cambiado)

    def _get_hay_nueva(self): return any(p.get("nueva") for p in self._rec["paquetes"])
    hayNueva = Property(bool, _get_hay_nueva, notify=cambiado)

    def _get_cargando(self): return self._cargando
    cargando = Property(bool, _get_cargando, notify=cambiado)

    def _get_error(self): return self._error
    error = Property(str, _get_error, notify=cambiado)

    def _get_proyecto(self): return self._decl["proyecto"] if self._decl else ""
    proyecto = Property(str, _get_proyecto, notify=cambiado)

    # ------------------------------------------------------------------ acciones
    @Slot()
    def recargar(self) -> None:
        """Vuelve a leer lo que el marco declara para el proyecto abierto (en un hilo)."""
        self._decl = datos.declaracion(self.proyectos.principal) if self.proyectos.hayAbierto else None
        self._rec = {"paquetes": [], "figuras": [], "tablas": [], "cifras": []}
        self._error = ""
        self._cargando = self._decl is not None
        self.cambiado.emit()
        if self._decl is None:
            return
        decl = dict(self._decl)

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos.recursos(decl)

        def fin(r):
            if self._decl is None or self._decl["proyecto"] != decl["proyecto"]:
                return                                  # se abrió otro proyecto mientras tanto
            self._rec, self._error, self._cargando = r, r.get("error", ""), False
            self.cambiado.emit()
        self.tareas.funcion(f"Datos de {decl['proyecto'].rsplit('/', 1)[-1]}", trabajo, silenciosa=True, operacion="lectura",
                            error=False, al_terminar=fin)

    @Slot()
    def actualizar(self) -> None:
        """Corre la orden `actualizar` del marco (escribe en el proyecto; la ventana confirma antes)."""
        if not self._decl or not self._decl["actualizar"]:
            return
        decl = dict(self._decl)

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            message_cb("cmd", " ".join(decl["actualizar"]))
            r = subprocess.run(decl["actualizar"], capture_output=True, text=True, cwd=decl["proyecto"], timeout=1800)
            for linea in (r.stdout + r.stderr).splitlines():
                message_cb("err" if "[ERROR]" in linea else "out", linea)
            return r.returncode

        def fin(codigo):
            self.consola.registrar("ok" if codigo == 0 else "error",
                                   f"{self._get_nombre()}: " + ("al día" if codigo == 0 else f"la actualización salió con {codigo}"))
            self.actualizado.emit(codigo == 0)
            self.recargar()
        self.tareas.funcion(f"Actualizar {self._get_nombre().lower()}", trabajo, operacion="escritura", error=False, al_terminar=fin)

    @Slot()
    def abrirProductor(self) -> None:
        """Abre el programa que produce los datos (el que declara el marco) en el proyecto abierto."""
        if not self._decl or not self._decl["productor"]["orden"]:
            return
        try:
            subprocess.Popen(self._decl["productor"]["orden"], start_new_session=True, cwd=self._decl["proyecto"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as e:
            self.consola.registrar("error", f"{self._decl['productor']['nombre']}: {e}")
