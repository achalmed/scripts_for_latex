"""latex_app/controladores/miniaturas.py — las miniaturas para QML: `url(pdf)` devuelve la imagen si ya está y, si no, la pide a un hilo y avisa con `lista(pdf)` cuando existe (latex_app/miniaturas.py).

Objetivo: que la página de proyectos pinte sus tarjetas al instante y las miniaturas lleguen solas, sin congelar la
  ventana con pdftoppm (decisiones §1.17).
Método: una cola en un hilo de fondo, un PDF a la vez y una sola vez por versión del PDF; `version` sube con cada una
  que llega, para que un `Image` que la lee vuelva a pedir su `url`.
Límite: sin pdftoppm, `url` devuelve "" y la tarjeta muestra el icono de su estado.
"""
from __future__ import annotations

import queue
import threading
from pathlib import Path

from gui_comun.qt import QObject, QUrl, Property, Signal, Slot

from latex_app import miniaturas as mn


class Miniaturas(QObject):
    lista = Signal(str)                  # el PDF cuya miniatura ya existe
    versionCambiada = Signal()

    def __init__(self, cache: Path, parent=None):
        super().__init__(parent)
        self._cache = Path(cache)
        self._cola: queue.Queue = queue.Queue()
        self._pedidos: set[str] = set()
        self._version = 0
        self._hilo = threading.Thread(target=self._trabajar, name="miniaturas", daemon=True)
        self._hilo.start()
        self.lista.connect(self._subir)

    def _get_version(self): return self._version
    version = Property(int, _get_version, notify=versionCambiada)

    def _subir(self, _pdf: str) -> None:
        self._version += 1
        self.versionCambiada.emit()

    def _trabajar(self) -> None:
        while True:
            pdf = self._cola.get()
            if pdf is None:
                return
            if mn.generar(pdf, self._cache) is not None:
                self.lista.emit(pdf)

    @Slot(str, result=str)
    def url(self, pdf: str) -> str:
        """La URL de la miniatura de `pdf` si ya existe; si no, "" y la pide (llega por `lista`)."""
        if not pdf:
            return ""
        d = mn.destino(pdf, self._cache)
        if d is None:
            return ""
        if d.is_file():
            return QUrl.fromLocalFile(str(d)).toString()
        clave = str(d)
        if clave not in self._pedidos:
            self._pedidos.add(clave)
            self._cola.put(pdf)
        return ""

    def apagar(self) -> None:
        self._cola.put(None)
