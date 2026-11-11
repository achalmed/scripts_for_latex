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

PROFUNDIDAD = 12                             # el máximo de los ajustes: ~/Documents entero cuesta < 1 s y llega a docencia/contenido/cursos/<c>/04-evaluaciones/<sub>/<expediente>
CARPETAS_SALTADAS = {"node_modules", "_site", "_freeze", ".quarto", "site_libs", ".build", "build", "__pycache__"}
LIMITE_LECTURA = 512 * 1024                  # un .tex más grande (tablas generadas) se lee hasta aquí
VERSION_CACHE = 6                            # 6: macros, envolturas de \input y sus llamadas (2026-11-10)

CATEGORIAS = ("Escritura académica", "Tesis y trabajos de investigación", "Artículos científicos",
              "Documentos legislativos", "Documentos institucionales", "Docencia y evaluaciones", "Publicaciones (Quarto)",
              "Notas y apuntes", "Archivo e histórico", "Pruebas y plantillas", "Otros proyectos")
DOCENCIA, QUARTO, NOTAS, ARCHIVO, PRUEBAS, OTROS = CATEGORIAS[5:]
NOMBRES_MOTOR = {"lualatex": "LuaLaTeX", "pdflatex": "pdfLaTeX", "xelatex": "XeLaTeX"}
NOMBRES_BIB = {"biber": "Biber", "bibtex": "BibTeX", "ninguna": ""}
NOMBRES_COMPILADOR = {"marco": "compilador del marco", "latexmk": "latexmk (latexmkrc)", "main.sh": "script_compilar_latex"}

_COMENTARIO = re.compile(r"(?<!\\)%.*")
_CLASE = re.compile(r"\\documentclass\s*(?:\[(?P<op>[^\]]*)\])?\s*\{(?P<clase>[^}]+)\}")
_MAGICO = re.compile(r"^\s*%\s*!\s*(?P<que>TEX\s+(?:TS-)?program|TEX\s+root|BIB\s+(?:TS-)?program)\s*=\s*(?P<valor>\S.*?)\s*$", re.I | re.M)
# los comentarios mágicos de un marco: «% !MODO = soluciones» (una palabra; los de TeX llevan dos: «TEX program»)
_MAGICO_MARCO = re.compile(r"^\s*%\s*!\s*(?P<que>[A-Za-z][\w-]*)\s*=\s*(?P<valor>\S.*?)\s*$", re.M)
_ARARA = re.compile(r"^\s*%\s*arara\s*:\s*(?P<regla>[\w-]+)(?P<resto>.*)$", re.M)
_INCLUSION = re.compile(r"\\(?P<orden>input|include|subfile|import|subimport|includefrom|subincludefrom)\s*"
                        r"(?:\{(?P<a>[^}]*)\}\s*)(?:\{(?P<b>[^}]*)\})?")
_INPUT_SUELTO = re.compile(r"\\input\s+(?P<a>[\w./-]+\.tex)\b")
_RECURSO_BIB = re.compile(r"\\addbibresource\s*(?:\[[^\]]*\])?\s*\{(?P<a>[^}]+)\}")
_BIBLIOGRAFIA = re.compile(r"\\bibliography\s*\{(?P<a>[^}]+)\}")
_BIBLATEX = re.compile(r"\\usepackage\s*(?:\[(?P<op>[^\]]*)\])?\s*\{[^}]*\bbiblatex\b[^}]*\}")
_PAQUETES = re.compile(r"\\(?:usepackage|RequirePackage)\s*(?:\[[^\]]*\])?\s*\{(?P<a>[^}]+)\}")
# una macro simple (\def\X{valor}, \newcommand{\X}{valor}): la que se usa en una ruta, \input{profiles/\CVprofile}
_MACRO_SIMPLE = re.compile(r"\\(?:[gex]?def\s*\\(?P<n1>[A-Za-z@]+)|(?:re|provide)?newcommand\*?\s*\{?\s*\\(?P<n2>[A-Za-z@]+)\s*\}?)"
                           r"\s*\{(?P<v>[^{}\\#]*)\}")
# una orden propia que incluye su argumento: \newcommand{\inputAnexos}[1]{\ifdefined\X\else\input{#1}\fi}, \def\Y#1{\input{#1}}
_ENVOLTURA = re.compile(r"\\(?:(?:re|provide)?newcommand\*?\s*\{?\s*\\(?P<n1>[A-Za-z@]+)\s*\}?\s*\[\d\](?:\[[^\]]*\])?"
                        r"|[gex]?def\s*\\(?P<n2>[A-Za-z@]+)\s*#1)\s*\{")
_INCLUYE_ARGUMENTO = re.compile(r"\\(?:input|include|subfile)\s*\{\s*#1\s*\}")
# una llamada cuyo argumento parece una ruta (se resuelve solo si la orden es una envoltura del proyecto)
_LLAMADA_RUTA = re.compile(r"\\(?P<orden>[A-Za-z@]+)\*?\s*\{(?P<a>[^{}\\#\s]*(?:/|\.tex)[^{}\\#\s]*)\}")
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
    "academic-exam": 5, "academic-beamer": 5,          # exámenes, prácticas y solucionarios; decks de clase (docencia)
}
_CATEGORIA_POR_CARPETA = {
    "theses": 1, "tesis": 1, "thesis": 1, "articles": 2, "articulos": 2, "articulo": 2, "papers": 2,
    "essays": 0, "ensayos": 0, "monographs": 0, "monografias": 0, "reports": 0, "informes": 0, "books": 0, "libros": 0,
    "legislativo": 3, "proyectos-de-ley": 3, "dictamenes": 3,
    "sesiones": 5, "sessions": 5, "_ediciones": 5, "ediciones": 5, "diapositivas": 5, "slides": 5, "evaluaciones": 5,
    "notas": 7, "notes": 7, "apuntes": 7,
    "archivo": 8, "archive": 8, "_archive": 8, "historico": 8, "legado": 8, "legacy": 8,
}
_CARPETAS_PRUEBA = {"pruebas", "prueba", "tests", "test", "plantillas", "templates", "ejemplos", "examples", "muestras",
                    "ejemplo", "example", "vendor", "scaffolds", "_extensions", "_plantillas",
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
    for m in _MAGICO_MARCO.finditer(texto[:4000]):
        magicos.setdefault(m["que"].upper(), m["valor"].strip())
    arara = [(m["regla"].lower(), m["resto"].strip()) for m in _ARARA.finditer(texto[:8000])]
    m = _CLASE.search(limpio)
    con_posicion = []
    for mi in _INCLUSION.finditer(limpio):
        orden, a, b = mi["orden"], (mi["a"] or "").strip(), (mi["b"] or "").strip()
        if "#" in a or "#" in b:                       # el cuerpo de una envoltura (\input{#1}): no es un archivo
            continue
        if orden in ("import", "subimport", "includefrom", "subincludefrom"):
            con_posicion.append((mi.start(), (orden, a, b)))
        elif a:
            con_posicion.append((mi.start(), (orden, a, "")))
    con_posicion += [(mi.start(), ("input", mi["a"], "")) for mi in _INPUT_SUELTO.finditer(limpio)]
    # las llamadas a órdenes que podrían ser envolturas, en su sitio (`("llamada", orden, ruta)`)
    no_envolturas = {"input", "include", "subfile", "import", "subimport", "includefrom", "subincludefrom", "includegraphics",
                     "addbibresource", "bibliography", "usepackage", "RequirePackage", "documentclass", "url", "href",
                     "includepdf", "lstinputlisting", "inputminted", "graphicspath", "IfFileExists", "InputIfFileExists"}
    con_posicion += [(mi.start(), ("llamada", mi["orden"], mi["a"].strip())) for mi in _LLAMADA_RUTA.finditer(limpio)
                     if mi["orden"] not in no_envolturas]
    inclusiones = [t for _pos, t in sorted(con_posicion, key=lambda x: x[0])]
    macros: dict[str, str] = {}
    for mm in _MACRO_SIMPLE.finditer(limpio):           # la primera definición es la de omisión (\ifdefined\X\else\def…)
        macros.setdefault(mm["n1"] or mm["n2"], mm["v"].strip())
    envolturas = sorted({me["n1"] or me["n2"] for me in _ENVOLTURA.finditer(limpio)
                         if _INCLUYE_ARGUMENTO.search(limpio, me.end(), me.end() + 400)})
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
        "macros": macros,
        "envolturas": envolturas,
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
    categoria_icono: str = ""            # el icono de una categoría declarada por el esquema del marco
    categoria_motivo: str = ""
    subcategorias: list = field(default_factory=list)   # hasta dos niveles bajo la categoría, de las carpetas (tipo · grupo)
    subcarpetas: list = field(default_factory=list)     # la carpeta de cada nivel, relativa a `raiz` ("" si es la del proyecto)
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
    # versiones que el compilador del marco produce de este .tex (`versiones:` del latex-studio.yml; §7 del contrato)
    versiones: list = field(default_factory=list)   # [{clave, nombre, job}]
    version_argumento: str = ""          # cómo se pide una al compilador del marco (--modo)
    version_comentario: str = ""         # el comentario mágico que la declara (MODO → «% !MODO = …»)
    version_declarada: str = ""          # la que declara el documento (o la de omisión)
    version: str = ""                    # la que se compila y se ve (la declarada, o la elegida en la ventana)

    @property
    def carpeta(self) -> str:
        return str(Path(self.principal).parent)

    @property
    def nombre(self) -> str:
        return Path(self.principal).name

    @property
    def job(self) -> str:
        """El nombre de la salida (PDF, .log, SyncTeX): el del principal o, con versiones, el de la versión elegida."""
        return self.job_de(self.version)

    def job_de(self, version: str) -> str:
        nombre = Path(self.principal).stem
        v = next((v for v in self.versiones if v.get("clave") == version), None)
        return str(v.get("job") or "{nombre}").replace("{nombre}", nombre) if v else nombre

    def elegir_version(self, version: str) -> bool:
        """Pasa a compilar y ver otra versión (sin escribir nada); False si el marco no la declara."""
        if not any(v.get("clave") == version for v in self.versiones):
            return False
        self.version = version
        return True

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


def rutas_con_macros(nombre: str, macros: dict[str, str], base: Path) -> list[str]:
    """Las rutas a que puede llevar `\\input{profiles/\\CVprofile}`: primero la del valor que el documento da a cada
    macro (la de omisión) y después las demás que existen con cualquier valor (`profiles/*.tex`), porque una macro en
    una ruta es un parámetro (el perfil, el capítulo) y todas sus variantes son archivos del proyecto."""
    salida: list[str] = []
    expandido = re.sub(r"\\([A-Za-z@]+)\s*", lambda m: macros.get(m.group(1), m.group(0)), nombre)
    if "\\" not in expandido:
        salida.append(expandido)
    patron = re.sub(r"\\[A-Za-z@]+\s*", "*", nombre)
    if "\\" not in patron and patron.strip("*/"):
        if not patron.endswith(".tex"):
            patron += ".tex"
        try:
            for hallado in sorted(base.glob(patron)):
                if hallado.is_file():
                    relativa = str(hallado.relative_to(base))[:-4]
                    if relativa not in salida and relativa + ".tex" not in salida:
                        salida.append(relativa)
        except (OSError, ValueError, NotImplementedError):
            pass
    return salida


def resolver_inclusiones(principal: Path, cache: Cache, limite: int = 400) -> tuple[list[Path], list[str], list[dict]]:
    """Los archivos que el principal incluye, recursivamente y en orden (sin repetir ni entrar en bucle); los que no se
    encuentran (con la carpeta del documento, como TeX: `\\input` es relativo a la carpeta del principal, `\\import` y
    `\\subfile` a la del archivo que los pide); y el análisis de cada archivo leído (principal incluido)."""
    base = principal.parent
    vistos: list[Path] = [principal.resolve()]
    faltan: list[str] = []
    analisis = [cache.tex(principal)]
    macros: dict[str, str] = {}
    envolturas: set[str] = set()

    def visitar(archivo: Path, dir_actual: Path, datos: dict) -> None:
        for k, v in (datos.get("macros") or {}).items():
            macros.setdefault(k, v)
        envolturas.update(datos.get("envolturas") or ())
        for orden, a, b in datos["inclusiones"]:
            if len(vistos) >= limite:
                return
            if orden == "llamada":                        # \inputAnexos{ruta}: cuenta si la orden envuelve un \input
                if a not in envolturas:
                    continue
                orden, a, b = "input", b, ""
            nombre_crudo = b if orden in ("import", "subimport", "includefrom", "subincludefrom") else a
            if "\\" in nombre_crudo:                       # una macro en la ruta: su valor primero y las demás que casan
                variantes = rutas_con_macros(nombre_crudo, macros, dir_actual if orden.startswith("sub") else base)
                if not variantes:
                    if nombre_crudo not in faltan:
                        faltan.append(nombre_crudo)
                    continue
                for v in variantes:
                    if len(vistos) >= limite:
                        return
                    hallado = _resolver(base, v) or _resolver(dir_actual, v)
                    if hallado is not None and hallado not in vistos:
                        vistos.append(hallado)
                        sub = cache.tex(hallado)
                        analisis.append(sub)
                        visitar(hallado, dir_actual, sub)
                continue
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


_ESQUEMA_DE_CARPETA: dict[str, str] = {}
_DATOS_ESQUEMA: dict[str, tuple[float, dict]] = {}


def documento_de_esquema(principal: Path, clase: str) -> tuple[dict, str] | None:
    """(documentos[i], marco) del `latex-studio.yml` del marco del documento que corresponde a su clase, o None. Se
    guarda por carpeta y por fecha."""
    from latex_app import configuracion as cf
    carpeta = str(principal.parent)
    if carpeta not in _ESQUEMA_DE_CARPETA:
        hallado = cf.buscar_esquema(principal)
        _ESQUEMA_DE_CARPETA[carpeta] = str(hallado) if hallado else ""
    ruta = _ESQUEMA_DE_CARPETA[carpeta]
    if not ruta:
        return None
    try:
        fecha = os.stat(ruta).st_mtime
        if ruta not in _DATOS_ESQUEMA or _DATOS_ESQUEMA[ruta][0] != fecha:
            _DATOS_ESQUEMA[ruta] = (fecha, cf.cargar_esquema(Path(ruta)))
    except (OSError, cf.ErrorEsquema):
        return None
    datos = _DATOS_ESQUEMA[ruta][1]
    for doc in datos.get("documentos") or []:
        clases = doc.get("clases") or []
        if not clases or clase in clases:
            return doc, str(datos.get("marco", ""))
    return None


def categoria_de_esquema(principal: Path, clase: str) -> tuple[str, str, str] | None:
    """(categoría, icono, marco) que declara el `latex-studio.yml` del marco del documento para su clase
    (`documentos[i].categoria`, `docs/configuracion-de-documentos.md` §2), o None."""
    hallado = documento_de_esquema(principal, clase)
    if not hallado or not hallado[0].get("categoria"):
        return None
    doc, marco = hallado
    return str(doc["categoria"]), str(doc.get("icono") or "folder-documents"), marco


def versiones_de_esquema(principal: Path, clase: str) -> dict | None:
    """El bloque `versiones:` que el marco declara para la clase (§7 del contrato), normalizado, o None."""
    hallado = documento_de_esquema(principal, clase)
    bloque = hallado[0].get("versiones") if hallado else None
    if not isinstance(bloque, dict) or not bloque.get("lista"):
        return None
    lista = [{"clave": str(v["clave"]), "nombre": str(v.get("nombre") or v["clave"]), "job": str(v.get("job") or "{nombre}")}
             for v in bloque["lista"] if isinstance(v, dict) and v.get("clave")]
    if not lista:
        return None
    omision = str(bloque.get("omision") or lista[0]["clave"])
    return {"lista": lista, "argumento": str(bloque.get("argumento") or ""), "comentario": str(bloque.get("comentario") or ""),
            "omision": omision if any(v["clave"] == omision for v in lista) else lista[0]["clave"]}


def orden_categoria(nombre: str) -> tuple[int, str]:
    """Cómo se ordenan las categorías: las fijas en su orden, las que declaran los marcos antes de «Pruebas y plantillas»
    y «Otros proyectos» (por nombre)."""
    if nombre in CATEGORIAS:
        i = CATEGORIAS.index(nombre)
        return (i + 1000 if nombre in (CATEGORIAS[-2], CATEGORIAS[-1]) else i, "")
    return (500, nombre)


def categorizar(principal: Path, raiz: Path, clase: str, en_despacho: bool = False) -> tuple[str, str]:
    """(categoría, motivo) con la regla R6; «Otros proyectos» si no hay información."""
    try:
        partes = [raiz.name.lower()] + [p.lower() for p in principal.parent.relative_to(raiz).parts]   # la raíz también cuenta
    except ValueError:
        partes = [p.lower() for p in principal.parent.parts[-3:]]
    prueba = next((p for p in partes if p in _CARPETAS_PRUEBA), "")
    if prueba:
        return PRUEBAS, f"carpeta «{prueba}»"
    if "$" in clase:                                    # plantilla de Pandoc ($documentclass$)
        return PRUEBAS, "plantilla de Pandoc"
    if principal.with_suffix(".qmd").is_file():        # el .tex que Quarto deja junto a su .qmd (keep-tex)
        return QUARTO, f"salida de Quarto de {principal.with_suffix('.qmd').name}"
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
    declarada = categoria_de_esquema(principal, clase)
    if declarada:
        return declarada[0], f"el esquema del marco {declarada[2]}".rstrip()
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
    return OTROS, ""


# ----------------------------------------------------------------------------------------------------- subcategorías
# Bajo cada categoría, hasta dos niveles más (la barra lateral tiene como mucho tres): salen de las carpetas entre la
# carpeta de trabajo y la del proyecto, que en el workspace dicen el tipo de documento y su grupo
# («documentos/oficios/OF-2026-…» → Oficios › 2026; «cursos/econometria-i/04-evaluaciones/examen_parcial/2021_ep» →
# Econometría I › Examen parcial). Se saltan las carpetas de estructura y las que repiten la categoría; la carpeta del
# propio proyecto solo cuenta por su año; una carpeta con `curso.yml` o `proyecto.yaml` se nombra por su `titulo`.

NIVELES_SUBCATEGORIA = 2
_CARPETAS_ESTRUCTURA = {"contenido", "content", "cursos", "courses", "src", "fuentes", "editables", "vista-previa",
                        "latex", "tex", "main", "preliminares", "tables", "tablas", "salidas", "generado", "plan"}
_NOMBRES_CARPETA = {
    "monographs": "Monografías", "reports": "Informes", "articles": "Artículos", "papers": "Artículos",
    "theses": "Tesis", "thesis": "Tesis", "essays": "Ensayos", "books": "Libros", "slides": "Diapositivas",
    "sessions": "Sesiones", "notes": "Notas", "templates": "Plantillas", "examples": "Ejemplos", "tests": "Pruebas",
    "archive": "Archivo", "legacy": "Legado", "pubs": "Publicaciones",
}
# las tildes que los nombres de carpeta (ASCII) pierden; palabras sueltas, en minúscula
_TILDES = {
    "economia": "economía", "econometria": "econometría", "estadistica": "estadística", "matematicas": "matemáticas",
    "matematica": "matemática", "macroeconomia": "macroeconomía", "microeconomia": "microeconomía",
    "organizacion": "organización", "evaluacion": "evaluación", "formulacion": "formulación",
    "investigacion": "investigación", "publica": "pública", "publico": "público", "representacion": "representación",
    "diseno": "diseño", "dinamica": "dinámica", "monografias": "monografías", "monografia": "monografía",
    "articulos": "artículos", "articulo": "artículo", "laminas": "láminas", "lamina": "lámina", "graficos": "gráficos",
    "rendicion": "rendición", "metodos": "métodos", "metodo": "método", "teoria": "teoría", "analisis": "análisis",
    "politica": "política", "economica": "económica", "economico": "económico", "historico": "histórico",
    "galeria": "galería", "practicas": "prácticas", "practica": "práctica", "sesion": "sesión", "educacion": "educación",
    "programacion": "programación", "presentacion": "presentación",
    "comunicacion": "comunicación", "gestion": "gestión", "informacion": "información", "regresion": "regresión",
    "cientifico": "científico", "cientificos": "científicos", "academico": "académico", "academica": "académica",
}
_ROMANOS = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}
# un año al comienzo, quizá tras un código en mayúsculas: «2026-11_SR-04_…», «OF-2026-0012», «OF-BORRADOR-2026», «2021_ep»
_ANIO = re.compile(r"^(?:[A-Z]{1,12}[-_])*(20\d{2})(?=[-_.\s]|$)")
_TITULOS_CARPETA: dict[str, str] = {}


def _normalizar(texto: str) -> str:
    import unicodedata
    sin = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[-_.\s]+", " ", re.sub(r"^\d+[-_.\s]+", "", sin)).strip()


def _titulo_declarado(carpeta: Path) -> str:
    """El `titulo:` del `curso.yml` o del `proyecto.yaml` de una carpeta (sin PyYAML), o ""."""
    clave = str(carpeta)
    if clave not in _TITULOS_CARPETA:
        titulo = ""
        for nombre in ("curso.yml", "proyecto.yaml"):
            f = carpeta / nombre
            if f.is_file():
                m = re.search(r"^titulo\s*:\s*['\"]?(.*?)['\"]?\s*(?:#.*)?$", _leer(f, 16 * 1024), re.M)
                if m and m.group(1).strip():
                    titulo = m.group(1).strip()
                    break
        _TITULOS_CARPETA[clave] = titulo
    return _TITULOS_CARPETA[clave]


def etiqueta_de_carpeta(nombre: str) -> str:
    """El nombre legible de una carpeta: el de `_NOMBRES_CARPETA`, o sin el número de orden («04-»), con espacios,
    tildes, romanos en mayúscula y la primera en mayúscula («econometria-i» → «Econometría I»)."""
    if nombre.lower() in _NOMBRES_CARPETA:
        return _NOMBRES_CARPETA[nombre.lower()]
    limpio = re.sub(r"^\d+[-_.\s]+", "", nombre.lstrip("_")) or nombre
    palabras = []
    for i, w in enumerate(re.split(r"[-_\s]+", limpio)):
        if not w:
            continue
        bajo = w.lower()
        if bajo in _ROMANOS and i > 0:
            palabras.append(bajo.upper())
        elif w != bajo and w != w.capitalize():          # siglas y nombres con mayúsculas propias: tal cual
            palabras.append(w)
        else:
            palabras.append(_TILDES.get(bajo, bajo))
    texto = " ".join(palabras)
    return texto[:1].upper() + texto[1:]


def _repite_categoria(nombre: str, categoria: str) -> bool:
    """La carpeta dice lo mismo que la categoría («documentos» en Documentos institucionales, «docencia» y
    «04-evaluaciones» en Docencia y evaluaciones): no aporta un nivel."""
    palabras = _normalizar(categoria).split()
    for n in {_normalizar(nombre), _normalizar(_NOMBRES_CARPETA.get(nombre.lower().lstrip("_"), ""))} - {""}:
        if n in palabras or any(len(w) >= 5 and len(n) >= 5 and (w.startswith(n) or n.startswith(w)) for w in palabras):
            return True
    return not _normalizar(nombre)


def subclasificar(principal: Path, raiz: Path, categoria: str) -> list[str]:
    """Hasta `NIVELES_SUBCATEGORIA` niveles bajo la categoría para un proyecto, de sus carpetas (ver arriba)."""
    return [etiqueta for etiqueta, _carpeta in subclasificar_con_carpetas(principal, raiz, categoria)]


def subclasificar_con_carpetas(principal: Path, raiz: Path, categoria: str) -> list[tuple[str, str]]:
    """Los niveles de `subclasificar` con la carpeta de la que sale cada uno (relativa a la carpeta de trabajo; "" si
    sale de la carpeta del propio proyecto, su año): la tabla nombra los proyectos desde la carpeta de la rama elegida."""
    try:
        partes = list(principal.parent.relative_to(raiz).parts)
    except ValueError:
        return []
    niveles: list[tuple[str, str]] = []
    carpeta = raiz
    for i, nombre in enumerate(partes):
        carpeta = carpeta / nombre
        propia = i == len(partes) - 1                      # la carpeta del proyecto: solo su año
        anio = _ANIO.match(nombre)
        if anio:
            etiqueta = anio.group(1)
        elif propia:
            continue
        elif nombre.startswith(".") or _normalizar(nombre) in _CARPETAS_ESTRUCTURA or _repite_categoria(nombre, categoria):
            continue
        else:
            etiqueta = _titulo_declarado(carpeta) or etiqueta_de_carpeta(nombre)
        if not niveles or niveles[-1][0] != etiqueta:
            niveles.append((etiqueta, "" if propia else "/".join(partes[:i + 1])))
        if len(niveles) == NIVELES_SUBCATEGORIA:
            break
    return niveles


def nombre_en_rama(relativa: str, subcarpetas: list[str], profundidad: int | None) -> str:
    """El nombre de un proyecto visto desde una rama de la barra lateral: su ruta sin las carpetas que la rama ya dice
    («documentos/oficios/OF-0005-…/oficio.tex» en Documentos institucionales › Oficios → «OF-0005-…/oficio.tex»; en
    Documentos institucionales → «oficios/OF-0005-…/oficio.tex»). `profundidad`: 0 la categoría, 1 y 2 sus niveles;
    None (todos, recientes) deja la ruta entera."""
    if profundidad is None:
        return relativa
    ancla = ""
    if profundidad == 0:
        primera = subcarpetas[0] if subcarpetas else ""
        ancla = primera.rpartition("/")[0] if primera else ""
    else:
        for k in range(min(profundidad, len(subcarpetas)) - 1, -1, -1):
            if subcarpetas[k]:                          # un año de la carpeta del proyecto no se quita: vale el nivel de arriba
                ancla = subcarpetas[k]
                break
        else:
            primera = subcarpetas[0] if subcarpetas else ""
            ancla = primera.rpartition("/")[0] if primera else ""
    return relativa[len(ancla) + 1:] if ancla and relativa.startswith(ancla + "/") else relativa


OTROS_GRUPO = "Otros"
SEPARADOR_GRUPO = " › "


def _orden_grupo(etiqueta: str) -> tuple:
    """Los años primero y del más reciente al más antiguo; luego por nombre; «Otros» al final."""
    if etiqueta == OTROS_GRUPO:
        return (2, 0, "")
    if re.fullmatch(r"20\d{2}", etiqueta):
        return (0, -int(etiqueta), "")
    return (1, 0, _normalizar(etiqueta))


def agrupar(proyectos: Iterable[Proyecto]) -> dict[str, list[str]]:
    """El grupo de cada proyecto en la barra lateral (principal → [categoría, tipo?, grupo?]): un nivel solo se abre
    si separa en dos o más (lo que no tiene ese nivel va a «Otros»); así ninguna rama tiene un único hijo."""
    por_categoria: dict[str, list[Proyecto]] = {}
    for p in proyectos:
        por_categoria.setdefault(p.categoria, []).append(p)
    salida: dict[str, list[str]] = {}

    def repartir(lista: list[Proyecto], prefijo: list[str], nivel: int) -> None:
        if nivel >= NIVELES_SUBCATEGORIA:
            for p in lista:
                salida[p.principal] = prefijo
            return
        valores = {(p.subcategorias[nivel] if len(p.subcategorias) > nivel else None) for p in lista}
        if len(valores - {None}) < 2:
            for p in lista:
                salida[p.principal] = prefijo
            return
        grupos: dict[str, list[Proyecto]] = {}
        for p in lista:
            v = p.subcategorias[nivel] if len(p.subcategorias) > nivel else OTROS_GRUPO
            grupos.setdefault(v, []).append(p)
        for v, sub in grupos.items():
            repartir(sub, prefijo + [v], nivel + 1)

    for categoria, lista in por_categoria.items():
        repartir(lista, [categoria], 0)
    return salida


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
    niveles = subclasificar_con_carpetas(principal, raiz, categoria)
    subcategorias, subcarpetas = [e for e, _c in niveles], [c for _e, c in niveles]
    icono = ""
    if categoria not in CATEGORIAS:
        declarada = categoria_de_esquema(principal, datos["clase"])
        icono = declarada[1] if declarada else ""
    yaml = _proyecto_yaml(principal.parent)
    versiones = versiones_de_esquema(principal, datos["clase"]) if marco is not None else None
    declarada = ""
    if versiones:
        pedida = datos["magicos"].get(versiones["comentario"].upper(), "").strip().lower() if versiones["comentario"] else ""
        declarada = pedida if any(v["clave"] == pedida for v in versiones["lista"]) else versiones["omision"]
    return Proyecto(versiones=versiones["lista"] if versiones else [], version_argumento=versiones["argumento"] if versiones else "",
                    version_comentario=versiones["comentario"] if versiones else "", version_declarada=declarada,
                    version=declarada,
                    principal=str(principal), raiz=str(raiz), clase=datos["clase"],
                    titulo=datos["titulo"] or yaml.get("titulo", ""), motor=motor, motor_origen=origen,
                    bibliografia=bib, compilador=compilador, marco=marco["ruta"] if marco else "",
                    latexmkrc=str(rc) if rc else "", carpeta_aux=carpeta_aux, archivos=[str(a) for a in archivos],
                    no_encontrados=faltan, bibs=bibs, bibs_no_encontradas=bibs_faltan,
                    paquetes=sorted({q for a in analisis for q in a["paquetes"]}), configuracion=configuracion,
                    indice=any(a.get("indice") for a in analisis), glosarios=any(a.get("glosarios") for a in analisis),
                    categoria=categoria, categoria_motivo=motivo, categoria_icono=icono, subcategorias=subcategorias,
                    subcarpetas=subcarpetas)


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
