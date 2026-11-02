"""latex_app/controladores/opciones.py — las opciones de compilación, de la sesión (QSettings; rediseño L6): motor
(`auto` · `lualatex`: la ventana no ofrece pdfLaTeX ni XeLaTeX, regla 6 del workspace), pasadas, bibliografía (ninguna ·
Biber · BibTeX heredado), índice, glosarios, borrador, carpeta del PDF, abrir el PDF al terminar y recompilar al guardar.
`para(tex, registro)` arma el `compilador.Opciones` con el que `Corrida` pide la orden a la CLI."""

from __future__ import annotations

from pathlib import Path

from gui_comun.qt import QObject, QSettings, Property, Signal, Slot

from latex_app import compilador as svc

MOTORES = svc.MOTORES_VENTANA
BIBLIOGRAFIAS = (("ninguna", "Sin bibliografía"), ("biber", "Biber (biblatex)"), ("bibtex", "BibTeX (heredado)"))


class Opciones(QObject):
    cambiado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._s = QSettings()

    # ------------------------------------------------------------- lectura y escritura genéricas
    def _leer(self, clave: str, defecto):
        v = self._s.value(f"compilar/{clave}", defecto)
        if isinstance(defecto, bool):
            return v in (True, "true", "True", 1, "1")
        if isinstance(defecto, int):
            try:
                return int(v)
            except (TypeError, ValueError):
                return defecto
        return str(v) if v is not None else defecto

    def _poner(self, clave: str, valor) -> None:
        defecto = {bool: False, int: 0}.get(type(valor), "")
        if self._s.value(f"compilar/{clave}") is None or self._leer(clave, defecto) != valor:
            self._s.setValue(f"compilar/{clave}", valor)
            self.cambiado.emit()

    # ------------------------------------------------------------- las opciones
    @Property("QVariantList", constant=True)
    def motores(self) -> list:
        return [{"valor": v, "texto": t} for v, t in MOTORES]

    @Property("QVariantList", constant=True)
    def bibliografias(self) -> list:
        return [{"valor": v, "texto": t} for v, t in BIBLIOGRAFIAS]

    def _motor_get(self) -> str:
        v = self._leer("motor", "auto")
        return v if v in dict(MOTORES) else "auto"          # un pdflatex guardado por 1.x vuelve a auto

    motor = Property(str, _motor_get, lambda self, v: self._poner("motor", v if v in dict(MOTORES) else "auto"), notify=cambiado)
    pasadas = Property(int, lambda self: min(5, max(1, self._leer("pasadas", 2))), lambda self, v: self._poner("pasadas", min(5, max(1, int(v)))), notify=cambiado)

    def _bib_get(self) -> str:
        v = self._leer("bibliografia", "biber")
        return v if v in dict(BIBLIOGRAFIAS) else "biber"

    bibliografia = Property(str, _bib_get, lambda self, v: self._poner("bibliografia", v if v in dict(BIBLIOGRAFIAS) else "biber"), notify=cambiado)
    indice = Property(bool, lambda self: self._leer("indice", False), lambda self, v: self._poner("indice", bool(v)), notify=cambiado)
    glosarios = Property(bool, lambda self: self._leer("glosarios", False), lambda self, v: self._poner("glosarios", bool(v)), notify=cambiado)
    borrador = Property(bool, lambda self: self._leer("borrador", False), lambda self, v: self._poner("borrador", bool(v)), notify=cambiado)
    salida = Property(str, lambda self: self._leer("salida", ""), lambda self, v: self._poner("salida", (v or "").strip()), notify=cambiado)
    abrirAlTerminar = Property(bool, lambda self: self._leer("abrir_al_terminar", False), lambda self, v: self._poner("abrir_al_terminar", bool(v)), notify=cambiado)
    vigilar = Property(bool, lambda self: self._leer("vigilar", False), lambda self, v: self._poner("vigilar", bool(v)), notify=cambiado)

    @Slot(str)
    def fijarMotor(self, v: str) -> None:
        self.motor = v

    @Slot(str)
    def fijarBibliografia(self, v: str) -> None:
        self.bibliografia = v

    # ------------------------------------------------------------- derivadas
    @Property(int, notify=cambiado)
    def pasadasEfectivas(self) -> int:
        """Las que correrá la CLI: sube a 3 con bibliografía o glosarios."""
        p = self.pasadas
        return max(p, 3) if self.bibliografia != "ninguna" or self.glosarios else p

    @Property(str, notify=cambiado)
    def descripcion(self) -> str:
        """«LuaLaTeX + Biber · 3 pasadas»: lo que la barra de estado dice del documento actual."""
        partes = [svc.NOMBRES_MOTOR.get(self.motor, "LuaLaTeX") if self.motor != "auto" else "LuaLaTeX (auto)"]
        if self.bibliografia != "ninguna":
            partes[0] += " + " + ("Biber" if self.bibliografia == "biber" else "BibTeX")
        extras = [n for n, v in (("índice", self.indice), ("glosarios", self.glosarios), ("borrador", self.borrador)) if v]
        partes.append(f"{self.pasadasEfectivas} pasada" + ("" if self.pasadasEfectivas == 1 else "s"))
        return " · ".join(partes + extras)

    def para(self, tex: Path, registro: Path | None = None, biber: bool = False) -> svc.Opciones:
        """El `compilador.Opciones` de una corrida; con `biber`, fuerza Biber (Ctrl+B) sin cambiar lo guardado."""
        return svc.Opciones(tex, self.motor, self.pasadas, "biber" if biber else self.bibliografia, self.indice, self.glosarios,
                            self.borrador, self.salida, registro)

    @Slot(str, result=str)
    def ordenTexto(self, ruta: str) -> str:
        """La orden que correría, legible (la pestaña Opciones)."""
        if not ruta:
            return ""
        argv = self.para(Path(ruta)).orden()
        return "main.sh " + " ".join(a if " " not in a else f'"{a}"' for a in argv[2:-1]) + f" {Path(ruta).name}"
