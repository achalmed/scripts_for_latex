"""latex_app/controladores/visor.py — el visor PDF del proyecto abierto: el de `gui-comun` 3.2
(`gui_comun.visor_pdf.VisorPdf`, con `VistaPdf` en QML: páginas con QtPdf o `pdftoppm`, zoom, miniaturas, recarga
conservando la página, selección, enlaces y búsqueda) más lo propio de LaTeX: SyncTeX en los dos sentidos, con el
`.synctex.gz` que deja el compilador del proyecto (junto al PDF o en su carpeta de auxiliares).

`LATEX_STUDIO_VISOR=pdftoppm` fuerza el respaldo sin QtPdf (además de `GUI_COMUN_VISOR`, la de la base).
"""

from __future__ import annotations

from pathlib import Path

from gui_comun.qt import Property, Signal, Slot
from gui_comun.visor_pdf import VisorPdf
from gui_comun.visor_pdf import hay_qtpdf as _hay_qtpdf

from latex_app import visor as vs

VARIABLE_MOTOR = "LATEX_STUDIO_VISOR"


def hay_qtpdf() -> bool:
    """¿Está el módulo QML `QtQuick.Pdf`? Si no, o con `LATEX_STUDIO_VISOR=pdftoppm`, el visor usa `pdftoppm`."""
    return _hay_qtpdf(VARIABLE_MOTOR)


class Visor(VisorPdf):
    irACodigo = Signal(str, int)
    synctexCambiado = Signal()               # propia: una propiedad de la subclase con la señal de la base de notify tumba QML

    def __init__(self, cache: Path | None = None, parent=None):
        super().__init__(Path(cache) if cache else Path.cwd(), variable_motor=VARIABLE_MOTOR, parent=parent)
        self._synctex_dir = ""
        self.cambiado.connect(self.synctexCambiado)

    @Slot(str, str)
    def abrir(self, pdf: str, synctex_dir: str = "") -> None:
        """Muestra `pdf` (recompilado: la vista conserva la página); `synctex_dir`, dónde está su `.synctex.gz`."""
        self._synctex_dir = synctex_dir
        super().abrir(pdf)

    @Slot()
    def recargar(self) -> None:
        pdf, self._pdf, self._clave = self._pdf, "", ""
        self.abrir(pdf, self._synctex_dir)

    # ---------------------------------------------------------------------------------------------------- SyncTeX
    @Property(bool, notify=synctexCambiado)
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
        self.marcarRecuadro(r["pagina"], r["x"], r["y"], r["ancho"], r["alto"])
        return True

    @Slot(int, float, float, result=bool)
    def haciaCodigo(self, pagina: int, x: float, y: float) -> bool:
        """Del PDF al código (doble clic en la página o «Ir al código de este punto»): abre el archivo en esa línea."""
        if not self.haySynctex:
            self.aviso.emit("Este PDF no tiene SyncTeX: no se puede volver al código.", "aviso")
            return False
        r = vs.hacia_codigo(Path(self._pdf), pagina, x, y, self._synctex_dir)
        if r is None:
            self.aviso.emit("SyncTeX no encontró el código de ese punto.", "aviso")
            return False
        self.irACodigo.emit(r["archivo"], r["linea"])
        return True
