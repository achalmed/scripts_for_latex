"""latex_app/controladores/corrida.py — compilar, simular y limpiar el documento actual por `script_compilar_latex/main.sh`
(la ventana no compila por su cuenta): la orden la arma `compilador.Opciones.orden()`, corre en `gui_comun.tareas` con
la salida íntegra en el panel inferior, el progreso por pasadas en la barra de estado («Pasada n/N» de la CLI) y Esc
para cancelar; el registro (`--log`) queda en la caché por documento (rediseño L4). Al terminar, la fila y los detalles
se releen del disco y la compilación entra al historial. Limpiar muestra antes la lista de lo que borraría (R3)."""

from __future__ import annotations

import time
from pathlib import Path

from gui_comun.qt import QObject, Property, Signal, Slot

from latex_app import compilador as svc


class Corrida(QObject):
    cambiado = Signal()
    terminada = Signal(str, bool)            # ruta del documento, si compiló
    aviso = Signal(str, str)

    def __init__(self, espacio, opciones, documentos, historial, consola, tareas, parent=None):
        super().__init__(parent)
        self.espacio, self.opciones, self.documentos, self.historial = espacio, opciones, documentos, historial
        self.consola, self.tareas = consola, tareas
        self._worker = None
        self._que = ""                 # compilar · simular · limpiar
        self._ruta = ""
        self._inicio = 0.0
        tareas.cambiada.connect(self.cambiado)
        documentos.actualCambiado.connect(self.cambiado)

    # ------------------------------------------------------------- estado
    @Property(bool, notify=cambiado)
    def enCurso(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    @Property(str, notify=cambiado)
    def que(self) -> str:
        return self._que if self.enCurso else ""

    @Property(str, notify=cambiado)
    def rutaEnCurso(self) -> str:
        return self._ruta if self.enCurso else ""

    @Property(bool, notify=cambiado)
    def puede(self) -> bool:
        return self.documentos.hayActual and not self.tareas.activa

    @Property(str, notify=cambiado)
    def motivo(self) -> str:
        if not self.documentos.hayActual:
            return "Abre un .tex (Ctrl+O) o elige uno en la tabla."
        if self.tareas.activa:
            return "Hay una operación en curso (Esc la cancela)."
        return ""

    def _tex(self) -> Path | None:
        return Path(self.documentos.actual) if self.documentos.hayActual else None

    # ------------------------------------------------------------- compilar y simular
    @Slot(result=bool)
    def compilar(self) -> bool:
        """F5: `main.sh` con las opciones de la sesión; el PDF y los auxiliares quedan junto al `.tex` (o en la carpeta de salida)."""
        return self._lanzar("compilar")

    @Slot(result=bool)
    def compilarConBiber(self) -> bool:
        """Ctrl+B: lo mismo, forzando Biber (3 pasadas) sin cambiar las opciones guardadas."""
        return self._lanzar("compilar", biber=True)

    @Slot(result=bool)
    def simular(self) -> bool:
        """Mayús+F5: `main.sh -n`, las órdenes que correría sin escribir nada."""
        return self._lanzar("simular")

    def _lanzar(self, que: str, biber: bool = False) -> bool:
        tex = self._tex()
        if tex is None or self.tareas.activa:
            if tex is None:
                self.aviso.emit(self.motivo, "aviso")
            return False
        if not tex.is_file():
            self.aviso.emit(f"No existe: {tex}", "error")
            return False
        simular = que == "simular"
        registro = None
        if not simular:
            registro = self.documentos.registro_de(tex)
            registro.parent.mkdir(parents=True, exist_ok=True)
            registro.unlink(missing_ok=True)
        opciones = self.opciones.para(tex, registro, biber)
        argv = opciones.orden(simular=simular)
        self._que, self._ruta, self._inicio = que, str(tex), time.monotonic()
        if not simular:
            self.documentos.marcarEnCurso(str(tex), True)
        nombre = ("Simulando" if simular else "Compilando") + f" {tex.name}"
        self._worker = self.tareas.proceso(nombre, argv, cwd=str(tex.parent), progreso_de=None if simular else svc.progreso_de_linea,
                                           al_terminar=lambda codigo, t=tex, o=opciones, s=simular: self._fin_compilar(codigo, t, o, s))
        self.cambiado.emit()
        return True

    def _fin_compilar(self, codigo: int, tex: Path, opciones: svc.Opciones, simular: bool) -> None:
        self._worker = None
        segundos = time.monotonic() - self._inicio
        if simular:
            self.cambiado.emit()
            self.terminada.emit(str(tex), codigo == 0)
            return
        self.documentos.marcarEnCurso(str(tex), False)
        estado = self.documentos.refrescar(str(tex)) or svc.estado_de(tex, opciones.log, opciones.salida)
        pdf = opciones.pdf()
        ok = codigo == 0 and (opciones.borrador or pdf.is_file())
        detalle = svc.resumen(estado.problemas)
        self.historial.anotar(tex, ok, segundos, detalle, estado.errores, estado.avisos)
        if ok and opciones.borrador:
            self.aviso.emit(f"{tex.name} compila (borrador: sin PDF) en {segundos:.1f} s · {detalle}.", "positivo")
        elif ok:
            self.aviso.emit(f"{pdf.name} en {segundos:.1f} s · {detalle}.", "positivo" if not estado.errores and not estado.avisos else "informacion")
            if self.opciones.abrirAlTerminar:
                self.espacio.abrir(str(pdf))
        else:
            self.aviso.emit(f"{tex.name} no compiló ({segundos:.1f} s) · {detalle}: revisa Problemas y la salida (F4).", "error")
        self.cambiado.emit()
        self.terminada.emit(str(tex), ok)

    # ------------------------------------------------------------- limpiar
    @Slot(result="QVariantList")
    def auxiliaresParaLimpiar(self) -> list:
        """Lo que `main.sh -c` borraría del documento actual (la lista del diálogo, antes de borrar)."""
        tex = self._tex()
        return [str(p.relative_to(tex.parent)) for p in svc.auxiliares_de(tex)] if tex else []

    @Slot(result=bool)
    def limpiar(self) -> bool:
        """`main.sh -c`: borra los auxiliares del documento actual (QML confirmó con la lista). El `.tex` y el PDF no se tocan."""
        tex = self._tex()
        if tex is None or self.tareas.activa:
            return False
        argv = svc.Opciones(tex).orden(limpiar=True)
        self._que, self._ruta, self._inicio = "limpiar", str(tex), time.monotonic()
        self._worker = self.tareas.proceso(f"Limpiando {tex.name}", argv, cwd=str(tex.parent),
                                           al_terminar=lambda codigo, t=tex: self._fin_limpiar(codigo, t))
        self.cambiado.emit()
        return True

    def _fin_limpiar(self, codigo: int, tex: Path) -> None:
        self._worker = None
        self.documentos.refrescar(str(tex))
        self.aviso.emit(f"Auxiliares de {tex.name} eliminados." if codigo == 0 else f"La limpieza de {tex.name} terminó con código {codigo}.",
                        "positivo" if codigo == 0 else "error")
        self.cambiado.emit()

    @Slot()
    def cancelar(self) -> None:
        if self.enCurso:
            self.tareas.cancelar()
