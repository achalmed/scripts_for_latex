"""latex_app/proyectos.py — la detección de proyectos LaTeX en las carpetas de trabajo (sin Qt, se prueba solo).

Un proyecto es un documento principal (reingeniería R1): un `.tex` con `\\documentclass` sin comentar, que no es de la
clase `subfiles`, no declara `% !TEX root` y que ningún otro principal incluye. Sus archivos son los `\\input`,
`\\include`, `\\subfile`, `\\import`/`\\subimport` resueltos recursivamente y sus `.bib`. Por proyecto: el motor (el
declarado o LuaLaTeX, R4), el compilador (el del marco, latexmk o `main.sh`, R5), la categoría solo con información
(R6) y el estado leído del disco (PDF frente a las fuentes, el `.log`; sin abrir el PDF).

El recorrido usa `os.scandir` con profundidad acotada y salta carpetas ocultas y de construcción; el análisis de cada
`.tex` y de cada `.log` se guarda en una caché JSON por (fecha de modificación, tamaño): la segunda pasada solo lee lo
que cambió (R3). `detectar(..., progreso=, cancelado=)` sirve a una tarea de `gui_comun.tareas`.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from latex_app import compilador as svc

PROFUNDIDAD = 6
CARPETAS_SALTADAS = {"node_modules", "_site", "_freeze", ".quarto", "site_libs", ".build", "build", "__pycache__"}
LIMITE_LECTURA = 512 * 1024                  # un .tex más grande (tablas generadas) se lee hasta aquí
VERSION_CACHE = 4

CATEGORIAS = ("Escritura académica", "Tesis y trabajos de investigación", "Artículos científicos",
              "Documentos legislativos", "Documentos institucionales", "Pruebas y plantillas", "Otros proyectos")
NOMBRES_MOTOR = {"lualatex": "LuaLaTeX", "pdflatex": "pdfLaTeX", "xelatex": "XeLaTeX"}
NOMBRES_BIB = {"biber": "Biber", "bibtex": "BibTeX", "ninguna": ""}
NOMBRES_COMPILADOR = {"marco": "compilador del marco", "latexmk": "latexmk (latexmkrc)", "main.sh": "script_compilar_latex"}

_COMENTARIO = re.compile(r"(?<!\\)%.*")
_CLASE = re.compile(r"\\documentclass\s*(?:\[(?P<op>[^\]]*)\])?\s*\{(?P<clase>[^}]+)\}")
_MAGICO = re.compile(r"^\s*%\s*!\s*(?P<que>TEX\s+(?:TS-)?program|TEX\s+root|BIB\s+(?:TS-)?program)\s*=\s*(?P<valor>\S.*?)\s*$", re.I | re.M)
_ARARA = re.compile(r"^\s*%\s*arara\s*:\s*(?P<regla>[\w-]+)(?P<resto>.*)$", re.M)
_INCLUSION = re.compile(r"\\(?P<orden>input|include|subfile|import|subimport|includefrom|subincludefrom)\s*"
                        r"(?:\{(?P<a>[^}]*)\}\s*)(?:\{(?P<b>[^}]*)\})?")
_INPUT_SUELTO = re.compile(r"\\input\s+(?P<a>[\w./-]+\.tex)\b")
_RECURSO_BIB = re.compile(r"\\addbibresource\s*(?:\[[^\]]*\])?\s*\{(?P<a>[^}]+)\}")
_BIBLIOGRAFIA = re.compile(r"\\bibliography\s*\{(?P<a>[^}]+)\}")
_BIBLATEX = re.compile(r"\\usepackage\s*(?:\[(?P<op>[^\]]*)\])?\s*\{[^}]*\bbiblatex\b[^}]*\}")
_PAQUETES = re.compile(r"\\(?:usepackage|RequirePackage)\s*(?:\[[^\]]*\])?\s*\{(?P<a>[^}]+)\}")
_TITULO = re.compile(r"\\title\s*(?:\[[^\]]*\])?\s*\{(?P<t>(?:[^{}]|\{[^{}]*\})*)\}")
_PDF_MODE = re.compile(r"^\s*\$pdf_mode\s*=\s*(\d)", re.M)
_SALIDA_LATEXMK = re.compile(r"^\s*\$(?:out_dir|aux_dir)\s*=\s*['\"]([^'\"]+)['\"]", re.M)
_MOTOR_MARCO = re.compile(r"TEX_ENGINE[^\n]*?\b(lualatex|pdflatex|xelatex)\b")
_BIB_MARCO = re.compile(r"BIB_ENGINE[^\n]*?\b(biber|bibtex)\b")

# R6: la clase dice la categoría cuando es de un marco conocido por su nombre (no hace falta la ruta del marco)
_CATEGORIA_POR_CLASE = {
    "tesis": 1, "thesis-core": 1, "thesis": 1,
    "articulo": 2,
    "dictamen": 3,
    "oficio": 4, "memorando": 4, "solicitud": 4, "acta": 4, "agenda": 4, "informe-sr": 4, "rendicion-viaticos": 4, "despacho": 4,
    "monografia": 0, "ensayo": 0, "informe": 0, "libro": 0, "lamina": 0, "presentacion": 0,
}
_CATEGORIA_POR_CARPETA = {
    "theses": 1, "tesis": 1, "thesis": 1, "articles": 2, "articulos": 2, "articulo": 2, "papers": 2,
    "essays": 0, "ensayos": 0, "monographs": 0, "monografias": 0, "reports": 0, "informes": 0, "books": 0, "libros": 0,
    "legislativo": 3, "proyectos-de-ley": 3, "dictamenes": 3,
}
_CARPETAS_PRUEBA = {"pruebas", "prueba", "tests", "test", "plantillas", "templates", "ejemplos", "examples", "muestras",
                    "galeria", "deben-compilar", "deben-fallar"}
_ESQUEMAS_LEGISLATIVOS = ("legislativ", "dictamen", "mocion", "pedido-de-informacion", "analisis-normativo", "proyecto-de-ley")


# ======================================================================================================================
# análisis de un .tex (lo que se guarda en la caché)

def _leer(ruta: Path, limite: int = LIMITE_LECTURA) -> str:
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            return f.read(limite)
    except OSError:
        return ""


def sin_comentarios(texto: str) -> str:
    """El texto sin los comentarios de TeX (un `%` no escapado hasta el fin de línea), conservando las líneas."""
    return _COMENTARIO.sub("", texto)


def analizar_tex(texto: str) -> dict:
    """Lo que un `.tex` declara: clase, comentarios mágicos, directivas de arara, inclusiones, bibliografía, paquetes,
    título. Sin rutas resueltas (eso depende de dónde está)."""
    limpio = sin_comentarios(texto)
    magicos = {}
    for m in _MAGICO.finditer(texto[:4000]):
        que = re.sub(r"\s+", " ", m["que"].upper()).replace("TS-", "")
        magicos[que] = m["valor"].strip()
    arara = [(m["regla"].lower(), m["resto"].strip()) for m in _ARARA.finditer(texto[:8000])]
    m = _CLASE.search(limpio)
    inclusiones = []
    for mi in _INCLUSION.finditer(limpio):
        orden, a, b = mi["orden"], (mi["a"] or "").strip(), (mi["b"] or "").strip()
        if orden in ("import", "subimport", "includefrom", "subincludefrom"):
            inclusiones.append((orden, a, b))
        elif a:
            inclusiones.append((orden, a, ""))
    inclusiones += [("input", mi["a"], "") for mi in _INPUT_SUELTO.finditer(limpio)]
    bib_recursos = [a.strip() for m2 in _RECURSO_BIB.finditer(limpio) for a in [m2["a"]]]
    bib_antiguas = [a.strip() for m2 in _BIBLIOGRAFIA.finditer(limpio) for a in m2["a"].split(",") if a.strip()]
    mb = _BIBLATEX.search(limpio)
    backend = ""
    if mb and mb["op"]:
        mm = re.search(r"backend\s*=\s*(\w+)", mb["op"])
        backend = mm.group(1).lower() if mm else ""
    paquetes = sorted({p.strip() for m2 in _PAQUETES.finditer(limpio) for p in m2["a"].split(",") if p.strip()})
    mt = _TITULO.search(limpio)
    return {
        "clase": m["clase"].strip() if m else "",
        "opciones_clase": (m["op"] or "").strip() if m else "",
        "magicos": magicos,
        "arara": arara,
        "inclusiones": inclusiones,
        "bib_recursos": bib_recursos,
        "bib_antiguas": bib_antiguas,
        "biblatex": bool(mb) or "\\printbibliography" in limpio,
        "backend": backend,
        "paquetes": paquetes,
        "indice": "\\makeindex" in limpio,
        "glosarios": "\\makeglossaries" in limpio or "\\makenoidxglossaries" in limpio,
        "opcionales": sorted({m2.group(1).strip() for m2 in re.finditer(r"\\IfFileExists\s*\{([^}]+)\}", limpio)}),
        "titulo": re.sub(r"\s+", " ", re.sub(r"\\\\|\\[a-zA-Z]+\*?|[{}]", " ", mt["t"])).strip() if mt else "",
    }


# ======================================================================================================================
# la caché

class Cache:
    """Análisis de `.tex` y de `.log` por ruta y (fecha, tamaño), en un JSON. Sin ruta, solo en memoria."""

    def __init__(self, ruta: Path | None = None):
        self.ruta = ruta
        self._datos: dict = {"version": VERSION_CACHE, "tex": {}, "log": {}}
        self.leidos = 0                      # cuántos análisis se hicieron de verdad (las pruebas lo miran)
        if ruta and ruta.is_file():
            try:
                datos = json.loads(ruta.read_text(encoding="utf-8"))
                if datos.get("version") == VERSION_CACHE:
                    self._datos = datos
            except (OSError, ValueError):
                pass

    @staticmethod
    def _firma(ruta: Path) -> list | None:
        try:
            st = ruta.stat()
            return [st.st_mtime, st.st_size]
        except OSError:
            return None

    def tex(self, ruta: Path) -> dict:
        firma = self._firma(ruta)
        clave = str(ruta)
        guardado = self._datos["tex"].get(clave)
        if guardado and guardado.get("firma") == firma:
            return guardado["analisis"]
        self.leidos += 1
        analisis = analizar_tex(_leer(ruta))
        self._datos["tex"][clave] = {"firma": firma, "analisis": analisis}
        return analisis

    def log(self, ruta: Path) -> dict:
        """Errores, avisos y avisos tipográficos de un `.log` del motor (los números y los primeros problemas)."""
        firma = self._firma(ruta)
        clave = str(ruta)
        guardado = self._datos["log"].get(clave)
        if guardado and guardado.get("firma") == firma:
            return guardado["resumen"]
        problemas = svc.leer_log(_leer(ruta, 4 * 1024 * 1024))
        resumen = {k: sum(p.nivel == k for p in problemas) for k in ("error", "aviso", "tipografia")}
        self._datos["log"][clave] = {"firma": firma, "resumen": resumen}
        return resumen

    def guardar(self) -> None:
        if not self.ruta:
            return
        try:
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.ruta.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._datos, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.ruta)
        except OSError:
            pass


# ======================================================================================================================
# el proyecto

@dataclass
class Proyecto:
    principal: str                        # ruta absoluta del .tex principal
    raiz: str = ""                        # la carpeta de trabajo de la que salió
    clase: str = ""
    titulo: str = ""
    motor: str = "lualatex"
    motor_origen: str = "por omisión"
    bibliografia: str = "ninguna"         # biber · bibtex · ninguna
    compilador: str = "main.sh"           # marco · latexmk · main.sh
    marco: str = ""                       # la carpeta del marco (la que tiene scripts/build.sh)
    latexmkrc: str = ""
    carpeta_aux: str = ""                 # dónde quedan el .log y el .synctex.gz (relativa a la carpeta)
    archivos: list = field(default_factory=list)      # los incluidos que existen (rutas absolutas), en orden
    no_encontrados: list = field(default_factory=list)
    bibs: list = field(default_factory=list)
    bibs_no_encontradas: list = field(default_factory=list)
    paquetes: list = field(default_factory=list)
    configuracion: list = field(default_factory=list)  # latexmkrc, proyecto.yaml, fuentes.yml
    indice: bool = False                  # \makeindex: main.sh -i
    glosarios: bool = False               # \makeglossaries: main.sh -g
    categoria: str = "Otros proyectos"
    categoria_motivo: str = ""
    # estado (del disco)
    estado: str = "sin_compilar"
    errores: int = 0
    avisos: int = 0
    tipografia: int = 0
    pdf: str = ""
    pdf_mtime: float = 0.0
    fuentes_mtime: float = 0.0
    log: str = ""
    auxiliares: int = 0
    synctex: str = ""

    @property
    def carpeta(self) -> str:
        return str(Path(self.principal).parent)

    @property
    def nombre(self) -> str:
        return Path(self.principal).name

    @property
    def job(self) -> str:
        return Path(self.principal).stem

    def texto_motor(self) -> str:
        nombre = NOMBRES_MOTOR.get(self.motor, self.motor)
        bib = NOMBRES_BIB.get(self.bibliografia, "")
        return nombre + (f" + {bib}" if bib else "")

    def fuentes(self) -> list[str]:
        """El principal, sus incluidos y sus `.bib`: lo que el editor ofrece y lo que decide si el PDF está al día."""
        return [self.principal] + [a for a in self.archivos if a != self.principal] + list(self.bibs)

    def a_dict(self) -> dict:
        d = asdict(self)
        d.update(carpeta=self.carpeta, nombre=self.nombre, job=self.job, texto_motor=self.texto_motor())
        return d


# ======================================================================================================================
# el recorrido

def recorrer(raiz: Path, profundidad: int = PROFUNDIDAD, cancelado: Callable[[], bool] | None = None) -> list[Path]:
    """Los `.tex` bajo `raiz` hasta `profundidad` carpetas, sin ocultas ni de construcción ni enlaces que vuelvan."""
    salida: list[Path] = []
    vistos: set = set()
    pila = [(raiz, 0)]
    while pila:
        if cancelado and cancelado():
            break
        carpeta, nivel = pila.pop()
        try:
            st = carpeta.stat()
            if (st.st_dev, st.st_ino) in vistos:
                continue
            vistos.add((st.st_dev, st.st_ino))
            entradas = list(os.scandir(carpeta))
        except OSError:
            continue
        subcarpetas = []
        for e in entradas:
            nombre = e.name
            try:
                if e.is_dir():
                    if nivel < profundidad and not nombre.startswith(".") and nombre not in CARPETAS_SALTADAS:
                        subcarpetas.append(Path(e.path))
                elif nombre.endswith(".tex") and e.is_file():
                    salida.append(Path(e.path))
            except OSError:
                continue
        pila.extend((s, nivel + 1) for s in sorted(subcarpetas, reverse=True))
    return sorted(salida)


def _candidatos(base: Path, nombre: str, extension: str = ".tex") -> list[Path]:
    n = nombre.strip().strip('"')
    if not n or "#" in n or "\\" in n:
        return []
    p = Path(n)
    lista = [p] if p.suffix == extension else [p.with_name(p.name + extension), p]
    return [(q if q.is_absolute() else base / q) for q in lista]


def _resolver(base: Path, nombre: str, extension: str = ".tex") -> Path | None:
    for c in _candidatos(base, nombre, extension):
        if c.is_file():
            return c.resolve()
    return None


def resolver_inclusiones(principal: Path, cache: Cache, limite: int = 400) -> tuple[list[Path], list[str], list[dict]]:
    """Los archivos que el principal incluye, recursivamente y en orden (sin repetir ni entrar en bucle); los que no se
    encuentran (con la carpeta del documento, como TeX: `\\input` es relativo a la carpeta del principal, `\\import` y
    `\\subfile` a la del archivo que los pide); y el análisis de cada archivo leído (principal incluido)."""
    base = principal.parent
    vistos: list[Path] = [principal.resolve()]
    faltan: list[str] = []
    analisis = [cache.tex(principal)]

    def visitar(archivo: Path, dir_actual: Path, datos: dict) -> None:
        for orden, a, b in datos["inclusiones"]:
            if len(vistos) >= limite:
                return
            if orden in ("import", "includefrom"):
                destino_dir = Path(a) if os.path.isabs(a) else base / a
                hallado, nuevo_dir = _resolver(destino_dir, b), destino_dir
            elif orden in ("subimport", "subincludefrom"):
                destino_dir = dir_actual / a
                hallado, nuevo_dir = _resolver(destino_dir, b), destino_dir
            elif orden == "subfile":
                hallado = _resolver(dir_actual, a) or _resolver(base, a)
                nuevo_dir = hallado.parent if hallado else dir_actual
            else:
                hallado = _resolver(base, a) or _resolver(dir_actual, a)
                nuevo_dir = dir_actual
            nombre = b if orden in ("import", "subimport", "includefrom", "subincludefrom") else a
            if hallado is None:
                opcional = nombre in datos.get("opcionales", ()) or f"{nombre}.tex" in datos.get("opcionales", ())
                if nombre and nombre not in faltan and not opcional:
                    faltan.append(nombre)
                continue
            if hallado in vistos:
                continue
            vistos.append(hallado)
            sub = cache.tex(hallado)
            analisis.append(sub)
            visitar(hallado, nuevo_dir, sub)

    visitar(principal, base, analisis[0])
    return vistos[1:], faltan, analisis


# ----------------------------------------------------------------------------------------------------- motor y marco

def _ancestros(carpeta: Path, tope: int = 8) -> Iterable[Path]:
    d = carpeta
    for _ in range(tope):
        yield d
        if d.parent == d:
            return
        d = d.parent


class _Marcos:
    """Los marcos con compilador propio (una carpeta con `scripts/build.sh` y `classes/`): qué clases trae cada uno y con
    qué motor compila. Se calcula una vez por carpeta y recorrido."""

    def __init__(self):
        self._por_carpeta: dict[Path, dict | None] = {}

    def de(self, carpeta: Path) -> dict | None:
        if carpeta in self._por_carpeta:
            return self._por_carpeta[carpeta]
        datos = None
        build = carpeta / "scripts" / "build.sh"
        if build.is_file() and (carpeta / "classes").is_dir():
            clases = set()
            for sub in ("classes", "core"):
                for raiz, dirs, archivos in os.walk(carpeta / sub):
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    clases.update(a[:-4] for a in archivos if a.endswith(".cls"))
            texto = _leer(build, 64 * 1024) + _leer(carpeta / "scripts" / "config.sh", 64 * 1024)
            mm, mb = _MOTOR_MARCO.search(texto), _BIB_MARCO.search(texto)
            datos = {"ruta": str(carpeta), "build": str(build), "clases": clases,
                     "motor": mm.group(1) if mm else "lualatex", "bib": mb.group(1) if mb else "biber",
                     "carpeta_aux": ".build" if re.search(r"BUILD_DIR[^\n]*\.build", texto) else ""}
        self._por_carpeta[carpeta] = datos
        return datos

    def para(self, principal: Path, clase: str) -> dict | None:
        if not clase:
            return None
        for d in _ancestros(principal.parent):
            m = self.de(d)
            if m and clase in m["clases"]:
                return m
        return None


def _latexmkrc(carpeta: Path) -> Path | None:
    for nombre in ("latexmkrc", ".latexmkrc"):
        p = carpeta / nombre
        if p.is_file():
            return p
    return None


_MOTORES_ARARA = {"lualatex": "lualatex", "pdflatex": "pdflatex", "xelatex": "xelatex"}


def decidir_motor(principal: Path, datos: dict, marco: dict | None, rc: Path | None) -> tuple[str, str, str, str]:
    """(motor, de dónde salió, bibliografía, compilador) según R4 y R5: el comentario mágico manda; después arara, el
    `latexmkrc` y el marco; sin declaración, LuaLaTeX. La bibliografía: `% !BIB program`, `backend=`, `\\bibliography`
    sin biblatex (BibTeX), biblatex (Biber)."""
    motor, origen = "", ""
    programa = datos["magicos"].get("TEX PROGRAM", "").lower()
    if programa in NOMBRES_MOTOR:
        motor, origen = programa, "comentario mágico"
    if not motor:
        for regla, resto in datos["arara"]:
            if regla in _MOTORES_ARARA:
                motor, origen = _MOTORES_ARARA[regla], "arara"
                break
            if regla == "latexmk":
                m = re.search(r"engine\s*:\s*(\w+)", resto)
                if m and m.group(1) in NOMBRES_MOTOR:
                    motor, origen = m.group(1), "arara"
                    break
    if not motor and rc is not None:
        m = _PDF_MODE.search(_leer(rc, 64 * 1024))
        if m:
            motor = {"1": "pdflatex", "4": "lualatex", "5": "xelatex"}.get(m.group(1), "")
            origen = "latexmkrc" if motor else ""
    if not motor and marco is not None:
        motor, origen = marco["motor"], "marco"
    if not motor:
        motor, origen = "lualatex", "por omisión"
    # bibliografía
    bib_programa = datos["magicos"].get("BIB PROGRAM", "").lower()
    arara_bib = next((r for r, _ in datos["arara"] if r in ("biber", "bibtex")), "")
    if bib_programa in ("biber", "bibtex"):
        bib = bib_programa
    elif arara_bib:
        bib = arara_bib
    elif datos["biblatex"]:
        bib = "bibtex" if datos["backend"] == "bibtex" else "biber"
    elif datos["bib_antiguas"]:
        bib = "bibtex"
    elif marco is not None:
        bib = marco["bib"]
    else:
        bib = "ninguna"
    compilador = "marco" if marco is not None else "latexmk" if rc is not None else "main.sh"
    return motor, origen, bib, compilador


# ----------------------------------------------------------------------------------------------------- categoría

def _proyecto_yaml(carpeta: Path) -> dict:
    """Las claves simples (`tipo`, `esquema`, `tema`, `titulo`) de un `proyecto.yaml`, sin depender de PyYAML."""
    p = carpeta / "proyecto.yaml"
    if not p.is_file():
        return {}
    salida = {}
    for linea in _leer(p, 32 * 1024).splitlines():
        m = re.match(r"^(tipo|esquema|tema|titulo)\s*:\s*['\"]?(.*?)['\"]?\s*(?:#.*)?$", linea)
        if m and m.group(1) not in salida:
            salida[m.group(1)] = m.group(2).strip()
    return salida


def categorizar(principal: Path, raiz: Path, clase: str, en_despacho: bool = False) -> tuple[str, str]:
    """(categoría, motivo) con la regla R6; «Otros proyectos» si no hay información."""
    try:
        partes = [p.lower() for p in principal.parent.relative_to(raiz).parts]
    except ValueError:
        partes = [p.lower() for p in principal.parent.parts[-3:]]
    prueba = next((p for p in partes if p in _CARPETAS_PRUEBA), "")
    if prueba:
        return CATEGORIAS[5], f"carpeta «{prueba}»"
    yaml = _proyecto_yaml(principal.parent)
    if yaml:
        esquema, tipo, tema = yaml.get("esquema", "").lower(), yaml.get("tipo", "").lower(), yaml.get("tema", "").lower()
        if tema == "legislativo" or any(e in esquema for e in _ESQUEMAS_LEGISLATIVOS):
            return CATEGORIAS[3], "proyecto.yaml (" + (f"tema: {tema}" if tema == "legislativo" else f"esquema: {esquema}") + ")"
        if tipo in ("tesis", "thesis"):
            return CATEGORIAS[1], "proyecto.yaml (tipo: tesis)"
        if tipo in ("articulo", "article"):
            return CATEGORIAS[2], "proyecto.yaml (tipo: articulo)"
        if tipo in ("monografia", "ensayo", "informe", "libro", "presentacion", "lamina"):
            return CATEGORIAS[0], f"proyecto.yaml (tipo: {tipo})"
    if clase in _CATEGORIA_POR_CLASE:
        indice = _CATEGORIA_POR_CLASE[clase]
        if en_despacho and indice == 0:
            indice = 4
        return CATEGORIAS[indice], f"clase «{clase}»"
    carpeta = next((p for p in reversed(partes) if p in _CATEGORIA_POR_CARPETA), "")
    if carpeta:
        return CATEGORIAS[_CATEGORIA_POR_CARPETA[carpeta]], f"carpeta «{carpeta}»"
    if (principal.parent / "fuentes.yml").is_file() or (principal.parent / "fuentes" / "fuentes.yml").is_file():
        return CATEGORIAS[0], "fuentes.yml (Método Documental)"
    return CATEGORIAS[6], ""


# ----------------------------------------------------------------------------------------------------- estado

def _mtime(ruta: str | Path) -> float:
    try:
        return os.stat(ruta).st_mtime
    except OSError:
        return 0.0


def leer_estado(p: Proyecto, cache: Cache, registro: Path | None = None) -> Proyecto:
    """El estado del proyecto leído del disco (sin abrir el PDF): el PDF frente a la fuente más reciente, los problemas
    del `.log` más reciente (el del motor o el registro de la ventana), los auxiliares y el SyncTeX."""
    principal = Path(p.principal)
    carpeta = principal.parent
    aux = carpeta / p.carpeta_aux if p.carpeta_aux else carpeta
    pdf = carpeta / f"{p.job}.pdf"
    if not pdf.is_file() and p.carpeta_aux and (aux / f"{p.job}.pdf").is_file():
        pdf = aux / f"{p.job}.pdf"
    p.pdf = str(pdf) if pdf.is_file() else ""
    p.pdf_mtime = _mtime(pdf) if p.pdf else 0.0
    p.fuentes_mtime = max((_mtime(f) for f in p.fuentes()), default=0.0)
    logs = [q for q in (aux / f"{p.job}.log", registro) if q is not None and q.is_file()]
    if logs:
        reciente = max(logs, key=_mtime)
        p.log = str(reciente)
        if registro is not None and reciente == registro:
            problemas = svc.problemas_de_registro(svc.leer_registro(registro))
            r = {k: sum(x.nivel == k for x in problemas) for k in ("error", "aviso", "tipografia")}
        else:
            r = cache.log(reciente)
        p.errores, p.avisos, p.tipografia = r["error"], r["aviso"], r["tipografia"]
        mtime_log = _mtime(reciente)
    else:
        p.log, p.errores, p.avisos, p.tipografia, mtime_log = "", 0, 0, 0, 0.0
    extensiones = svc.extensiones_auxiliares()
    if p.carpeta_aux and aux.is_dir():
        try:
            p.auxiliares = sum(1 for e in os.scandir(aux) if e.is_file())
        except OSError:
            p.auxiliares = 0
    else:
        p.auxiliares = sum(1 for ext in extensiones if (aux / f"{p.job}.{ext}").is_file())
    synctex = aux / f"{p.job}.synctex.gz"
    p.synctex = str(synctex) if synctex.is_file() else ""
    if p.errores and (not p.pdf or mtime_log >= p.pdf_mtime - 1):
        p.estado = "errores"
    elif not p.pdf:
        p.estado = "sin_compilar"
    elif p.pdf_mtime + 1 < p.fuentes_mtime:
        p.estado = "desactualizado"
    elif p.avisos and mtime_log >= p.pdf_mtime - 60:
        p.estado = "avisos"
    else:
        p.estado = "compilado"
    return p


# ----------------------------------------------------------------------------------------------------- detección

def construir(principal: Path, raiz: Path, cache: Cache, marcos: _Marcos | None = None, en_despacho: bool = False) -> Proyecto:
    """El proyecto de un principal ya elegido: inclusiones, `.bib`, motor, compilador, categoría (sin estado)."""
    marcos = marcos or _Marcos()
    principal = principal.resolve()
    archivos, faltan, analisis = resolver_inclusiones(principal, cache)
    datos = analisis[0]
    # lo que declaran los incluidos también cuenta para la bibliografía y los paquetes
    junto = dict(datos)
    junto["bib_recursos"] = [b for a in analisis for b in a["bib_recursos"]]
    junto["bib_antiguas"] = [b for a in analisis for b in a["bib_antiguas"]]
    junto["biblatex"] = any(a["biblatex"] for a in analisis)
    junto["backend"] = next((a["backend"] for a in analisis if a["backend"]), "")
    marco = marcos.para(principal, datos["clase"])
    rc = _latexmkrc(principal.parent)
    motor, origen, bib, compilador = decidir_motor(principal, junto, marco, rc)
    bibs, bibs_faltan = [], []
    for nombre in junto["bib_recursos"] + junto["bib_antiguas"]:
        hallado = _resolver(principal.parent, nombre, ".bib")
        if hallado and str(hallado) not in bibs:
            bibs.append(str(hallado))
        elif not hallado and nombre not in bibs_faltan:
            bibs_faltan.append(nombre)
    carpeta_aux = ""
    if marco is not None:
        carpeta_aux = marco["carpeta_aux"]
    elif rc is not None:
        m = _SALIDA_LATEXMK.search(_leer(rc, 64 * 1024))
        carpeta_aux = m.group(1) if m else ""
    configuracion = [str(q) for q in (rc, principal.parent / "proyecto.yaml", principal.parent / "fuentes.yml",
                                      principal.parent / "fuentes" / "fuentes.yml") if q is not None and q.is_file()]
    categoria, motivo = categorizar(principal, raiz, datos["clase"], en_despacho)
    yaml = _proyecto_yaml(principal.parent)
    return Proyecto(principal=str(principal), raiz=str(raiz), clase=datos["clase"],
                    titulo=datos["titulo"] or yaml.get("titulo", ""), motor=motor, motor_origen=origen,
                    bibliografia=bib, compilador=compilador, marco=marco["ruta"] if marco else "",
                    latexmkrc=str(rc) if rc else "", carpeta_aux=carpeta_aux, archivos=[str(a) for a in archivos],
                    no_encontrados=faltan, bibs=bibs, bibs_no_encontradas=bibs_faltan,
                    paquetes=sorted({q for a in analisis for q in a["paquetes"]}), configuracion=configuracion,
                    indice=any(a.get("indice") for a in analisis), glosarios=any(a.get("glosarios") for a in analisis),
                    categoria=categoria, categoria_motivo=motivo)


def detectar(raices: list[tuple[str, Path]] | list[Path], profundidad: int = PROFUNDIDAD, cache: Cache | None = None,
             progreso: Callable[[int, str], None] | None = None, cancelado: Callable[[], bool] | None = None,
             registro_de: Callable[[Path], Path | None] | None = None, despacho: Path | None = None) -> list[Proyecto]:
    """Los proyectos de las carpetas de trabajo (R1–R6), con su estado. `raices`: rutas o pares (nombre, ruta).
    `registro_de(tex)`: el registro de la ventana de ese principal (para el estado). `despacho`: la carpeta del
    despacho, si es una de las raíces (sus documentos de clases genéricas son institucionales)."""
    cache = cache or Cache()
    marcos = _Marcos()
    pares = [(r if isinstance(r, tuple) else (Path(r).name, Path(r))) for r in raices]
    proyectos: list[Proyecto] = []
    vistos: set[str] = set()
    for i, (_nombre, raiz) in enumerate(pares):
        raiz = Path(raiz).expanduser()
        if not raiz.is_dir():
            continue
        if progreso:
            progreso(int(i * 100 / max(1, len(pares))), f"recorriendo {raiz.name}")
        texs = recorrer(raiz, profundidad, cancelado)
        principales: list[Path] = []
        incluidos: set[Path] = set()
        con_raiz: set[Path] = set()
        for j, tex in enumerate(texs):
            if cancelado and cancelado():
                return proyectos
            if progreso and j % 50 == 0:
                progreso(int((i + j / max(1, len(texs))) * 100 / max(1, len(pares))), f"{raiz.name}: {j} de {len(texs)} .tex")
            datos = cache.tex(tex)
            if datos["magicos"].get("TEX ROOT"):
                con_raiz.add(tex.resolve())
                continue
            if datos["clase"] and datos["clase"] != "subfiles":
                principales.append(tex.resolve())
        for tex in principales:
            archivos, _f, _a = resolver_inclusiones(tex, cache)
            incluidos.update(archivos)
        en_despacho = despacho is not None and (raiz.resolve() == despacho.resolve() or despacho.resolve() in raiz.resolve().parents)
        for tex in principales:
            if tex in incluidos or tex in con_raiz or str(tex) in vistos:
                continue
            vistos.add(str(tex))
            p = construir(tex, raiz, cache, marcos, en_despacho)
            leer_estado(p, cache, registro_de(tex) if registro_de else None)
            proyectos.append(p)
    if progreso:
        progreso(100, f"{len(proyectos)} proyectos")
    cache.guardar()
    return proyectos


def proyecto_de(tex: Path, cache: Cache | None = None, raiz: Path | None = None) -> Proyecto | None:
    """El proyecto de un `.tex` abierto suelto (Ctrl+O): si es un principal, el suyo; si declara `% !TEX root`, el de
    esa raíz; si no tiene clase, None."""
    cache = cache or Cache()
    tex = Path(tex).expanduser().resolve()
    if not tex.is_file():
        return None
    datos = cache.tex(tex)
    raiz_magica = datos["magicos"].get("TEX ROOT", "")
    if raiz_magica:
        destino = _resolver(tex.parent, raiz_magica)
        if destino and destino != tex:
            return proyecto_de(destino, cache, raiz)
    if not datos["clase"] or datos["clase"] == "subfiles":
        return None
    p = construir(tex, raiz or tex.parent, cache)
    return leer_estado(p, cache)
