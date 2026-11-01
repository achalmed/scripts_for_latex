"""El puente con `script_compilar_latex` (sin Qt, se prueba solo): la orden con sus opciones y la lectura del `.log`.

La ventana no compila por su cuenta: arma la orden de la CLI de este mismo repo (la que usan `docencia` y el alias
`compilar`) y, al terminar, lee el `.log` de LaTeX para mostrar cada error y aviso con su archivo y su línea.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CLI = REPO / "script_compilar_latex" / "main.sh"
MOTORES = ("auto", "lualatex", "pdflatex", "xelatex")
BIBLIOGRAFIAS = (("ninguna", "Sin bibliografía"), ("biber", "Biber (biblatex)"), ("bibtex", "BibTeX"))


@dataclass
class Opciones:
    tex: Path
    motor: str = "auto"
    pasadas: int = 2
    bibliografia: str = "biber"
    indice: bool = False
    glosarios: bool = False
    borrador: bool = False
    salida: str = ""            # carpeta a la que se mueve el PDF; vacío: junto al .tex
    log: Path | None = None     # dónde guardar el .log (para leer los problemas)

    def orden(self, simular: bool = False, limpiar: bool = False) -> list[str]:
        argv = ["bash", str(CLI)]
        if limpiar:
            argv += ["-c"]
        else:
            argv += ["-e", self.motor, "-p", str(self.pasadas)]
            if self.bibliografia == "biber":
                argv.append("--biber")
            elif self.bibliografia == "bibtex":
                argv.append("-b")
            if self.indice:
                argv.append("-i")
            if self.glosarios:
                argv.append("-g")
            if self.borrador:
                argv.append("--draft")
            if self.salida:
                argv += ["-o", self.salida]
            if self.log:
                argv += ["--log", str(self.log)]
        if simular:
            argv.append("-n")
        return argv + [str(self.tex)]

    def pdf(self) -> Path:
        carpeta = Path(self.salida) if self.salida else self.tex.parent
        return carpeta / f"{self.tex.stem}.pdf"


@dataclass
class Problema:
    nivel: str                 # error · aviso · tipografia
    mensaje: str
    linea: int | None = None
    archivo: str = ""
    detalle: list[str] = field(default_factory=list)


_ERROR_FLE = re.compile(r"^(?P<archivo>[^:\s][^:]*\.(?:tex|sty|cls|bib|ltx)):(?P<linea>\d+): (?P<msg>.+)$")
_AVISO = re.compile(r"^(?:LaTeX|Package (?P<paquete>\S+)|Class \S+) Warning: (?P<msg>.+)$")
_LINEA_INPUT = re.compile(r"on input line (\d+)")
_TIPOGRAFIA = re.compile(r"^(Overfull|Underfull) \\[hv]box ")
_LINEAS = re.compile(r"at lines? (\d+)")
_ARCHIVO_ABIERTO = re.compile(r"\((\.?/[^\s()]+\.tex)")


def leer_log(texto: str) -> list[Problema]:
    """Errores, avisos y avisos tipográficos de un `.log` de LaTeX, en orden, sin repetir."""
    problemas: list[Problema] = []
    vistos: set[tuple] = set()
    lineas = texto.splitlines()
    archivo_actual = ""

    def agregar(p: Problema) -> None:
        clave = (p.nivel, p.mensaje, p.linea)
        if clave not in vistos:
            vistos.add(clave)
            problemas.append(p)

    i = 0
    while i < len(lineas):
        l = lineas[i]
        for m in _ARCHIVO_ABIERTO.finditer(l):
            archivo_actual = m.group(1)
        m = _ERROR_FLE.match(l)
        if m:
            agregar(Problema("error", m["msg"].strip(), int(m["linea"]), m["archivo"]))
        elif l.startswith("! "):
            mensaje, linea = l[2:].strip(), None
            for siguiente in lineas[i + 1:i + 12]:              # el «l.123 …» que dice dónde
                mm = re.match(r"^l\.(\d+)", siguiente)
                if mm:
                    linea = int(mm.group(1))
                    break
            agregar(Problema("error", mensaje, linea, archivo_actual))
        else:
            m = _AVISO.match(l)
            if m:
                mensaje = m["msg"].strip()
                j = i + 1
                while j < len(lineas) and lineas[j].startswith(("(", " ")) and not lineas[j].startswith(("(./", "(/")) \
                        and j < i + 6 and lineas[j].strip():
                    mensaje += " " + lineas[j].strip().lstrip("(").split(")", 1)[-1].strip()
                    j += 1
                mm = _LINEA_INPUT.search(mensaje)
                mensaje = re.sub(r"\s+", " ", _LINEA_INPUT.sub("", mensaje)).strip(" .")
                if m["paquete"]:
                    mensaje = f"{m['paquete']}: {mensaje}"
                agregar(Problema("aviso", mensaje, int(mm.group(1)) if mm else None, archivo_actual))
            else:
                if _TIPOGRAFIA.match(l):
                    mm = _LINEAS.search(l)
                    agregar(Problema("tipografia", l.split(" in ")[0].strip(), int(mm.group(1)) if mm else None,
                                     archivo_actual))
        i += 1
    orden = {"error": 0, "aviso": 1, "tipografia": 2}
    return sorted(problemas, key=lambda p: orden[p.nivel])


def resumen(problemas: list[Problema]) -> str:
    n = {k: sum(p.nivel == k for p in problemas) for k in ("error", "aviso", "tipografia")}
    partes = [f"{n['error']} error(es)" if n["error"] else "", f"{n['aviso']} aviso(s)" if n["aviso"] else "",
              f"{n['tipografia']} de tipografía" if n["tipografia"] else ""]
    return " · ".join(p for p in partes if p) or "sin problemas"
