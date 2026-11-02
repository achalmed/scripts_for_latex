"""latex_app/controladores/documentos.py — los documentos: la tabla de los `.tex` de la carpeta de trabajo y la de los
recientes (estado leído del disco: rediseño L5), el documento actual (sobre el que actúan Compilar, Simular, Limpiar,
Abrir el PDF y Abrir en el editor) y sus detalles: Resumen, Problemas (del registro de su última corrida, rediseño L4),
Registro (la salida íntegra), Salidas (el PDF y los auxiliares). También «Recompilar al guardar» (`QFileSystemWatcher`
sobre el documento actual, rediseño L7). Solo lee: compilar y limpiar son de `Corrida`."""

from __future__ import annotations

import os
from pathlib import Path

from gui_comun.modelos import ModeloFiltrado, ModeloLista, ModeloTabla
from gui_comun.qt import QFileSystemWatcher, QObject, QSettings, QStandardPaths, QTimer, Property, Signal, Slot

from latex_app import compilador as svc
from latex_app import modelos as mod

ESPERA_RECOMPILAR_MS = 900


def cache_del_studio() -> Path:
    """La caché del studio (`~/.cache/<org>/<app>` o `XDG_CACHE_HOME`): ahí van los registros de cada corrida."""
    return Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation) or (Path.home() / ".cache" / "latex-studio"))


class Documentos(QObject):
    cambiado = Signal()                 # las tablas (carpeta, recientes) y sus contadores
    actualCambiado = Signal()           # el documento actual y sus detalles
    filtroCambiado = Signal()
    recompilar = Signal()               # el documento actual cambió en disco y «Recompilar al guardar» está marcado
    aviso = Signal(str, str)

    def __init__(self, espacio, opciones, historial, consola, cache: Path | None = None, parent=None):
        super().__init__(parent)
        self.espacio, self.opciones, self.historial, self.consola = espacio, opciones, historial, consola
        self._s = QSettings()
        self._cache = cache or cache_del_studio()
        self._tabla_carpeta = ModeloTabla(mod.COLUMNAS_DOCUMENTOS, parent=self)
        self._carpeta = ModeloFiltrado(self._tabla_carpeta, parent=self)
        self._tabla_recientes = ModeloTabla(mod.COLUMNAS_DOCUMENTOS, parent=self)
        self._recientes = ModeloFiltrado(self._tabla_recientes, parent=self)
        self._problemas = ModeloLista(mod.ROLES_PROBLEMAS, parent=self)
        self._problemas_filtrados = ModeloFiltrado(self._problemas, parent=self)
        self._salidas = ModeloTabla(mod.COLUMNAS_SALIDAS, parent=self)
        self._actual = ""
        self._en_curso = ""
        self._estado: svc.Estado | None = None
        self._registro = ""
        self._pdf: dict = {}
        self._mostrar = {"error": True, "aviso": True, "tipografia": True}
        self._problemas_filtrados.aceptar_con(self._acepta_problema)
        self._vigia: QFileSystemWatcher | None = None       # se crea al vigilar por primera vez (su notificador de inotify no
        self._espera = QTimer(self)                          # sobrevive bien a que Python recoja un controlador que nadie usa)
        self._espera.setSingleShot(True)
        self._espera.setInterval(ESPERA_RECOMPILAR_MS)
        self._espera.timeout.connect(self.recompilar)
        espacio.carpetaCambiada.connect(self.recargar)
        historial.recientesCambiados.connect(self._pintar_recientes)
        opciones.cambiado.connect(self._opciones_cambiaron)
        self.recargar()
        self._pintar_recientes()
        guardado = str(self._s.value("actual", "") or "")
        if guardado and Path(guardado).is_file():
            self.fijarActual(guardado)

    modelo = Property(QObject, lambda self: self._carpeta, constant=True)
    modeloRecientes = Property(QObject, lambda self: self._recientes, constant=True)
    problemas = Property(QObject, lambda self: self._problemas_filtrados, constant=True)
    salidas = Property(QObject, lambda self: self._salidas, constant=True)

    # ----------------------------------------------------------------- lectura del disco
    def registro_de(self, tex: Path) -> Path:
        return svc.registro_de(tex, self._cache)

    def estado_de(self, tex: Path) -> svc.Estado:
        return svc.estado_de(tex, self.registro_de(tex), self.opciones.salida, en_curso=str(tex) == self._en_curso)

    def _fila(self, tex: Path) -> dict:
        return mod.fila_documento(tex, self.estado_de(tex), self.opciones.motor, self.opciones.salida)

    @Slot()
    def recargar(self) -> None:
        """Relee los `.tex` de la carpeta de trabajo y el estado de cada uno."""
        carpeta = Path(self.espacio.carpeta)
        self._tabla_carpeta.poner([self._fila(t) for t in svc.documentos_en(carpeta)])
        if self._actual and not Path(self._actual).is_file():
            self.fijarActual("")
        self.cambiado.emit()
        if self._actual:
            self._leer_actual()

    def _pintar_recientes(self) -> None:
        self._tabla_recientes.poner([self._fila(Path(r)) for r in self.historial.recientes()])
        self.cambiado.emit()

    def _opciones_cambiaron(self) -> None:
        self.recargar()
        self._pintar_recientes()
        self._vigilar()

    def refrescar(self, ruta: str) -> svc.Estado | None:
        """Vuelve a leer del disco una sola fila (tras compilar o limpiar) y, si es la actual, sus detalles."""
        tex = Path(ruta)
        estado = None
        for tabla in (self._tabla_carpeta, self._tabla_recientes):
            for i, f in enumerate(tabla.todas()):
                if f.get("ruta") == ruta:
                    fila = self._fila(tex)
                    estado = estado or self.estado_de(tex)
                    tabla.actualizar(i, **fila)
        self.cambiado.emit()
        if ruta == self._actual:
            estado = self._leer_actual()
        return estado or (self.estado_de(tex) if tex.is_file() else None)

    def marcarEnCurso(self, ruta: str, en_curso: bool) -> None:
        self._en_curso = ruta if en_curso else ""
        self.refrescar(ruta)

    # ----------------------------------------------------------------- el documento actual
    @Slot(str)
    def fijarActual(self, ruta: str) -> None:
        ruta = str(Path(ruta).expanduser()) if ruta else ""
        if ruta and not Path(ruta).is_file():
            ruta = ""
        if ruta == self._actual:
            return
        self._actual = ruta
        self._s.setValue("actual", ruta)
        self._leer_actual()
        self._vigilar()

    @Slot(int)
    def fijarFila(self, fila_visible: int) -> None:
        """La fila elegida en la tabla de la carpeta."""
        if fila_visible >= 0:
            self.fijarActual(self._tabla_carpeta.fila(self._carpeta.filaOrigen(fila_visible)).get("ruta", ""))

    @Slot(int)
    def fijarFilaReciente(self, fila_visible: int) -> None:
        if fila_visible >= 0:
            self.fijarActual(self._tabla_recientes.fila(self._recientes.filaOrigen(fila_visible)).get("ruta", ""))

    @Slot(str, result=int)
    def filaDe(self, ruta: str) -> int:
        """La fila visible de ese documento en la tabla de la carpeta; −1 si no está."""
        for i, f in enumerate(self._tabla_carpeta.todas()):
            if f.get("ruta") == ruta:
                return self._carpeta.filaVisible(i)
        return -1

    @Slot(str, result=str)
    def abrir(self, ruta: str) -> str:
        """Abre un `.tex` (Ctrl+O o soltado en la ventana): su carpeta pasa a ser la de trabajo, queda seleccionado y
        entra a recientes. Devuelve el error, o vacío."""
        p = Path(ruta.strip()).expanduser()
        if p.suffix.lower() != ".tex":
            p = p.with_suffix(".tex")
        if not p.is_file():
            return f"No existe ese .tex: {p}"
        p = p.resolve()
        error = self.espacio.fijarCarpeta(str(p.parent))
        if error:
            return error
        self.historial.recordar(p)
        self.fijarActual(str(p))
        self.espacio.fijarVista("carpeta")
        self.consola.registrar("info", f"Documento: {p}")
        return ""

    def _leer_actual(self) -> svc.Estado | None:
        if not self._actual:
            self._estado, self._registro, self._pdf = None, "", {}
            self._problemas.poner([])
            self._salidas.poner([])
            self.espacio.fijarContexto("")
            self.actualCambiado.emit()
            return None
        tex = Path(self._actual)
        self._estado = self.estado_de(tex)
        self._registro = svc.leer_registro(Path(self._estado.origen)) if self._estado.origen else ""
        self._pdf = svc.info_pdf(svc.pdf_de(tex, self.opciones.salida))
        self._problemas.poner(mod.filas_problemas(self._estado.problemas))
        self._salidas.poner([mod.fila_salida(s) for s in svc.salidas_de(tex, self.opciones.salida)])
        self.espacio.fijarContexto(f"{tex.name} · {self.opciones.descripcion}")
        self.actualCambiado.emit()
        return self._estado

    @Property(str, notify=actualCambiado)
    def actual(self) -> str:
        return self._actual

    @Property(bool, notify=actualCambiado)
    def hayActual(self) -> bool:
        return bool(self._actual)

    @Property(str, notify=actualCambiado)
    def nombre(self) -> str:
        return Path(self._actual).name if self._actual else ""

    @Property(str, notify=actualCambiado)
    def carpetaActual(self) -> str:
        return str(Path(self._actual).parent) if self._actual else ""

    @Property(str, notify=actualCambiado)
    def motorTexto(self) -> str:
        return mod.texto_motor(Path(self._actual), self.opciones.motor) if self._actual else ""

    @Property(str, notify=actualCambiado)
    def motorDeclarado(self) -> str:
        return svc.motor_declarado(Path(self._actual)) if self._actual else ""

    @Property(str, notify=actualCambiado)
    def modificado(self) -> str:
        try:
            return svc.fecha_legible(Path(self._actual).stat().st_mtime) if self._actual else ""
        except OSError:
            return ""

    @Property(str, notify=actualCambiado)
    def estadoTexto(self) -> str:
        return self._estado.texto if self._estado else ""

    @Property(str, notify=actualCambiado)
    def estadoNivel(self) -> str:
        return self._estado.nivel if self._estado else ""

    @Property(str, notify=actualCambiado)
    def estadoClave(self) -> str:
        return self._estado.clave if self._estado else ""

    @Property(int, notify=actualCambiado)
    def nErrores(self) -> int:
        return self._estado.errores if self._estado else 0

    @Property(int, notify=actualCambiado)
    def nAvisos(self) -> int:
        return self._estado.avisos if self._estado else 0

    @Property(int, notify=actualCambiado)
    def nTipografia(self) -> int:
        return self._estado.tipografia if self._estado else 0

    @Property(int, notify=actualCambiado)
    def nProblemas(self) -> int:
        return self._problemas.filas

    @Property(str, notify=actualCambiado)
    def resumenProblemas(self) -> str:
        return svc.resumen(self._estado.problemas) if self._estado else ""

    @Property(str, notify=actualCambiado)
    def origenProblemas(self) -> str:
        """De dónde salieron los problemas: el registro de la ventana o el `.log` del motor; vacío si no hay ninguno."""
        return self._estado.origen if self._estado else ""

    @Property(str, notify=actualCambiado)
    def registro(self) -> str:
        return self._registro

    @Property(str, notify=actualCambiado)
    def pdfRuta(self) -> str:
        return self._pdf.get("ruta", "")

    @Property(bool, notify=actualCambiado)
    def hayPdf(self) -> bool:
        return bool(self._pdf.get("existe"))

    @Property(str, notify=actualCambiado)
    def pdfFecha(self) -> str:
        return self._pdf.get("modificado", "")

    @Property(str, notify=actualCambiado)
    def pdfTamano(self) -> str:
        return self._pdf.get("tamano", "")

    @Property(int, notify=actualCambiado)
    def pdfPaginas(self) -> int:
        return int(self._pdf.get("paginas", 0) or 0)

    @Property(str, notify=actualCambiado)
    def ultimaCompilacion(self) -> str:
        """«2026-11-02 10:58 · compiló en 4,2 s · 2 aviso(s)» según el historial; vacío si nunca se compiló aquí."""
        h = self.historial.ultima_de(self._actual) if self._actual else {}
        if not h:
            return ""
        return f"{h.get('cuando', '')} · {'compiló' if h.get('ok') else 'falló'} en {h.get('segundos', 0)} s" + (f" · {h['detalle']}" if h.get("detalle") else "")

    # ----------------------------------------------------------------- problemas
    def _acepta_problema(self, fila: int) -> bool:
        return self._mostrar.get(self._problemas.fila(fila).get("nivel", ""), True)

    def _mostrar_get(self, nivel: str):
        return lambda self_: self_._mostrar[nivel]

    def _fijar_mostrar(self, nivel: str, valor: bool) -> None:
        if self._mostrar[nivel] != bool(valor):
            self._mostrar[nivel] = bool(valor)
            self._problemas_filtrados.aceptar_con(self._acepta_problema)
            self.filtroCambiado.emit()

    mostrarErrores = Property(bool, lambda self: self._mostrar["error"], lambda self, v: self._fijar_mostrar("error", v), notify=filtroCambiado)
    mostrarAvisos = Property(bool, lambda self: self._mostrar["aviso"], lambda self, v: self._fijar_mostrar("aviso", v), notify=filtroCambiado)
    mostrarTipografia = Property(bool, lambda self: self._mostrar["tipografia"], lambda self, v: self._fijar_mostrar("tipografia", v), notify=filtroCambiado)

    def _archivo_del_problema(self, p: dict) -> str:
        """La ruta absoluta del archivo de un problema (`./capitulo.tex`, relativa a la carpeta del `.tex`); sin archivo, el `.tex`."""
        if not self._actual:
            return ""
        archivo = p.get("archivo", "")
        if not archivo:
            return self._actual
        ruta = Path(archivo) if os.path.isabs(archivo) else Path(self._actual).parent / archivo
        return str(ruta) if ruta.is_file() else self._actual

    @Slot(int)
    def irA(self, fila_visible: int) -> None:
        """Intro o doble clic en un problema: el editor en su archivo y su línea."""
        if fila_visible < 0:
            return
        p = self._problemas.fila(self._problemas_filtrados.filaOrigen(fila_visible))
        self.espacio.abrirEnEditor(self._archivo_del_problema(p), int(p.get("linea") or 0))

    # ----------------------------------------------------------------- abrir
    @Slot()
    def abrirPdf(self) -> None:
        if not self._actual:
            self.aviso.emit("No hay documento: abre un .tex (Ctrl+O) o elige uno en la tabla.", "aviso")
        elif self.hayPdf:
            self.espacio.abrir(self.pdfRuta)
        else:
            self.aviso.emit(f"Todavía no hay PDF de {self.nombre}: compílalo (F5).", "aviso")

    @Slot()
    def abrirEditor(self) -> None:
        if self._actual:
            self.espacio.abrirEnEditor(self._actual, 0)

    # ----------------------------------------------------------------- navegación y recuentos
    @Property("QVariantMap", notify=cambiado)
    def contadores(self) -> dict:
        return mod.contar(self._tabla_carpeta.todas())

    @Property("QVariantList", notify=cambiado)
    def filasNavegacion(self) -> list:
        return [{"nombre": "carpeta", "texto": "Carpeta de trabajo", "icono": "folder-open", "contador": self._tabla_carpeta.filas},
                {"nombre": "recientes", "texto": "Recientes", "icono": "document-open-recent", "contador": self._tabla_recientes.filas}]

    @Property(int, notify=cambiado)
    def total(self) -> int:
        return self._tabla_carpeta.filas

    def nombres(self) -> list[str]:
        return [f["nombre"] for f in self._tabla_carpeta.todas()]

    # ----------------------------------------------------------------- recompilar al guardar
    def _vigilar(self) -> None:
        """Vigila el documento actual si «Recompilar al guardar» está marcado; si no, retira el vigía (con `deleteLater`,
        dentro del bucle de eventos: su notificador de inotify no sobrevive a que lo recoja Python)."""
        if self.opciones.vigilar and self._actual and Path(self._actual).is_file():
            if self._vigia is None:
                self._vigia = QFileSystemWatcher(self)
                self._vigia.fileChanged.connect(self._cambio_en_disco)
            for f in self._vigia.files():
                self._vigia.removePath(f)
            self._vigia.addPath(self._actual)
        elif self._vigia is not None:
            self._vigia.fileChanged.disconnect(self._cambio_en_disco)
            self._vigia.deleteLater()
            self._vigia = None

    def _cambio_en_disco(self, ruta: str) -> None:
        if self._vigia is not None and Path(ruta).exists() and ruta not in self._vigia.files():
            self._vigia.addPath(ruta)            # los editores guardan reemplazando: se vuelve a vigilar
        if self.opciones.vigilar and ruta == self._actual:
            self._espera.start()

    @Property(bool, notify=actualCambiado)
    def vigilando(self) -> bool:
        return bool(self._vigia is not None and self._vigia.files())
