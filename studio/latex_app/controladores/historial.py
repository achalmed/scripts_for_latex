"""latex_app/controladores/historial.py — la vista Historial: cada compilación (documento, resultado, duración, detalle,
cuándo) guardada en QSettings con las claves de 1.x (`historial`, hasta 60; rediseño L10) como tabla ordenable y
filtrable; elegir una fila vuelve a ese documento (`elegido`). También los recientes (`recientes`, hasta 12)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from gui_comun.modelos import ModeloFiltrado, ModeloTabla
from gui_comun.qt import QObject, QSettings, Property, Signal, Slot

from latex_app import modelos as mod

MAX_HISTORIAL = 60
MAX_RECIENTES = 12


class Historial(QObject):
    cambiado = Signal()
    recientesCambiados = Signal()
    seleccionCambiada = Signal()
    elegido = Signal(str)               # la ruta del documento de la fila elegida

    def __init__(self, consola, parent=None):
        super().__init__(parent)
        self.consola = consola
        self._s = QSettings()
        self._tabla = ModeloTabla(mod.COLUMNAS_HISTORIAL, parent=self)
        self._modelo = ModeloFiltrado(self._tabla, parent=self)
        self._fila = -1
        self._pintar()

    modelo = Property(QObject, lambda self: self._modelo, constant=True)
    tabla = Property(QObject, lambda self: self._tabla, constant=True)

    # ------------------------------------------------------------- lista
    def _lista(self, clave: str) -> list:
        try:
            v = json.loads(self._s.value(clave, "[]") or "[]")
            return v if isinstance(v, list) else []
        except (ValueError, TypeError):
            return []

    def _guardar(self, clave: str, valor: list) -> None:
        self._s.setValue(clave, json.dumps(valor, ensure_ascii=False))

    def entradas(self) -> list[dict]:
        return [h for h in self._lista("historial") if isinstance(h, dict) and h.get("tex")]

    def _pintar(self) -> None:
        self._tabla.poner([mod.fila_historial(h) for h in self.entradas()])
        self.cambiado.emit()

    def anotar(self, tex: Path, ok: bool, segundos: float, detalle: str, errores: int = 0, avisos: int = 0) -> None:
        """Una compilación más (la primera de la lista) y el documento a recientes."""
        entrada = {"tex": str(tex), "ok": ok, "segundos": round(segundos, 1), "detalle": detalle, "cuando": time.strftime("%Y-%m-%d %H:%M"),
                   "errores": errores, "avisos": avisos}
        self._guardar("historial", ([entrada] + self.entradas())[:MAX_HISTORIAL])
        self.recordar(tex)
        self._pintar()

    def ultima_de(self, tex: str) -> dict:
        return next((h for h in self.entradas() if h.get("tex") == tex), {})

    @Property(int, notify=cambiado)
    def total(self) -> int:
        return self._tabla.filas

    @Slot(int)
    def quitar(self, fila_visible: int) -> None:
        """Quita esa compilación del historial (solo de la lista)."""
        if fila_visible < 0:
            return
        origen = self._modelo.filaOrigen(fila_visible)
        entradas = self.entradas()
        if 0 <= origen < len(entradas):
            del entradas[origen]
            self._guardar("historial", entradas)
            self._pintar()
            self.fijarFila(-1)

    @Slot()
    def vaciar(self) -> None:
        self._guardar("historial", [])
        self._pintar()
        self.fijarFila(-1)
        self.consola.registrar("info", "Historial vaciado")

    # --------------------------------------------------------- selección
    @Slot(int)
    def fijarFila(self, fila_visible: int) -> None:
        self._fila = self._modelo.filaOrigen(fila_visible) if fila_visible >= 0 else -1
        self.seleccionCambiada.emit()
        if self._fila >= 0:
            self.elegido.emit(self._tabla.fila(self._fila).get("ruta", ""))

    @Property(int, notify=seleccionCambiada)
    def filaActual(self) -> int:
        return self._fila

    @Property(bool, notify=seleccionCambiada)
    def haySeleccion(self) -> bool:
        return self._fila >= 0

    # ---------------------------------------------------------- recientes
    def recientes(self) -> list[str]:
        return [r for r in self._lista("recientes") if isinstance(r, str) and Path(r).is_file()]

    def recordar(self, tex: Path) -> None:
        lista = [str(tex)] + [r for r in self._lista("recientes") if r != str(tex)]
        self._guardar("recientes", lista[:MAX_RECIENTES])
        self.recientesCambiados.emit()
