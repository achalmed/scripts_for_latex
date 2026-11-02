"""latex_app/controladores/ajustes.py — las preferencias de LaTeX Studio, en QSettings (nunca en el repo, R2):

- las carpetas de trabajo: las de omisión (`WRITING_DIR` y `DESPACHO_DIR` de `core/env.py`, las que existan; se pueden
  desactivar) y las que el usuario añade con el diálogo de carpetas; la profundidad del recorrido;
- las rutas de TeX extra (TEXINPUTS) para compilar con `main.sh` o latexmk documentos de un marco que no está instalado;
- el editor: tamaño de letra, ajuste de líneas, compilar al guardar;
- el editor externo («Abrir en Kate») y la terminal.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from gui_comun.qt import QObject, QSettings, Property, Signal, Slot

from latex_app import proyectos as pr

VARIABLES_OMISION = (("WRITING_DIR", "Escritura"), ("DESPACHO_DIR", "Despacho"))


def ruta_de_entorno(variable: str) -> str:
    """La ruta de una variable de `core/env.py`; el entorno manda (las pruebas apuntan a temporales)."""
    if os.environ.get(variable):
        return os.environ[variable]
    try:
        from gui_comun import rutas
        return str(rutas.variable(variable))
    except Exception:                    # fuera del espacio de trabajo no hay core/env.py: sin carpeta por omisión
        return ""


class Ajustes(QObject):
    cambiado = Signal()
    carpetasCambiadas = Signal()
    guardado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._s = QSettings()

    # ------------------------------------------------------------- genéricos
    def _lista(self, clave: str) -> list:
        try:
            v = json.loads(self._s.value(clave, "[]") or "[]")
            return v if isinstance(v, list) else []
        except (TypeError, ValueError):
            return []

    def _poner_lista(self, clave: str, valor: list) -> None:
        self._s.setValue(clave, json.dumps(valor, ensure_ascii=False))

    def _bool(self, clave: str, defecto: bool) -> bool:
        return self._s.value(clave, defecto) in (True, "true", "True", 1, "1")

    # ------------------------------------------------------------- carpetas de trabajo
    def omision(self) -> list[dict]:
        salida = []
        for variable, nombre in VARIABLES_OMISION:
            ruta = ruta_de_entorno(variable)
            if ruta:
                salida.append({"nombre": nombre, "ruta": ruta, "variable": variable, "existe": os.path.isdir(ruta)})
        return salida

    def raices(self) -> list[tuple[str, Path]]:
        """Las carpetas que se recorren: las de omisión activas y existentes, más las del usuario que existan."""
        desactivadas = set(self._lista("proyectos/desactivadas"))
        salida = [(o["nombre"], Path(o["ruta"])) for o in self.omision() if o["existe"] and o["ruta"] not in desactivadas]
        vistas = {str(r) for _n, r in salida}
        for ruta in self._lista("proyectos/carpetas"):
            if isinstance(ruta, str) and os.path.isdir(ruta) and ruta not in vistas:
                salida.append((os.path.basename(ruta.rstrip("/")) or ruta, Path(ruta)))
                vistas.add(ruta)
        return salida

    def despacho(self) -> Path | None:
        ruta = ruta_de_entorno("DESPACHO_DIR")
        return Path(ruta) if ruta and os.path.isdir(ruta) else None

    @Property("QVariantList", notify=carpetasCambiadas)
    def carpetas(self) -> list:
        """Para la página de ajustes y la navegación: nombre, ruta, de dónde sale, si existe y si está activa."""
        desactivadas = set(self._lista("proyectos/desactivadas"))
        filas = [{"nombre": o["nombre"], "ruta": o["ruta"], "origen": f"por omisión ({o['variable']})", "existe": o["existe"],
                  "activa": o["ruta"] not in desactivadas, "quitable": False} for o in self.omision()]
        filas += [{"nombre": os.path.basename(r.rstrip("/")) or r, "ruta": r, "origen": "añadida", "existe": os.path.isdir(r),
                   "activa": True, "quitable": True} for r in self._lista("proyectos/carpetas") if isinstance(r, str)]
        return filas

    @Slot(str, result=str)
    def anadirCarpeta(self, ruta: str) -> str:
        ruta = os.path.abspath(os.path.expanduser((ruta or "").strip())) if (ruta or "").strip() else ""
        if not ruta or not os.path.isdir(ruta):
            return f"No es una carpeta: {ruta or '(vacío)'}"
        lista = [r for r in self._lista("proyectos/carpetas") if r != ruta]
        if ruta in {o["ruta"] for o in self.omision()}:
            self.activarCarpeta(ruta, True)
            return ""
        self._poner_lista("proyectos/carpetas", lista + [ruta])
        self.carpetasCambiadas.emit()
        return ""

    @Slot(str)
    def quitarCarpeta(self, ruta: str) -> None:
        """Quita una carpeta añadida de la lista (la carpeta no se toca)."""
        self._poner_lista("proyectos/carpetas", [r for r in self._lista("proyectos/carpetas") if r != ruta])
        self.carpetasCambiadas.emit()

    @Slot(str, bool)
    def activarCarpeta(self, ruta: str, activa: bool) -> None:
        """Activa o desactiva una carpeta por omisión (no se borra de la lista: se deja de recorrer)."""
        desactivadas = [r for r in self._lista("proyectos/desactivadas") if r != ruta]
        if not activa:
            desactivadas.append(ruta)
        self._poner_lista("proyectos/desactivadas", desactivadas)
        self.carpetasCambiadas.emit()

    def _profundidad_get(self) -> int:
        try:
            return max(1, min(12, int(self._s.value("proyectos/profundidad", pr.PROFUNDIDAD))))
        except (TypeError, ValueError):
            return pr.PROFUNDIDAD

    def _profundidad_set(self, v: int) -> None:
        v = max(1, min(12, int(v)))
        if v != self._profundidad_get():
            self._s.setValue("proyectos/profundidad", v)
            self.carpetasCambiadas.emit()

    profundidad = Property(int, _profundidad_get, _profundidad_set, notify=carpetasCambiadas)

    # ------------------------------------------------------------- rutas de TeX
    def _rutas_tex_get(self) -> list:
        return [r for r in self._lista("compilar/rutas_tex") if isinstance(r, str)]

    rutasTex = Property("QVariantList", _rutas_tex_get, notify=cambiado)

    @Slot(str, result=str)
    def anadirRutaTex(self, ruta: str) -> str:
        ruta = os.path.abspath(os.path.expanduser((ruta or "").strip())) if (ruta or "").strip() else ""
        if not ruta or not os.path.isdir(ruta):
            return f"No es una carpeta: {ruta or '(vacío)'}"
        self._poner_lista("compilar/rutas_tex", [r for r in self._rutas_tex_get() if r != ruta] + [ruta])
        self.cambiado.emit()
        return ""

    @Slot(str)
    def quitarRutaTex(self, ruta: str) -> None:
        self._poner_lista("compilar/rutas_tex", [r for r in self._rutas_tex_get() if r != ruta])
        self.cambiado.emit()

    # ------------------------------------------------------------- editor
    def _tamano_get(self) -> int:
        try:
            return max(7, min(32, int(self._s.value("editor/tamano", 0) or 0))) if self._s.value("editor/tamano") else 0
        except (TypeError, ValueError):
            return 0

    def _tamano_set(self, v: int) -> None:
        self._s.setValue("editor/tamano", max(0, min(32, int(v))))
        self.cambiado.emit()

    tamanoLetra = Property(int, _tamano_get, _tamano_set, notify=cambiado)       # 0: el de la fuente fija del sistema
    ajustarLineas = Property(bool, lambda self: self._bool("editor/ajustar", True),
                             lambda self, v: (self._s.setValue("editor/ajustar", bool(v)), self.cambiado.emit()), notify=cambiado)
    compilarAlGuardar = Property(bool, lambda self: self._bool("editor/compilar_al_guardar", False),
                                 lambda self, v: (self._s.setValue("editor/compilar_al_guardar", bool(v)), self.cambiado.emit()), notify=cambiado)

    # ------------------------------------------------------------- sistema
    def _texto(self, clave: str, defecto: str) -> str:
        return str(self._s.value(clave, defecto) or defecto)

    editor = Property(str, lambda self: self._texto("sistema/editor", "kate"),
                      lambda self, v: (self._s.setValue("sistema/editor", (v or "").strip() or "kate"), self.cambiado.emit()), notify=cambiado)
    terminal = Property(str, lambda self: self._texto("sistema/terminal", "konsole"),
                        lambda self, v: (self._s.setValue("sistema/terminal", (v or "").strip() or "konsole"), self.cambiado.emit()), notify=cambiado)

    @Slot()
    def guardar(self) -> None:
        self._s.sync()
        self.cambiado.emit()
        self.guardado.emit()
