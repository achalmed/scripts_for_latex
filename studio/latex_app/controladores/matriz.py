"""latex_app/controladores/matriz.py — la matriz de consistencia del proyecto abierto (Ctrl+Alt+M) y el asistente de pregunta en cuatro pasos.

Objetivo: ver, junto al editor, cada fila de la matriz (problema, objetivo, hipótesis, la evidencia que la refutaría, el
  supuesto que cuestiona, sus indicadores y su sección) con lo que tiene huérfano, ir a la sección o a la fila con un
  clic, generar el cuadro y pasar de un tema a una pregunta con el asistente (decisiones §1.22; mejoras C1.1 a C1.3 del
  flujo de conocimiento).
Método: corre las órdenes de la sección `matriz:` del `latex-studio.yml` del marco (contrato §13; latex_app/datos.py) en
  hilos: `leer` (la matriz resuelta; `datos.resultado_matriz` pone rutas absolutas y cuenta fallas y avisos), `guia`
  (los pasos del asistente), `pregunta` (sin `--aplicar` revisa lo escrito; con él, al pulsar «Guardar la pregunta»),
  `cuadro` y `nueva` (con `--aplicar` tras el clic del autor, que es la confirmación). Después de escribir, vuelve a leer.
Límite: la ventana no sabe qué es una hipótesis ni un indicador: pinta lo que el marco devuelve. Sin la sección, la
  acción queda deshabilitada.
"""
from __future__ import annotations

import json

from gui_comun.qt import QObject, Property, Signal, Slot

from latex_app import datos


class MatrizProyecto(QObject):
    cambiado = Signal()
    resultadoCambiado = Signal()
    guiaCambiada = Signal()
    preguntaRevisada = Signal("QVariantMap")          # {ok, avisos, texto} (simulado)
    preguntaGuardada = Signal("QVariantMap")          # {ok, escrito} o {error}
    escrito = Signal("QVariantMap")                   # lo que respondió `cuadro` o `nueva`

    def __init__(self, proyectos, tareas, consola, parent=None):
        super().__init__(parent)
        self.proyectos, self.tareas, self.consola = proyectos, tareas, consola
        self._decl: dict | None = None
        self._resultado = datos.resultado_matriz({}, "")
        self._guia: dict = {}
        self._leyendo = False
        self._pedido = 0
        proyectos.abiertoCambiado.connect(self.recargar)

    # ------------------------------------------------------------------ propiedades
    def _get_disponible(self): return self._decl is not None
    disponible = Property(bool, _get_disponible, notify=cambiado)

    def _get_nombre(self): return self._decl["nombre"] if self._decl else "Matriz de consistencia"
    nombre = Property(str, _get_nombre, notify=cambiado)

    def _get_resultado(self): return self._resultado
    resultado = Property("QVariantMap", _get_resultado, notify=resultadoCambiado)

    def _get_leyendo(self): return self._leyendo
    leyendo = Property(bool, _get_leyendo, notify=resultadoCambiado)

    def _get_guia(self): return self._guia
    guia = Property("QVariantMap", _get_guia, notify=guiaCambiada)

    def _get_puede(self) -> dict:
        d = self._decl or {}
        return {k: bool(d.get(k)) for k in ("cuadro", "nueva", "guia", "pregunta")}
    puede = Property("QVariantMap", _get_puede, notify=cambiado)

    # ------------------------------------------------------------------ leer
    @Slot()
    def recargar(self) -> None:
        decl = datos.declaracion_seccion(self.proyectos.principal, "matriz") if self.proyectos.hayAbierto else None
        if (decl or {}).get("proyecto") != (self._decl or {}).get("proyecto"):
            self._resultado = datos.resultado_matriz({}, "")
            self.resultadoCambiado.emit()
        self._decl = decl
        self.cambiado.emit()

    def _correr(self, nombre: str, argv: list, fin_dato, operacion: str = "lectura") -> None:
        decl = dict(self._decl or {})

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["proyecto"])

        def fin(r):
            dato, error = r
            fin_dato(dato if isinstance(dato, dict) else {"error": error or "la orden no devolvió nada"})
        self.tareas.funcion(nombre, trabajo, silenciosa=True, operacion=operacion, error=False, al_terminar=fin)

    @Slot()
    def leer(self) -> None:
        if not self._decl:
            return
        self._pedido += 1
        pedido, proyecto = self._pedido, self._decl["proyecto"]
        self._leyendo = True
        self.resultadoCambiado.emit()

        def fin(dato):
            if pedido != self._pedido or not self._decl or self._decl["proyecto"] != proyecto:
                return
            self._resultado = datos.resultado_matriz(dato, proyecto)
            self._leyendo = False
            if self._resultado["error"]:
                self.consola.registrar("warn", f"Matriz de consistencia: {self._resultado['error']}")
            self.resultadoCambiado.emit()
        self._correr("Leer la matriz de consistencia", self._decl["leer"], fin)

    # ------------------------------------------------------------------ escribir
    def _escribir(self, clave: str, nombre: str) -> None:
        if not self._decl or not self._decl.get(clave):
            return

        def fin(dato):
            if dato.get("error"):
                self.consola.registrar("warn", f"{nombre}: {dato['error']}")
            elif dato.get("escrito"):
                self.consola.registrar("ok", f"{nombre}: {dato.get('archivo', '')}")
            self.escrito.emit(dato)
            self.leer()
        self._correr(nombre, self._decl[clave] + ["--aplicar"], fin, "escritura")

    @Slot()
    def generarCuadro(self) -> None:
        """El cuadro de la matriz (lo escribe el marco, que se niega a pisar uno escrito a mano)."""
        self._escribir("cuadro", "Generar el cuadro de la matriz")

    @Slot()
    def crear(self) -> None:
        """Una matriz vacía con su forma, para llenarla en el editor o con el asistente."""
        self._escribir("nueva", "Crear la matriz de consistencia")

    # ------------------------------------------------------------------ el asistente de pregunta
    @Slot()
    def pedirGuia(self) -> None:
        if not self._decl or not self._decl.get("guia"):
            return

        def fin(dato):
            self._guia = dato if not dato.get("error") else {}
            self.guiaCambiada.emit()
        self._correr("Leer el asistente de pregunta", self._decl["guia"], fin)

    @Slot("QVariantMap", bool)
    def pregunta(self, valores: dict, aplicar: bool) -> None:
        """Lo escrito en el asistente: sin `aplicar` lo revisa (avisos); con él lo guarda en la matriz del proyecto."""
        if not self._decl or not self._decl.get("pregunta"):
            return
        argv = datos.con(self._decl["pregunta"], datos=json.dumps(dict(valores), ensure_ascii=False)) + (["--aplicar"] if aplicar else [])

        def fin(dato):
            if aplicar:
                if dato.get("escrito"):
                    self.consola.registrar("ok", f"Pregunta guardada en {dato.get('archivo', 'la matriz')}")
                self.preguntaGuardada.emit(dato)
                self.leer()
            else:
                self.preguntaRevisada.emit(dato)
        self._correr("Guardar la pregunta" if aplicar else "Revisar la pregunta", argv, fin, "escritura" if aplicar else "lectura")
