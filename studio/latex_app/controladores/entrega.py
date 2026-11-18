"""latex_app/controladores/entrega.py — «Antes de entregar» (Ctrl+Alt+E): los controles que el marco revisa antes de entregar el documento abierto, los puntos manuales que el autor marca y el registro de cada uso de la IA que acepta.

Objetivo: cerrar la cadena de evidencia sin salir de la ventana (decisiones §1.21): ver cada control con su estado, su
  porqué con la fuente y sus hallazgos (un clic lleva al archivo y la línea), marcar o justificar lo manual, y saber si
  está «Listo para entregar».
Método: corre las tres órdenes de la sección `entrega:` del `latex-studio.yml` del marco (contrato §12;
  latex_app/datos.py) en hilos: `revisar` (devuelve los controles; `datos.resultado_entrega` les pone la ruta absoluta y
  el veredicto), `marcar` con `--aplicar` al tocar la casilla o guardar la nota (el clic es la confirmación; luego se
  revisa de nuevo) y `registrar_ia` con `--aplicar` cuando el autor pone en el editor un cambio de la ayuda de la IA
  (contrato §10, «Poner en el editor»).
Límite: la ventana no sabe qué es una cifra viva ni qué lista corresponde a un tipo: lo dice el marco. El veredicto lo
  calcula la ventana con lo revisado (`datos.veredicto`): listo si no hay fallas y todo lo manual está marcado o
  justificado. Sin la sección, la acción queda deshabilitada y nada se registra.
"""
from __future__ import annotations

import json

from gui_comun.qt import QObject, Property, Signal, Slot

from latex_app import datos


class AntesDeEntregar(QObject):
    cambiado = Signal()
    resultadoCambiado = Signal()
    marcado = Signal("QVariantMap")                  # lo que respondió `marcar` ({id, estado, escrito} o {error})
    registrado = Signal("QVariantMap")               # lo que respondió `registrar_ia`

    def __init__(self, proyectos, tareas, consola, parent=None):
        super().__init__(parent)
        self.proyectos, self.tareas, self.consola = proyectos, tareas, consola
        self._decl: dict | None = None
        self._resultado: dict = datos.resultado_entrega({"controles": []}, "")
        self._revisando = False
        self._pedido = 0
        proyectos.abiertoCambiado.connect(self.recargar)

    # ------------------------------------------------------------------ propiedades
    def _get_disponible(self): return self._decl is not None
    disponible = Property(bool, _get_disponible, notify=cambiado)

    def _get_nombre(self): return self._decl["nombre"] if self._decl else "Antes de entregar"
    nombre = Property(str, _get_nombre, notify=cambiado)

    def _get_resultado(self): return self._resultado
    resultado = Property("QVariantMap", _get_resultado, notify=resultadoCambiado)

    def _get_revisando(self): return self._revisando
    revisando = Property(bool, _get_revisando, notify=resultadoCambiado)

    def _get_puede_marcar(self): return bool(self._decl and self._decl.get("marcar"))
    puedeMarcar = Property(bool, _get_puede_marcar, notify=cambiado)

    # ------------------------------------------------------------------ revisar
    @Slot()
    def recargar(self) -> None:
        """Lee la declaración del marco para el proyecto abierto; lo revisado de otro proyecto se olvida."""
        decl = datos.declaracion_entrega(self.proyectos.principal) if self.proyectos.hayAbierto else None
        if (decl or {}).get("proyecto") != (self._decl or {}).get("proyecto"):
            self._resultado = datos.resultado_entrega({"controles": []}, "")
            self.resultadoCambiado.emit()
        self._decl = decl
        self.cambiado.emit()

    @Slot()
    def revisar(self) -> None:
        """Corre `revisar` del marco en un hilo (el último pedido manda); `resultado` trae los controles y el veredicto."""
        if not self._decl:
            return
        decl = dict(self._decl)
        self._pedido += 1
        pedido = self._pedido
        self._revisando = True
        self.resultadoCambiado.emit()

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(decl["revisar"], decl["proyecto"], tope=120)

        def fin(r):
            if pedido != self._pedido or not self._decl or self._decl["proyecto"] != decl["proyecto"]:
                return
            dato, error = r
            self._resultado = datos.resultado_entrega(dato if dato is not None else {"error": error}, decl["proyecto"])
            self._revisando = False
            if self._resultado["error"]:
                self.consola.registrar("warn", f"Antes de entregar: {self._resultado['error']}")
            self.resultadoCambiado.emit()
        self.tareas.funcion("Revisar antes de entregar", trabajo, silenciosa=True, operacion="lectura", error=False, al_terminar=fin)

    # ------------------------------------------------------------------ marcar un punto manual
    @Slot(str, bool, str)
    def marcar(self, id: str, hecho: bool, nota: str) -> None:
        """La casilla y la nota de un punto manual: hecho, justificado (sin casilla y con nota) o pendiente."""
        if not self.puedeMarcar:
            return
        nota = (nota or "").strip()
        estado = "hecho" if hecho else "justificado" if nota else "pendiente"
        decl = dict(self._decl)
        argv = datos.con(decl["marcar"], id=id, estado=estado, nota=nota) + ["--aplicar"]

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["proyecto"])

        def fin(r):
            dato, error = r
            dato = dato if isinstance(dato, dict) else {"error": error or "la orden no devolvió nada"}
            if dato.get("error"):
                self.consola.registrar("warn", f"Marcar: {dato['error']}")
            self.marcado.emit(dato)
            self.revisar()
        self.tareas.funcion("Marcar un punto", trabajo, silenciosa=True, operacion="escritura", error=False, al_terminar=fin)

    # ------------------------------------------------------------------ registrar un uso de la IA
    @Slot("QVariantMap")
    def registrarIa(self, uso: dict) -> None:
        """Al poner en el editor un cambio de la ayuda de la IA: {ruta, parte, prompt: {titulo, ruta, version, texto},
        antes, despues}. El marco lo agrega a su registro y regenera la declaración (sin la sección, no hace nada)."""
        if not self._decl or not self._decl.get("registrar_ia"):
            return
        uso = dict(uso)
        decl = dict(self._decl)
        carga = datos.uso_de_ia(decl["proyecto"], str(uso.get("ruta") or ""), str(uso.get("parte") or ""),
                                dict(uso.get("prompt") or {}), str(uso.get("antes") or ""), str(uso.get("despues") or ""))
        argv = datos.con(decl["registrar_ia"], datos=json.dumps(carga, ensure_ascii=False)) + ["--aplicar"]

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["proyecto"])

        def fin(r):
            dato, error = r
            dato = dato if isinstance(dato, dict) else {"error": error or "la orden no devolvió nada"}
            if dato.get("escrito"):
                self.consola.registrar("ok", f"Uso de la IA registrado: {dato.get('registro', '')} ({dato.get('total', '')} en total)")
            else:
                self.consola.registrar("warn", f"Registrar el uso de la IA: {dato.get('error', 'no se escribió')}")
            self.registrado.emit(dato)
        self.tareas.funcion("Registrar el uso de la IA", trabajo, silenciosa=True, operacion="escritura", error=False, al_terminar=fin)
