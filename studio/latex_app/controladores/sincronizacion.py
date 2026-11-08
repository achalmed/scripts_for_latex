"""latex_app/controladores/sincronizacion.py — trabajar junto a TeXstudio (u otro editor): vigila el proyecto abierto.

Las fuentes del proyecto (principal, `\\input`, `.bib`) y su PDF se vigilan con un `QFileSystemWatcher`, también los que
no están abiertos en el editor. Cuando otro programa guarda una fuente, la ventana relee la estructura y, si el ajuste
lo pide, compila; cuando otro programa compila (el PDF cambia sin que compile la ventana), el visor recarga el PDF
conservando la página. Los cambios llegan agrupados (TeXstudio escribe en varias pasadas): se espera un momento antes
de reaccionar. El vigía se crea al abrir un proyecto y se retira con `soltar()` (su notificador de inotify no
sobrevive a que Python recoja el objeto; la misma trampa que el del editor).
"""

from __future__ import annotations

import os
from pathlib import Path

from gui_comun.qt import QFileSystemWatcher, QObject, QTimer, Signal

ESPERA_MS = 700


class Sincronizacion(QObject):
    fuentesCambiadas = Signal("QVariantList")   # rutas de fuentes que cambiaron fuera de la ventana
    pdfCambiado = Signal(str)                   # el PDF del proyecto cambió fuera de la ventana

    def __init__(self, parent=None):
        super().__init__(parent)
        self._vigia: QFileSystemWatcher | None = None
        self._fuentes: set[str] = set()
        self._pdf = ""
        self._firma_pdf: tuple = ()
        self._pendientes: set[str] = set()
        self._t_fuentes = QTimer(self, singleShot=True, interval=ESPERA_MS)
        self._t_fuentes.timeout.connect(self._avisar_fuentes)
        self._t_pdf = QTimer(self, singleShot=True, interval=ESPERA_MS)
        self._t_pdf.timeout.connect(self._avisar_pdf)

    @staticmethod
    def _firma(ruta: str) -> tuple:
        try:
            st = os.stat(ruta)
            return (st.st_mtime_ns, st.st_size)
        except OSError:
            return ()

    def vigilar(self, fuentes: list[str], pdf: str) -> None:
        """Pasa a vigilar estas fuentes y este PDF (aunque aún no exista: se vigila su carpeta)."""
        if self._vigia is None:
            self._vigia = QFileSystemWatcher(self)
            self._vigia.fileChanged.connect(self._cambio)
            self._vigia.directoryChanged.connect(self._carpeta)
        actuales = self._vigia.files() + self._vigia.directories()
        if actuales:
            self._vigia.removePaths(actuales)
        self._fuentes = {str(Path(f)) for f in fuentes if f and os.path.isfile(f)}
        self._pdf = str(Path(pdf)) if pdf else ""
        self._firma_pdf = self._firma(self._pdf) if self._pdf else ()
        rutas = sorted(self._fuentes)
        if self._pdf and os.path.isfile(self._pdf):
            rutas.append(self._pdf)
        if self._pdf and os.path.isdir(os.path.dirname(self._pdf)):
            rutas.append(os.path.dirname(self._pdf))      # el PDF se reemplaza al compilar (o aún no existe)
        if rutas:
            self._vigia.addPaths(rutas)

    def olvidar(self) -> None:
        self.vigilar([], "")

    def anotar_pdf_propio(self) -> None:
        """La ventana acaba de compilar: el PDF nuevo es suyo y no debe tomarse por un cambio de fuera."""
        self._firma_pdf = self._firma(self._pdf) if self._pdf else ()

    def _revigilar(self, ruta: str) -> None:
        if self._vigia is not None and os.path.exists(ruta) and ruta not in self._vigia.files():
            self._vigia.addPath(ruta)              # los editores guardan reemplazando el archivo

    def _cambio(self, ruta: str) -> None:
        self._revigilar(ruta)
        if ruta == self._pdf:
            self._t_pdf.start()
        elif ruta in self._fuentes:
            self._pendientes.add(ruta)
            self._t_fuentes.start()

    def _carpeta(self, _carpeta: str) -> None:
        if self._pdf and self._firma(self._pdf) != self._firma_pdf:
            self._revigilar(self._pdf)
            self._t_pdf.start()

    def _avisar_fuentes(self) -> None:
        rutas, self._pendientes = sorted(self._pendientes), set()
        if rutas:
            self.fuentesCambiadas.emit(rutas)

    def _avisar_pdf(self) -> None:
        firma = self._firma(self._pdf)
        if firma and firma != self._firma_pdf:
            self._firma_pdf = firma
            self.pdfCambiado.emit(self._pdf)

    def soltar(self) -> None:
        """Retira el vigía dentro del bucle de eventos. Llámese al cerrar la ventana."""
        if self._vigia is not None:
            self._vigia.fileChanged.disconnect(self._cambio)
            self._vigia.directoryChanged.disconnect(self._carpeta)
            self._vigia.deleteLater()
            self._vigia = None
