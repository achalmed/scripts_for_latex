"""latex_app/controladores/ajustes.py — «Configurar LaTeX Studio…»: las dos preferencias que la ventana usa, en QSettings:
el editor con el que se abre un `.tex` en una línea («Ir a la línea»: `kate --line N`, o VS Code con `-g`) y la terminal
de «Abrir terminal aquí». Las opciones de compilación no están aquí: viven en la pestaña Opciones (`opciones.py`)."""

from __future__ import annotations

from gui_comun.qt import QObject, QSettings, Property, Signal, Slot

EDITORES = ("kate", "code", "kwrite", "gedit")


class Ajustes(QObject):
    cambiado = Signal()
    guardado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._s = QSettings()

    def _editor_get(self) -> str:
        return str(self._s.value("sistema/editor", "kate") or "kate")

    def _editor_set(self, v: str) -> None:
        v = (v or "").strip() or "kate"
        if v != self._editor_get():
            self._s.setValue("sistema/editor", v)
            self.cambiado.emit()

    editor = Property(str, _editor_get, _editor_set, notify=cambiado)

    def _terminal_get(self) -> str:
        return str(self._s.value("sistema/terminal", "konsole") or "konsole")

    def _terminal_set(self, v: str) -> None:
        v = (v or "").strip() or "konsole"
        if v != self._terminal_get():
            self._s.setValue("sistema/terminal", v)
            self.cambiado.emit()

    terminal = Property(str, _terminal_get, _terminal_set, notify=cambiado)

    @Slot()
    def guardar(self) -> None:
        self._s.sync()
        self.cambiado.emit()
        self.guardado.emit()
