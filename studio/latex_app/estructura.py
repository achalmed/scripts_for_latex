"""latex_app/estructura.py — lo que el editor sabe de un proyecto (sin Qt, se prueba solo): la estructura del documento
(partes, capítulos, secciones, figuras, tablas, etiquetas) en el orden en que TeX la lee siguiendo los `\\input`, las
etiquetas para `\\ref`, las claves de los `.bib` para `\\cite` y el autocompletado de órdenes y entornos (R12).
"""

from __future__ import annotations

import re
from pathlib import Path

from latex_app import proyectos as pr

NIVELES = {"part": 0, "chapter": 1, "section": 2, "subsection": 3, "subsubsection": 4, "paragraph": 5, "frametitle": 2}
FLOTANTES = {"figure": "figura", "figure*": "figura", "table": "tabla", "table*": "tabla", "longtable": "tabla",
             "sidewaysfigure": "figura", "sidewaystable": "tabla", "frame": "lámina"}
ICONOS = {"seccion": "format-text-bold", "figura": "image-x-generic", "tabla": "table", "etiqueta": "tag", "lámina": "view-presentation"}

_SECCION = re.compile(r"\\(?P<orden>part|chapter|section|subsection|subsubsection|paragraph|frametitle)(?P<estrella>\*?)"
                      r"\s*(?:\[[^\]]*\])?\s*\{(?P<titulo>(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}")
_INICIO = re.compile(r"\\begin\s*\{(?P<entorno>[^}]+)\}")
_FIN = re.compile(r"\\end\s*\{(?P<entorno>[^}]+)\}")
_LEYENDA = re.compile(r"\\caption\s*(?:\[[^\]]*\])?\s*\{(?P<t>(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}")
_ETIQUETA = re.compile(r"\\label\s*\{(?P<e>[^}]+)\}")
_INCLUSION_LINEA = re.compile(r"\\(?P<orden>input|include|subfile|import|subimport)\s*\{(?P<a>[^}]*)\}(?:\s*\{(?P<b>[^}]*)\})?")
_ENTRADA_BIB = re.compile(r"@(?P<tipo>\w+)\s*\{\s*(?P<clave>[^,\s]+)\s*,", re.I)
_CAMPO_BIB = re.compile(r"\b(?P<campo>title|author|year|date)\s*=\s*[{\"](?P<valor>(?:[^{}\"]|\{[^{}]*\})*)[}\"]", re.I)
_NUEVA_ORDEN = re.compile(r"\\(?:re)?newcommand\*?\s*\{?\\(?P<n>[A-Za-z@]+)\}?|\\DeclareMathOperator\*?\s*\{\\(?P<m>[A-Za-z]+)\}"
                          r"|\\NewDocumentCommand\s*\{?\\(?P<d>[A-Za-z]+)\}?")
_NUEVO_ENTORNO = re.compile(r"\\(?:re)?newenvironment\s*\{(?P<n>[^}]+)\}|\\newtheorem\s*\{(?P<t>[^}]+)\}|\\NewDocumentEnvironment\s*\{(?P<d>[^}]+)\}")

ORDENES = sorted(set("""
section subsection subsubsection chapter part paragraph subparagraph section* subsection* chapter*
textbf textit emph underline texttt textsc textsf textrm textsuperscript textsubscript footnote footnotetext
label ref eqref pageref autoref cref Cref nameref cite parencite textcite autocite footcite citeauthor citeyear nocite
includegraphics caption centering input include subfile import subimport item maketitle tableofcontents listoffigures
listoftables printbibliography addbibresource bibliography bibliographystyle usepackage documentclass newcommand
renewcommand newenvironment begin end hline toprule midrule bottomrule cline multicolumn multirow url href hspace vspace
newpage clearpage noindent par frac dfrac tfrac sqrt sum prod int lim infty partial alpha beta gamma delta epsilon
varepsilon theta lambda mu sigma rho tau phi varphi omega Delta Gamma Sigma Omega cdot cdots ldots times leq geq neq
approx equiv in notin subset cup cap forall exists mathbb mathcal mathbf mathrm text left right quad qquad overline
hat bar tilde vec dot mathit operatorname title author date thanks today appendix frametitle pause
""".split()))
ENTORNOS = sorted(set("""
document figure figure* table table* tabular tabularx longtable equation equation* align align* gather gather* multline
split cases itemize enumerate description center flushleft flushright quote quotation verbatim minipage abstract
theorem lemma proof definition corollary proposition example remark frame block columns column thebibliography
subfigure array matrix pmatrix bmatrix vmatrix tikzpicture axis lstlisting minted landscape appendices
""".split()))
ORDENES_REF = ("ref", "eqref", "pageref", "autoref", "cref", "Cref", "nameref", "vref", "labelcref")
ORDENES_CITA = ("cite", "parencite", "textcite", "autocite", "footcite", "citeauthor", "citeyear", "nocite", "citep",
                "citet", "fullcite", "smartcite", "Cite", "Textcite", "Parencite", "Autocite", "cites", "parencites")


def _limpiar_titulo(t: str) -> str:
    t = re.sub(r"\\(?:textbf|textit|emph|texttt|textsc|mbox|protect)\s*", "", t)
    t = re.sub(r"\\[a-zA-Z]+\*?\s*(?:\{[^{}]*\})?", lambda m: re.sub(r"^\\[a-zA-Z]+\*?\s*\{?|\}$", "", m.group(0)), t)
    return re.sub(r"\s+", " ", t.replace("{", "").replace("}", "").replace("~", " ")).strip()


def _leer_lineas(ruta: Path) -> list[str]:
    try:
        return ruta.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def esquema(principal: str | Path, limite_archivos: int = 300) -> list[dict]:
    """La estructura del documento en orden de lectura: cada sección, figura, tabla, lámina y etiqueta con su tipo,
    título, nivel (para sangrar), archivo y línea (1-based). Sigue `\\input`, `\\include`, `\\subfile`, `\\import`."""
    principal = Path(principal).resolve()
    base = principal.parent
    salida: list[dict] = []
    visitados: set[Path] = set()

    def visitar(archivo: Path, dir_actual: Path, nivel_base: int) -> None:
        if archivo in visitados or len(visitados) >= limite_archivos:
            return
        visitados.add(archivo)
        flotante: dict | None = None
        en_documento = archivo != principal
        for n, linea_cruda in enumerate(_leer_lineas(archivo), start=1):
            linea = pr.sin_comentarios(linea_cruda)
            if not linea.strip():
                continue
            if not en_documento and "\\begin{document}" in linea:
                en_documento = True
            for m in _SECCION.finditer(linea):
                if not en_documento:
                    continue
                orden = m["orden"]
                salida.append({"tipo": "seccion", "orden": orden + m["estrella"], "titulo": _limpiar_titulo(m["titulo"]) or "(sin título)",
                               "nivel": NIVELES[orden], "archivo": str(archivo), "linea": n})
            for m in _INICIO.finditer(linea):
                entorno = m["entorno"].strip()
                if entorno in FLOTANTES and en_documento:
                    flotante = {"tipo": FLOTANTES[entorno], "orden": entorno, "titulo": "", "nivel": 6, "archivo": str(archivo),
                                "linea": n, "etiqueta": ""}
                    salida.append(flotante)
            if flotante is not None:
                mc = _LEYENDA.search(linea)
                if mc and not flotante["titulo"]:
                    flotante["titulo"] = _limpiar_titulo(mc["t"])
            for m in _ETIQUETA.finditer(linea):
                if flotante is not None and not flotante.get("etiqueta"):
                    flotante["etiqueta"] = m["e"]
                elif en_documento:
                    salida.append({"tipo": "etiqueta", "orden": "label", "titulo": m["e"], "nivel": 7, "archivo": str(archivo), "linea": n})
            for m in _FIN.finditer(linea):
                if m["entorno"].strip() in FLOTANTES and flotante is not None:
                    if not flotante["titulo"]:
                        flotante["titulo"] = flotante.get("etiqueta") or f"({flotante['tipo']} sin leyenda)"
                    flotante = None
            for m in _INCLUSION_LINEA.finditer(linea):
                orden, a, b = m["orden"], m["a"], m["b"] or ""
                if orden == "import":
                    hallado, nuevo = pr._resolver(base / a, b), base / a
                elif orden == "subimport":
                    hallado, nuevo = pr._resolver(dir_actual / a, b), dir_actual / a
                elif orden == "subfile":
                    hallado = pr._resolver(dir_actual, a) or pr._resolver(base, a)
                    nuevo = hallado.parent if hallado else dir_actual
                else:
                    hallado, nuevo = pr._resolver(base, a) or pr._resolver(dir_actual, a), dir_actual
                if hallado is not None:
                    visitar(hallado, nuevo, nivel_base)

    visitar(principal, base, 0)
    for e in salida:
        e["icono"] = ICONOS.get(e["tipo"], "text-x-generic")
    return salida


def etiquetas(archivos: list[str]) -> list[dict]:
    """Las `\\label` de los archivos del proyecto: nombre, archivo, línea y el contexto (la línea, recortada)."""
    salida, vistas = [], set()
    for ruta in archivos:
        for n, linea in enumerate(_leer_lineas(Path(ruta)), start=1):
            for m in _ETIQUETA.finditer(pr.sin_comentarios(linea)):
                if m["e"] not in vistas:
                    vistas.add(m["e"])
                    salida.append({"nombre": m["e"], "archivo": ruta, "linea": n, "detalle": linea.strip()[:80]})
    return salida


def claves_bib(bibs: list[str]) -> list[dict]:
    """Las entradas de los `.bib`: clave, tipo, autor, año y título (para `\\cite` y la pestaña Bibliografía)."""
    salida, vistas = [], set()
    for ruta in bibs:
        try:
            texto = Path(ruta).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        posiciones = [(m.start(), m) for m in _ENTRADA_BIB.finditer(texto)]
        for i, (inicio, m) in enumerate(posiciones):
            if m["tipo"].lower() in ("comment", "string", "preamble"):
                continue
            fin = posiciones[i + 1][0] if i + 1 < len(posiciones) else len(texto)
            cuerpo = texto[inicio:fin]
            campos = {c["campo"].lower(): re.sub(r"\s+", " ", c["valor"].replace("{", "").replace("}", "")).strip()
                      for c in _CAMPO_BIB.finditer(cuerpo)}
            clave = m["clave"]
            if clave in vistas:
                continue
            vistas.add(clave)
            salida.append({"nombre": clave, "tipo": m["tipo"].lower(), "autor": campos.get("author", ""),
                           "anio": campos.get("year", campos.get("date", "")[:4]), "titulo": campos.get("title", ""),
                           "archivo": ruta, "linea": texto.count("\n", 0, inicio) + 1})
    return salida


def definiciones(archivos: list[str]) -> tuple[list[str], list[str]]:
    """Las órdenes y entornos que el proyecto define (`\\newcommand`, `\\newenvironment`, `\\newtheorem`…)."""
    ordenes, entornos = set(), set()
    for ruta in archivos:
        texto = pr.sin_comentarios("\n".join(_leer_lineas(Path(ruta))))
        for m in _NUEVA_ORDEN.finditer(texto):
            ordenes.add(m["n"] or m["m"] or m["d"])
        for m in _NUEVO_ENTORNO.finditer(texto):
            entornos.add((m["n"] or m["t"] or m["d"]).strip())
    return sorted(ordenes), sorted(entornos)


_CONTEXTO_REF = re.compile(r"\\(?P<orden>[A-Za-z]+)\*?\s*(?:\[[^\]]*\]\s*){0,2}\{(?P<previas>[^{}]*,)?(?P<prefijo>[^{},]*)$")
_CONTEXTO_ENTORNO = re.compile(r"\\(?:begin|end)\s*\{(?P<prefijo>[^{}]*)$")
_CONTEXTO_ORDEN = re.compile(r"\\(?P<prefijo>[A-Za-z@]*)$")


def completar(antes: str, etiquetas_: list[dict], claves: list[dict], ordenes_extra: list[str] = (),
              entornos_extra: list[str] = (), limite: int = 60) -> dict:
    """Qué ofrecer en el cursor, según el texto de la línea antes de él: `\\ref{` → etiquetas, `\\cite{` (o tras una coma
    dentro de las llaves) → claves de los `.bib`, `\\begin{` → entornos, `\\xx` → órdenes. Devuelve {tipo, prefijo,
    elementos: [{texto, detalle, insertar}]} o tipo vacío si no hay nada que ofrecer."""
    m = _CONTEXTO_ENTORNO.search(antes)
    if m:
        prefijo = m["prefijo"]
        candidatos = sorted(set(ENTORNOS) | set(entornos_extra))
        elementos = [{"texto": e, "detalle": "entorno", "insertar": e} for e in candidatos if e.startswith(prefijo)]
        return {"tipo": "entorno", "prefijo": prefijo, "elementos": elementos[:limite]}
    m = _CONTEXTO_REF.search(antes)
    if m and (m["orden"] in ORDENES_REF or m["orden"] in ORDENES_CITA):
        prefijo = m["prefijo"].strip()
        if m["orden"] in ORDENES_REF:
            elementos = [{"texto": e["nombre"], "detalle": Path(e["archivo"]).name + f":{e['linea']}", "insertar": e["nombre"]}
                         for e in etiquetas_ if prefijo.lower() in e["nombre"].lower()]
            return {"tipo": "etiqueta", "prefijo": prefijo, "elementos": elementos[:limite]}
        p = prefijo.lower()
        elementos = [{"texto": c["nombre"], "detalle": " · ".join(x for x in (c.get("autor", "")[:40], c.get("anio", ""), c.get("titulo", "")[:60]) if x),
                      "insertar": c["nombre"]}
                     for c in claves if p in c["nombre"].lower() or p in c.get("autor", "").lower() or p in c.get("titulo", "").lower()]
        return {"tipo": "cita", "prefijo": prefijo, "elementos": elementos[:limite]}
    m = _CONTEXTO_ORDEN.search(antes)
    if m:
        prefijo = m["prefijo"]
        candidatos = sorted(set(ORDENES) | set(ordenes_extra))
        elementos = [{"texto": "\\" + o, "detalle": "definida en el proyecto" if o in ordenes_extra else "", "insertar": o}
                     for o in candidatos if o.startswith(prefijo) and o != prefijo]
        return {"tipo": "orden", "prefijo": prefijo, "elementos": elementos[:limite]}
    return {"tipo": "", "prefijo": "", "elementos": []}
