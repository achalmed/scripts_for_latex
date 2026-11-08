"""latex_app/instancia.py — una sola ventana de LaTeX Studio por usuario: `main.py --ir ARCHIVO LÍNEA` se lo pasa a la que
ya está abierta (el SyncTeX inverso de Okular, Mayús+clic, la llama así) y termina; si no hay ninguna, arranca y va ahí.

La ventana escucha con un `QLocalServer` en un socket propio del usuario (`$XDG_RUNTIME_DIR/latex-studio-<uid>.sock`); quien
envía es Python a secas (`socket`), sin arrancar Qt. El mensaje es una línea JSON `{"archivo": …, "linea": …}`.
"""

from __future__ import annotations

import json
import os
import socket
import tempfile

from gui_comun.qt import QObject, Signal

try:
    from PySide6.QtNetwork import QLocalServer
except ImportError:                                  # PyQt6
    from PyQt6.QtNetwork import QLocalServer         # type: ignore[no-redef]

NOMBRE = os.path.join(os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir(), f"latex-studio-{os.getuid()}.sock")


def argumentos_ir(argv: list[str]) -> tuple[str, int] | None:
    """(archivo, línea) de `--ir ARCHIVO LÍNEA` (Okular pasa `%f %l`), o None."""
    if "--ir" not in argv:
        return None
    i = argv.index("--ir")
    if i + 1 >= len(argv):
        return None
    archivo = os.path.abspath(argv[i + 1])
    try:
        linea = int(argv[i + 2]) if i + 2 < len(argv) else 0
    except ValueError:
        linea = 0
    return archivo, linea


def enviar(archivo: str, linea: int, nombre: str = NOMBRE) -> bool:
    """Pasa el salto a la ventana abierta; False si no hay ninguna."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect(nombre)
            s.sendall((json.dumps({"archivo": archivo, "linea": int(linea)}) + "\n").encode())
        return True
    except OSError:
        return False


def _hay_otra(nombre: str) -> bool:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect(nombre)
        return True
    except OSError:
        return False


class Servidor(QObject):
    """La ventana abierta escucha y emite `irA(archivo, linea)` por cada salto que le llega."""

    irA = Signal(str, int)

    def __init__(self, nombre: str = NOMBRE, parent=None):
        super().__init__(parent)
        self._servidor = QLocalServer(self)
        self.escuchando = False
        if _hay_otra(nombre):                        # otra ventana abierta: es ella la que recibe los saltos
            return
        QLocalServer.removeServer(nombre)            # el socket de una ventana que no cerró bien
        self.escuchando = self._servidor.listen(nombre)
        self._servidor.newConnection.connect(self._nueva)

    def _nueva(self) -> None:
        while self._servidor.hasPendingConnections():
            s = self._servidor.nextPendingConnection()
            s.readyRead.connect(lambda s=s: self._leer(s))

    def _leer(self, s) -> None:
        while s.canReadLine():
            try:
                datos = json.loads(bytes(s.readLine()).decode())
                self.irA.emit(str(datos["archivo"]), int(datos.get("linea") or 0))
            except (ValueError, KeyError, TypeError):
                pass

    def cerrar(self) -> None:
        self._servidor.close()
