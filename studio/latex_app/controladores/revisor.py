"""latex_app/controladores/revisor.py — el revisor del editor: estilo de la redacción y LaTeX del archivo abierto, con reglas explicadas y citadas, que sugiere y nunca reescribe (pestaña «Revisión» del panel inferior; Ctrl+Alt+R).

Objetivo: revisar el texto mientras se escribe, no solo al final (decisiones §1.23; mejoras C6.1, C6.2 y C13.2 del flujo
  de conocimiento): cada hallazgo con su línea, lo que se halló, qué considerar y la línea tenue «por qué · fuente» de su
  regla; un clic lleva a la línea. El perfil de lector del documento (académico, decisor, estudiante) lo decide el marco.
Método: la orden `revisar` de la sección `revisor:` del `latex-studio.yml` del marco (contrato §14) recibe una copia del
  texto del editor (con lo no guardado) en un archivo de la caché (`{archivo}`) y la ruta real (`{ruta}`), y devuelve
  {perfil, reglas, hallazgos}; `datos.resultado_revisor` junta cada hallazgo con su regla. Corre en un hilo al pedirlo y
  al guardar; el último pedido manda.
Límite: la ventana no sabe qué es una nominalización ni qué paquete es obsoleto: lo dice el marco. Nada se cambia en el
  texto: las sugerencias se leen y el autor decide. Sin la sección, la pestaña dice que el marco no declara revisor.
"""
from __future__ import annotations

import os
from pathlib import Path

from gui_comun.qt import QObject, Property, Signal, Slot

from latex_app import datos


def _cache() -> Path:
    d = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "latex-studio" / "revisor"
    d.mkdir(parents=True, exist_ok=True)
    return d


class RevisorEditor(QObject):
    cambiado = Signal()
    resultadoCambiado = Signal()

    def __init__(self, proyectos, tareas, consola, parent=None):
        super().__init__(parent)
        self.proyectos, self.tareas, self.consola = proyectos, tareas, consola
        self._decl: dict | None = None
        self._resultado = datos.resultado_revisor({})
        self._ruta = ""
        self._revisando = False
        self._pedido = 0
        proyectos.abiertoCambiado.connect(self.recargar)

    def _get_disponible(self): return self._decl is not None
    disponible = Property(bool, _get_disponible, notify=cambiado)

    def _get_resultado(self): return self._resultado
    resultado = Property("QVariantMap", _get_resultado, notify=resultadoCambiado)

    def _get_ruta(self): return self._ruta
    ruta = Property(str, _get_ruta, notify=resultadoCambiado)

    def _get_revisando(self): return self._revisando
    revisando = Property(bool, _get_revisando, notify=resultadoCambiado)

    @Slot()
    def recargar(self) -> None:
        self._decl = datos.declaracion_seccion(self.proyectos.principal, "revisor") if self.proyectos.hayAbierto else None
        self._resultado = datos.resultado_revisor({})
        self._ruta = ""
        self.cambiado.emit()
        self.resultadoCambiado.emit()

    @Slot(str)
    def revisarArchivo(self, ruta: str) -> None:
        """Al guardar: el archivo tal como quedó en el disco."""
        if self._decl and ruta.endswith(".tex"):
            try:
                self.revisar(ruta, Path(ruta).read_text(encoding="utf-8", errors="replace"))
            except OSError:
                return

    @Slot(str, str)
    def revisar(self, ruta: str, texto: str) -> None:
        """El archivo `ruta` tal como está en el editor (`texto`); `resultado` trae los hallazgos."""
        if not self._decl or not ruta or not ruta.endswith(".tex"):
            return
        decl = dict(self._decl)
        self._pedido += 1
        pedido = self._pedido
        copia = _cache() / f"editor-{pedido % 4}.tex"
        copia.write_text(texto or "", encoding="utf-8")
        argv = datos.con(decl["revisar"], archivo=str(copia), ruta=ruta)
        self._revisando = True
        self.resultadoCambiado.emit()

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["proyecto"], tope=30)

        def fin(r):
            if pedido != self._pedido:
                return
            dato, error = r
            self._resultado = datos.resultado_revisor(dato if dato is not None else {"error": error})
            self._ruta = ruta
            self._revisando = False
            if self._resultado["error"]:
                self.consola.registrar("warn", f"Revisión: {self._resultado['error']}")
            self.resultadoCambiado.emit()
        self.tareas.funcion("Revisar el estilo", trabajo, silenciosa=True, operacion="lectura", error=False, al_terminar=fin)
