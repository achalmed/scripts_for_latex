"""latex_app/controladores/plantillas.py — las plantillas del marco que ahorran tiempo («Insertar una plantilla…», Ctrl+Alt+T): una tabla de regresión desde el paquete, una figura con su nota, su fuente y su texto alternativo, un cuadro con booktabs…

Objetivo: reducir el costo de LaTeX frente a un procesador de texto en lo que más se repite (decisiones §1.24; mejora
  C13.4 del flujo de conocimiento): se elige la plantilla, se llena un formulario corto y el texto que el marco compone
  se ve antes de ponerlo en el cursor.
Método: la sección `plantillas:` del `latex-studio.yml` del marco (contrato §15): `listar` devuelve las plantillas con sus
  campos (`{clave, nombre, descripcion, porque, fuente, campos: [{clave, rotulo, tipo, opciones, omision, obligatorio,
  ayuda}]}`) y `componer` recibe `{plantilla, valores}` y devuelve `{insertar, avisos}` o `{error}`. Ninguna escribe.
Límite: la ventana no sabe qué es una tabla de regresión: pinta el formulario y pone en el cursor lo que el marco compone.
"""
from __future__ import annotations

import json

from gui_comun.qt import QObject, Property, Signal, Slot

from latex_app import datos


class PlantillasMarco(QObject):
    cambiado = Signal()
    listaCambiada = Signal()
    compuesta = Signal("QVariantMap")                 # {insertar, avisos} o {error}

    def __init__(self, proyectos, tareas, consola, parent=None):
        super().__init__(parent)
        self.proyectos, self.tareas, self.consola = proyectos, tareas, consola
        self._decl: dict | None = None
        self._lista: list = []
        self._error = ""
        proyectos.abiertoCambiado.connect(self.recargar)

    def _get_disponible(self): return self._decl is not None
    disponible = Property(bool, _get_disponible, notify=cambiado)

    def _get_lista(self): return self._lista
    lista = Property("QVariantList", _get_lista, notify=listaCambiada)

    def _get_error(self): return self._error
    error = Property(str, _get_error, notify=listaCambiada)

    @Slot()
    def recargar(self) -> None:
        self._decl = datos.declaracion_seccion(self.proyectos.principal, "plantillas") if self.proyectos.hayAbierto else None
        self._lista, self._error = [], ""
        self.cambiado.emit()
        self.listaCambiada.emit()

    def _correr(self, nombre, argv, fin_dato):
        decl = dict(self._decl or {})

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["proyecto"])

        def fin(r):
            dato, error = r
            fin_dato(dato if dato is not None else {"error": error or "la orden no devolvió nada"})
        self.tareas.funcion(nombre, trabajo, silenciosa=True, operacion="lectura", error=False, al_terminar=fin)

    @Slot()
    def listar(self) -> None:
        if not self._decl:
            return

        def fin(dato):
            lista = dato.get("plantillas") if isinstance(dato, dict) else dato
            self._error = str(dato.get("error") or "") if isinstance(dato, dict) else ""
            self._lista = [p for p in lista or [] if isinstance(p, dict) and p.get("clave")]
            self.listaCambiada.emit()
        self._correr("Leer las plantillas", self._decl["listar"], fin)

    @Slot(str, "QVariantMap")
    def componer(self, clave: str, valores: dict) -> None:
        if not self._decl or not self._decl.get("componer"):
            return
        carga = json.dumps({"plantilla": clave, "valores": dict(valores)}, ensure_ascii=False)
        self._correr("Componer la plantilla", datos.con(self._decl["componer"], datos=carga),
                     lambda d: self.compuesta.emit(d if isinstance(d, dict) else {"error": "la orden no devolvió nada"}))
