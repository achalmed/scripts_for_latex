"""latex_app/controladores/visor.py — el visor PDF integrado (R10, R11): las páginas del PDF del proyecto abierto como
modelo (tamaño en puntos y la imagen ya renderizada a la resolución del zoom), el renderizado con `pdftoppm` en hilos
aparte y por demanda (QML pide las páginas visibles), las miniaturas, la recarga al recompilar conservando la página,
y SyncTeX en los dos sentidos.

Los hilos solo corren `pdftoppm`; el modelo se toca siempre en el hilo de la interfaz (la señal `_hecho` cruza de hilo).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from gui_comun.modelos import ModeloLista
from gui_comun.qt import QObject, Property, Signal, Slot

from latex_app import visor as vs

ROLES = ("pagina", "ancho", "alto", "imagen", "miniatura")
PPP_MINIATURA = 18
ZOOM_MIN, ZOOM_MAX = 0.25, 4.0


class Visor(QObject):
    cambiado = Signal()
    zoomCambiado = Signal()
    irAPagina = Signal(int, float)           # página (1-based), y en puntos desde arriba (−1: el principio)
    marcar = Signal(int, float, float, float, float)   # SyncTeX: página, x, y, ancho, alto (puntos)
    irACodigo = Signal(str, int)
    aviso = Signal(str, str)
    _hecho = Signal(str, int, int, str)      # clave del PDF, página, ppp, ruta del PNG (desde el hilo)

    def __init__(self, cache: Path | None = None, parent=None):
        super().__init__(parent)
        self._cache = cache                  # la base de la caché del studio (la de las páginas cuelga de ella)
        self._paginas = ModeloLista(ROLES, parent=self)
        self._pdf = ""
        self._clave = ""
        self._synctex_dir = ""
        self._zoom = 1.0
        self._ajustar = True
        self._escala = 1.0                   # devicePixelRatio de la pantalla (lo fija QML)
        self._pedidas: set = set()
        self._hilos = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pdftoppm")
        self._hecho.connect(self._poner_imagen)

    paginas = Property(QObject, lambda self: self._paginas, constant=True)

    # ---------------------------------------------------------------------------------------------------- el PDF
    @Slot(str, str)
    def abrir(self, pdf: str, synctex_dir: str = "") -> None:
        """Muestra `pdf`; si es el mismo con otra fecha (recompilado), conserva la página (QML la guarda y la repone)."""
        self._synctex_dir = synctex_dir
        ruta = Path(pdf) if pdf else None
        if ruta is None or not ruta.is_file():
            self._pdf, self._clave = "", ""
            self._paginas.poner([])
            self.cambiado.emit()
            return
        clave = vs.clave(ruta)
        if pdf == self._pdf and clave == self._clave:
            return
        self._pdf, self._clave = pdf, clave
        self._pedidas.clear()
        tamanos = vs.paginas(ruta)
        self._paginas.poner([{"pagina": i, "ancho": a, "alto": b, "imagen": "", "miniatura": ""} for i, (a, b) in enumerate(tamanos, start=1)])
        vs.podar(self._cache, conservar=clave)
        self.cambiado.emit()

    @Slot()
    def recargar(self) -> None:
        pdf, self._pdf, self._clave = self._pdf, "", ""
        self.abrir(pdf, self._synctex_dir)

    @Property(str, notify=cambiado)
    def pdf(self) -> str:
        return self._pdf

    @Property(int, notify=cambiado)
    def total(self) -> int:
        return self._paginas.filas

    @Property(float, notify=cambiado)
    def anchoMaximo(self) -> float:
        """El ancho en puntos de la página más ancha (el ancho del contenido del visor)."""
        return max((f["ancho"] for f in self._paginas.todas()), default=0.0)

    # ---------------------------------------------------------------------------------------------------- zoom
    def _zoom_set(self, z: float) -> None:
        z = max(ZOOM_MIN, min(ZOOM_MAX, float(z)))
        if abs(z - self._zoom) > 1e-3:
            self._zoom = z
            self.zoomCambiado.emit()

    zoom = Property(float, lambda self: self._zoom, _zoom_set, notify=zoomCambiado)
    ajustarAncho = Property(bool, lambda self: self._ajustar,
                            lambda self, v: (setattr(self, "_ajustar", bool(v)), self.zoomCambiado.emit()), notify=zoomCambiado)
    escala = Property(float, lambda self: self._escala, lambda self, v: setattr(self, "_escala", max(1.0, float(v))), notify=zoomCambiado)

    @Slot()
    def acercar(self) -> None:
        self.ajustarAncho = False
        self.zoom = self._zoom * 1.2

    @Slot()
    def alejar(self) -> None:
        self.ajustarAncho = False
        self.zoom = self._zoom / 1.2

    @Slot(float)
    def ajustarA(self, ancho_disponible: float) -> None:
        """Con «ajustar al ancho», el zoom que hace caber la página más ancha en `ancho_disponible` (píxeles lógicos)."""
        if self._ajustar and self._paginas.filas:
            ancho = max(f["ancho"] for f in self._paginas.todas())
            self.zoom = max(ZOOM_MIN, min(ZOOM_MAX, ancho_disponible / ancho))

    def ppp(self) -> int:
        """Los puntos por pulgada del zoom actual, redondeados a pasos de 12 para que la caché se reutilice."""
        valor = 72.0 * self._zoom * self._escala
        return max(24, min(400, int(round(valor / 12.0)) * 12))

    # ---------------------------------------------------------------------------------------------------- renderizado
    @Slot(int)
    def pedir(self, pagina: int) -> None:
        """QML pide una página visible: si no está a la resolución del zoom, se renderiza en un hilo."""
        self._pedir(pagina, self.ppp())

    @Slot(int)
    def pedirMiniatura(self, pagina: int) -> None:
        self._pedir(pagina, PPP_MINIATURA)

    def _pedir(self, pagina: int, ppp: int) -> None:
        if not self._pdf or not (1 <= pagina <= self._paginas.filas):
            return
        clave = (self._clave, pagina, ppp)
        if clave in self._pedidas:
            return
        self._pedidas.add(clave)
        pdf, base, clave_pdf = Path(self._pdf), self._cache, self._clave

        def trabajo():
            ruta = vs.renderizar(pdf, pagina, ppp, base)
            self._hecho.emit(clave_pdf, pagina, ppp, str(ruta) if ruta else "")

        self._hilos.submit(trabajo)

    def renderizar_ya(self, pagina: int, ppp: int | None = None) -> str:
        """En el hilo actual (pruebas y capturas)."""
        ppp = ppp or self.ppp()
        ruta = vs.renderizar(Path(self._pdf), pagina, ppp, self._cache)
        self._poner_imagen(self._clave, pagina, ppp, str(ruta) if ruta else "")
        return str(ruta) if ruta else ""

    def _poner_imagen(self, clave: str, pagina: int, ppp: int, ruta: str) -> None:
        if clave != self._clave or not ruta or not (1 <= pagina <= self._paginas.filas):
            if not ruta:
                self._pedidas.discard((clave, pagina, ppp))
            return
        url = Path(ruta).as_uri()
        if ppp == PPP_MINIATURA:
            self._paginas.actualizar(pagina - 1, miniatura=url)
        else:
            self._paginas.actualizar(pagina - 1, imagen=url)

    def apagar(self) -> None:
        self._hilos.shutdown(wait=False, cancel_futures=True)

    # ---------------------------------------------------------------------------------------------------- SyncTeX
    @Property(bool, notify=cambiado)
    def haySynctex(self) -> bool:
        if not self._pdf:
            return False
        stem = Path(self._pdf).stem
        carpeta = Path(self._synctex_dir) if self._synctex_dir else Path(self._pdf).parent
        return (carpeta / f"{stem}.synctex.gz").is_file() or (carpeta / f"{stem}.synctex").is_file()

    @Slot(str, int, int, result=bool)
    def desdeCodigo(self, archivo: str, linea: int, columna: int = 0) -> bool:
        """Del código al PDF (Ctrl+clic o Ctrl+Alt+J): va a la página y marca el recuadro."""
        if not self._pdf:
            self.aviso.emit("No hay PDF: compila el proyecto (F5).", "aviso")
            return False
        if not self.haySynctex:
            self.aviso.emit("Este PDF no tiene SyncTeX (el compilador del proyecto no lo genera, o se limpiaron los auxiliares).", "aviso")
            return False
        r = vs.hacia_pdf(Path(self._pdf), Path(archivo), linea, columna, self._synctex_dir)
        if r is None:
            self.aviso.emit(f"SyncTeX no encontró la línea {linea} de {Path(archivo).name} en el PDF (¿el PDF es anterior al cambio?).", "aviso")
            return False
        self.irAPagina.emit(r["pagina"], r["y"])
        self.marcar.emit(r["pagina"], r["x"], r["y"], r["ancho"], r["alto"])
        return True

    @Slot(int, float, float, result=bool)
    def haciaCodigo(self, pagina: int, x: float, y: float) -> bool:
        """Del PDF al código (doble clic en la página): abre el archivo en esa línea."""
        if not self.haySynctex:
            self.aviso.emit("Este PDF no tiene SyncTeX: no se puede volver al código.", "aviso")
            return False
        r = vs.hacia_codigo(Path(self._pdf), pagina, x, y, self._synctex_dir)
        if r is None:
            self.aviso.emit("SyncTeX no encontró el código de ese punto.", "aviso")
            return False
        self.irACodigo.emit(r["archivo"], r["linea"])
        return True
