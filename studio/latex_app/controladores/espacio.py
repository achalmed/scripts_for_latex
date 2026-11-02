"""latex_app/controladores/espacio.py — lo transversal: la vista activa (Carpeta de trabajo · Recientes · Historial), la
carpeta de trabajo y las carpetas recientes (QSettings), el resumen y el contexto de la barra de estado y las acciones
sobre una ruta (abrir con el sistema, Dolphin, terminal, portapapeles, el editor en una línea)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from gui_comun.qt import QGuiApplication, QObject, QSettings, Property, Signal, Slot
from gui_comun.rutas import docs_root

VISTAS = (("carpeta", "Carpeta de trabajo", "folder-open"), ("recientes", "Recientes", "document-open-recent"),
          ("historial", "Compilaciones", "view-history"))
NOMBRES_VISTAS = tuple(v[0] for v in VISTAS)
MAX_CARPETAS = 8


class Espacio(QObject):
    vistaCambiada = Signal()
    carpetaCambiada = Signal()
    carpetasCambiadas = Signal()
    resumenCambiado = Signal()
    contextoCambiado = Signal()
    aviso = Signal(str, str)                 # texto, tipo (informacion · positivo · aviso · error)

    def __init__(self, consola, ajustes=None, parent=None):
        super().__init__(parent)
        self.consola, self.ajustes = consola, ajustes
        self._s = QSettings()
        self._vista = NOMBRES_VISTAS[0]
        self._carpeta = ""
        self._resumen = ""
        self._contexto = ""
        inicial = str(self._s.value("carpeta", "") or "")
        self.fijarCarpeta(inicial if os.path.isdir(inicial) else str(docs_root()))

    # ------------------------------------------------------------- vista
    @Property("QVariantList", constant=True)
    def vistas(self) -> list:
        return [{"nombre": n, "texto": t, "icono": i} for n, t, i in VISTAS]

    @Property(str, notify=vistaCambiada)
    def vista(self) -> str:
        return self._vista

    @Property(int, notify=vistaCambiada)
    def indiceVista(self) -> int:
        return NOMBRES_VISTAS.index(self._vista)

    @Property(str, notify=vistaCambiada)
    def textoVista(self) -> str:
        return next(t for n, t, _i in VISTAS if n == self._vista)

    @Slot(str)
    def fijarVista(self, nombre: str) -> None:
        if nombre in NOMBRES_VISTAS and nombre != self._vista:
            self._vista = nombre
            self.vistaCambiada.emit()

    @Slot(int)
    def fijarVistaPorIndice(self, i: int) -> None:
        if 0 <= i < len(NOMBRES_VISTAS):
            self.fijarVista(NOMBRES_VISTAS[i])

    # ----------------------------------------------------------- carpeta
    @Property(str, notify=carpetaCambiada)
    def carpeta(self) -> str:
        return self._carpeta

    @Property(str, notify=carpetaCambiada)
    def nombreCarpeta(self) -> str:
        return os.path.basename(self._carpeta.rstrip("/")) or self._carpeta

    @Slot(str, result=str)
    def fijarCarpeta(self, ruta: str) -> str:
        """Cambia la carpeta de trabajo; devuelve el error si no es una carpeta (y no cambia nada)."""
        ruta = os.path.abspath(os.path.expanduser(ruta.strip())) if ruta.strip() else ""
        if not ruta or not os.path.isdir(ruta):
            return f"No es una carpeta: {ruta or '(vacío)'}"
        if ruta == self._carpeta:
            return ""
        self._carpeta = ruta
        self._s.setValue("carpeta", ruta)
        recientes = [ruta] + [c for c in self.carpetas_recientes() if c != ruta]
        self._s.setValue("carpetas", json.dumps(recientes[:MAX_CARPETAS], ensure_ascii=False))
        self.carpetaCambiada.emit()
        self.carpetasCambiadas.emit()
        return ""

    @Slot()
    def subir(self) -> None:
        self.fijarCarpeta(os.path.dirname(self._carpeta.rstrip("/")) or "/")

    def carpetas_recientes(self) -> list[str]:
        try:
            lista = json.loads(self._s.value("carpetas", "[]") or "[]")
        except (ValueError, TypeError):
            lista = []
        return [c for c in lista if isinstance(c, str) and os.path.isdir(c)]

    @Property("QVariantList", notify=carpetasCambiadas)
    def filasCarpetas(self) -> list:
        """Las carpetas recientes para la navegación (`dir:<ruta>`), la actual la primera."""
        return [{"nombre": f"dir:{c}", "texto": os.path.basename(c.rstrip("/")) or c, "icono": "folder", "contador": ""}
                for c in self.carpetas_recientes()]

    # ------------------------------------------------------ barra de estado
    @Property(str, notify=resumenCambiado)
    def resumen(self) -> str:
        return self._resumen

    @Slot(str)
    def fijarResumen(self, texto: str) -> None:
        if texto != self._resumen:
            self._resumen = texto
            self.resumenCambiado.emit()

    @Property(str, notify=contextoCambiado)
    def contexto(self) -> str:
        return self._contexto

    @Slot(str)
    def fijarContexto(self, texto: str) -> None:
        if texto != self._contexto:
            self._contexto = texto
            self.contextoCambiado.emit()

    # ------------------------------------------------------- sobre una ruta
    def _ruta(self, ruta: str) -> str:
        return ruta or self._carpeta

    @Slot(str)
    def abrir(self, ruta: str) -> None:
        """Un archivo o carpeta con la aplicación del sistema (xdg-open)."""
        ruta = self._ruta(ruta)
        if os.path.exists(ruta):
            subprocess.Popen(["xdg-open", ruta])
            self.consola.registrar("info", f"Abierto con el sistema: {ruta}")
        else:
            self.aviso.emit(f"No existe: {ruta}", "aviso")

    @Slot(str)
    def abrirDolphin(self, ruta: str) -> None:
        ruta = self._ruta(ruta)
        carpeta = ruta if os.path.isdir(ruta) else os.path.dirname(ruta)
        if os.path.isdir(carpeta):
            subprocess.Popen(["xdg-open", carpeta])
        else:
            self.aviso.emit(f"No existe la carpeta: {carpeta}", "aviso")

    def _terminal(self) -> str:
        preferido = (self.ajustes.terminal if self.ajustes is not None else "konsole") or "konsole"
        for candidato in (preferido, "konsole", "x-terminal-emulator"):
            if shutil.which(candidato):
                return candidato
        return ""

    @Slot(str)
    def abrirTerminal(self, ruta: str) -> None:
        ruta = self._ruta(ruta)
        carpeta = ruta if os.path.isdir(ruta) else os.path.dirname(ruta)
        if not os.path.isdir(carpeta):
            return
        terminal = self._terminal()
        if terminal == "konsole":
            subprocess.Popen(["konsole", "--workdir", carpeta])
        elif terminal:
            subprocess.Popen([terminal], cwd=carpeta)
        else:
            self.aviso.emit("No se encontró un emulador de terminal (konsole).", "aviso")

    @Slot(str)
    def copiarRuta(self, ruta: str) -> None:
        ruta = self._ruta(ruta)
        QGuiApplication.clipboard().setText(ruta)
        self.consola.registrar("info", f"Ruta copiada: {ruta}")

    def orden_editor(self, ruta: str, linea: int = 0) -> list[str]:
        """La orden que abre `ruta` en el editor preferido, en la línea si la admite (Kate, KWrite, VS Code); si no hay
        ninguno, con la aplicación del sistema. Vacía si no existe el archivo."""
        if not os.path.isfile(ruta):
            return []
        preferido = (self.ajustes.editor if self.ajustes is not None else "kate") or "kate"
        for editor in (preferido, "kate", "kwrite", "code"):
            if shutil.which(editor):
                if editor in ("kate", "kwrite"):
                    return [editor, "--line", str(linea or 1), ruta]
                if editor == "code":
                    return [editor, "-g", f"{ruta}:{linea or 1}"]
                return [editor, ruta]
        return ["xdg-open", ruta]

    @Slot(str, int)
    def abrirEnEditor(self, ruta: str, linea: int = 0) -> None:
        orden = self.orden_editor(ruta, linea)
        if not orden:
            self.aviso.emit(f"No existe: {ruta}", "aviso")
            return
        subprocess.Popen(orden)
        self.consola.registrar("info", "Editor: " + " ".join(orden))

    # --------------------------------------------------------------- paleta
    def entradas_paleta(self, _texto: str) -> list[dict]:
        """«Ir a <vista>» y «Carpeta: …» (las recientes) para la paleta de órdenes."""
        salida = [{"nombre": f"ir.{n}", "texto": f"Ir a {t}", "grupo": "Vistas", "icono": i, "ejecutar": lambda n=n: self.fijarVista(n)}
                  for n, t, i in VISTAS]
        salida += [{"nombre": f"dir.{c}", "texto": f"Carpeta: {os.path.basename(c.rstrip('/')) or c}", "grupo": "Carpetas", "icono": "folder",
                    "ejecutar": lambda c=c: (self.fijarCarpeta(c), self.fijarVista("carpeta"))} for c in self.carpetas_recientes()]
        return salida
