"""latex_app/controladores/configuracion.py — la configuración del documento (Ctrl+Alt+D): lo que el esquema
`latex-studio.yml` de su marco permite configurar, con los valores actuales, los cambios pendientes, la diferencia y
la escritura confirmada (`docs/configuracion-de-documentos.md`). Python calcula y escribe; QML pinta el formulario y
pide confirmación antes de `aplicar`.
"""

from __future__ import annotations

from pathlib import Path

from gui_comun.qt import QObject, Property, Signal, Slot

from latex_app import configuracion as cf


class ConfiguracionDocumento(QObject):
    cambiado = Signal()
    aplicado = Signal(str)                # el principal, tras escribir

    def __init__(self, consola, editor=None, rutas=None, parent=None):
        super().__init__(parent)
        self.consola = consola
        self.editor = editor
        self.rutas = rutas or (lambda: [])          # dónde buscar la clase de un documento fuera del árbol de su marco
        self._conf: cf.Configuracion | None = None
        self._pendientes: dict[str, object] = {}
        self._cambios: list[cf.Cambio] = []

    # ------------------------------------------------------------------ propiedades
    def _secciones(self) -> list:
        if self._conf is None:
            return []
        salida = []
        for s in self._conf.secciones:
            d = s.a_dict()
            for c in d["campos"]:
                if c["clave"] in self._pendientes:
                    c["valor"] = self._pendientes[c["clave"]]
            salida.append(d)
        return salida

    secciones = Property("QVariantList", _secciones, notify=cambiado)
    principal = Property(str, lambda s: str(s._conf.principal) if s._conf else "", notify=cambiado)
    nombre = Property(str, lambda s: s._conf.nombre if s._conf else "", notify=cambiado)
    marco = Property(str, lambda s: s._conf.marco if s._conf else "", notify=cambiado)
    clase = Property(str, lambda s: s._conf.clase if s._conf else "", notify=cambiado)
    esquema = Property(str, lambda s: str(s._conf.esquema) if s._conf and s._conf.esquema else "", notify=cambiado)
    pendientes = Property(int, lambda s: len(s._pendientes), notify=cambiado)

    # ------------------------------------------------------------------ operaciones
    @Slot(str, result=str)
    def abrir(self, ruta: str) -> str:
        """Lee lo configurable del documento; devuelve el error o ""."""
        self._pendientes, self._cambios = {}, []
        if not ruta or not Path(ruta).is_file():
            self._conf = None
            self.cambiado.emit()
            return "No hay un documento que configurar: elige o abre un proyecto."
        try:
            self._conf = cf.configuracion_de(Path(ruta), rutas=[Path(r) for r in self.rutas()])
        except (cf.ErrorEsquema, OSError) as e:
            self._conf = None
            self.cambiado.emit()
            return str(e)
        self.cambiado.emit()
        return ""

    @Slot(str, "QVariant")
    def fijar(self, clave: str, valor) -> None:
        if self._conf is None:
            return
        campo = self._conf.campos().get(clave)
        if campo is None:
            return
        if valor == campo.valor:
            self._pendientes.pop(clave, None)
        else:
            self._pendientes[clave] = valor
        self.cambiado.emit()

    @Slot()
    def descartar(self) -> None:
        self._pendientes, self._cambios = {}, []
        self.cambiado.emit()

    @Slot(result=str)
    def diferencia(self) -> str:
        """La diferencia de todos los archivos que se tocarían (vacía si no cambia nada). No escribe."""
        if self._conf is None or not self._pendientes:
            self._cambios = []
            return ""
        self._cambios = cf.cambios(self._conf, self._pendientes)
        return "\n".join(c.diferencia() for c in self._cambios)

    @Slot(result=str)
    def aplicar(self) -> str:
        """Escribe la diferencia calculada; devuelve el error o "". No pisa un archivo con cambios sin guardar."""
        if self._conf is None or not self._cambios:
            return "No hay cambios que aplicar."
        sucios = set(self.editor.modificados()) if self.editor is not None else set()
        tocados = [c.archivo for c in self._cambios if str(c.archivo) in sucios]
        if tocados:
            return f"{tocados[0].name} tiene cambios sin guardar en el editor: guárdalos o descártalos antes."
        try:
            escritos = cf.aplicar(self._cambios)
        except (cf.ErrorEsquema, OSError) as e:
            return str(e)
        principal = str(self._conf.principal)
        for a in escritos:
            self.consola.registrar("info", f"Configuración del documento escrita en {a}")
        self.abrir(principal)
        self.aplicado.emit(principal)
        return ""
