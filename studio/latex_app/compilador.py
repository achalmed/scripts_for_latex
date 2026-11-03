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
_PARENTESIS = re.compile(r"\((\.?/[^\s()]+\.(?:tex|sty|cls|ltx|def|cfg|fd|lua))|\(|\)")
_CONSECUENCIAS = ("==> Fatal error occurred", "Emergency stop", "LaTeX Error: File ended while")


def _seguir_archivos(linea: str, pila: list[str]) -> None:
    """Mantiene la pila de archivos que el `.log` tiene abiertos: cada «(./ruta» entra, cada «)» saca uno. Los `.tex` del
    documento mandan sobre los paquetes: un error dentro de un `.sty` se atribuye al `.tex` que lo cargó."""
    for m in _PARENTESIS.finditer(linea):
        if m.group(1):
            pila.append(m.group(1))
        elif m.group(0) == "(":
            pila.append("")
        elif pila:
            pila.pop()


def _archivo_de(pila: list[str]) -> str:
    for ruta in reversed(pila):
        if ruta.endswith(".tex") and not ruta.startswith("/"):
            return ruta
    for ruta in reversed(pila):
        if ruta.endswith(".tex"):
            return ruta
    return ""


def leer_log(texto: str) -> list[Problema]:
    """Errores, avisos y avisos tipográficos de un `.log` de LaTeX, en orden, sin repetir; cada uno con el `.tex` que
    el registro tenía abierto (el del documento, no el paquete) y su línea."""
    problemas: list[Problema] = []
    vistos: set[tuple] = set()
    lineas = texto.splitlines()
    pila: list[str] = []

    def agregar(p: Problema) -> None:
        clave = (p.nivel, p.mensaje, p.linea)
        if clave not in vistos:
            vistos.add(clave)
            problemas.append(p)

    i = 0
    while i < len(lineas):
        l = lineas[i]
        _seguir_archivos(l, pila)
        archivo_actual = _archivo_de(pila)
        m = _ERROR_FLE.match(l)
        if m:
            agregar(Problema("error", m["msg"].strip(), int(m["linea"]), m["archivo"]))
        elif l.startswith("! ") and not any(c in l for c in _CONSECUENCIAS):
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


# ======================================================================================================================
# Consultas de la ventana 2.x (2026-11-02): qué documentos hay, qué motor declara cada uno, en qué estado está (leído
# del disco), qué salidas y auxiliares tiene y el progreso de una corrida leído de la salida de la CLI. Nada de Qt.

import hashlib
import os
import shutil
import subprocess
from datetime import datetime

CONFIG = REPO / "script_compilar_latex" / "config.sh"
MOTORES_VENTANA = (("auto", "Automático (LuaLaTeX salvo % !TEX program)"), ("lualatex", "LuaLaTeX"))
NOMBRES_MOTOR = {"lualatex": "LuaLaTeX", "pdflatex": "pdfLaTeX", "xelatex": "XeLaTeX"}
ESTADOS = {"compilado": ("Compilado", "positivo"), "avisos": ("Con avisos", "neutro"), "errores": ("Con errores", "negativo"),
           "desactualizado": ("PDF anterior al .tex", "activo"), "sin_compilar": ("Sin compilar", "inactivo"),
           "compilando": ("Compilando…", "activo")}
_PROGRAMA = re.compile(r"^\s*%\s*!TEX\s+(?:TS-)?program\s*=\s*(\w+)", re.I)
_PASADA = re.compile(r"Pasada (\d+)/(\d+)")
_EXTENSIONES = re.compile(r"EXTENSIONES_AUXILIARES=\((.*?)\)", re.S)
_AUX_INCLUIDO = re.compile(r"\\@input\{([^}]+\.aux)\}")


def motor_declarado(tex: Path) -> str:
    """El motor del comentario mágico `% !TEX program = …` de las 5 primeras líneas (la regla de `lib/detector.sh`); vacío si no hay."""
    try:
        with open(tex, encoding="utf-8", errors="replace") as f:
            for _ in range(5):
                m = _PROGRAMA.match(f.readline())
                if m and m.group(1).lower() in MOTORES:
                    return m.group(1).lower()
    except OSError:
        pass
    return ""


def motor_efectivo(tex: Path, motor: str = "auto") -> str:
    """Con qué motor compilaría la CLI: el pedido o, en `auto`, el declarado o lualatex."""
    return motor if motor != "auto" else (motor_declarado(tex) or "lualatex")


def extensiones_auxiliares() -> tuple[str, ...]:
    """`EXTENSIONES_AUXILIARES` de `config.sh`: la única lista (la ventana no la repite)."""
    m = _EXTENSIONES.search(CONFIG.read_text(encoding="utf-8"))
    return tuple(m.group(1).split()) if m else ("aux", "log", "out", "toc", "bbl", "bcf", "blg", "run.xml")


def auxiliares_de(tex: Path) -> list[Path]:
    """Lo que `main.sh -c` borraría: los `<nombre>.<ext>` que existen y los `.aux` que el `.aux` declara con `\\@input`
    (rutas relativas dentro de la carpeta), en el mismo orden que `listar_auxiliares` de la CLI."""
    salida = [p for p in (tex.parent / f"{tex.stem}.{ext}" for ext in extensiones_auxiliares()) if p.is_file()]
    aux = tex.with_suffix(".aux")
    if aux.is_file():
        for rel in _AUX_INCLUIDO.findall(aux.read_text(encoding="utf-8", errors="replace")):
            if rel.startswith("/") or ".." in rel:
                continue
            p = tex.parent / rel
            if p.is_file() and p not in salida:
                salida.append(p)
    return salida


def pdf_de(tex: Path, salida: str = "") -> Path:
    """Dónde queda el PDF: junto al `.tex` o en la carpeta de salida (`-o`, relativa a la carpeta del `.tex`)."""
    carpeta = (tex.parent / salida) if salida and not os.path.isabs(salida) else (Path(salida) if salida else tex.parent)
    return carpeta / f"{tex.stem}.pdf"


def tamano_legible(n: int) -> str:
    for unidad in ("B", "KB", "MB", "GB"):
        if n < 1024 or unidad == "GB":
            return f"{n} {unidad}" if unidad == "B" else f"{n:.1f} {unidad}"
        n /= 1024
    return f"{n:.1f} GB"


def fecha_legible(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def paginas_pdf(pdf: Path) -> int:
    """Las páginas del PDF según `pdfinfo` (poppler); 0 si no está o falla."""
    if not shutil.which("pdfinfo"):
        return 0
    try:
        r = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, timeout=10)
        m = re.search(r"^Pages:\s+(\d+)", r.stdout, re.M)
        return int(m.group(1)) if m else 0
    except (OSError, subprocess.SubprocessError):
        return 0


def info_pdf(pdf: Path, con_paginas: bool = True) -> dict:
    """ruta, existe, bytes, tamaño, modificado y páginas del PDF."""
    if not pdf.is_file():
        return {"ruta": str(pdf), "existe": False, "bytes": 0, "tamano": "", "modificado": "", "mtime": 0.0, "paginas": 0}
    st = pdf.stat()
    return {"ruta": str(pdf), "existe": True, "bytes": st.st_size, "tamano": tamano_legible(st.st_size),
            "modificado": fecha_legible(st.st_mtime), "mtime": st.st_mtime, "paginas": paginas_pdf(pdf) if con_paginas else 0}


def salidas_de(tex: Path, salida: str = "") -> list[dict]:
    """El PDF (si existe) y los auxiliares que hay en la carpeta, con tipo, tamaño y fecha (la pestaña Salidas)."""
    filas = []
    pdf = pdf_de(tex, salida)
    if pdf.is_file():
        st = pdf.stat()
        filas.append({"ruta": str(pdf), "nombre": pdf.name, "tipo": "PDF", "bytes": st.st_size, "tamano": tamano_legible(st.st_size),
                      "modificado": fecha_legible(st.st_mtime), "mtime": st.st_mtime})
    for p in auxiliares_de(tex):
        st = p.stat()
        filas.append({"ruta": str(p), "nombre": str(p.relative_to(tex.parent)), "tipo": "auxiliar", "bytes": st.st_size,
                      "tamano": tamano_legible(st.st_size), "modificado": fecha_legible(st.st_mtime), "mtime": st.st_mtime})
    return filas


def documentos_en(carpeta: Path) -> list[Path]:
    """Los `.tex` de la carpeta (sin subcarpetas), por nombre."""
    try:
        return sorted((p for p in carpeta.iterdir() if p.is_file() and p.suffix.lower() == ".tex"), key=lambda p: p.name.lower())
    except OSError:
        return []


def registro_de(tex: Path, cache: Path) -> Path:
    """El archivo donde la ventana guarda la salida íntegra de la última corrida de ese documento (`--log`)."""
    clave = hashlib.sha1(str(tex.resolve()).encode("utf-8")).hexdigest()[:12]
    return cache / "registros" / f"{clave}-{tex.stem}.log"


_BANNER_MOTOR = re.compile(r"^This is (?:Lua(?:HB)?TeX|pdfTeX|XeTeX)\b", re.M)
_BIBER = re.compile(r"^(?:(?:INFO|WARN|ERROR) - )?(?P<nivel>ERROR|WARN) - (?P<msg>.+)$", re.M)


def ultima_pasada(texto: str) -> str:
    """Del registro de una corrida (todas las pasadas seguidas), solo la última pasada del motor: los avisos de las
    pasadas anteriores («Citation undefined», «Rerun») no son problemas del documento."""
    posiciones = [m.start() for m in _BANNER_MOTOR.finditer(texto)]
    return texto[posiciones[-1]:] if posiciones else texto


def problemas_de_registro(texto: str) -> list[Problema]:
    """Los problemas de un registro de la ventana (`--log`): los errores y avisos de Biber o BibTeX de toda la corrida y
    los del motor en su última pasada, sin repetir."""
    problemas = [Problema("error" if m["nivel"] == "ERROR" else "aviso", "Biber: " + m["msg"].strip()) for m in _BIBER.finditer(texto)]
    vistos = {(p.nivel, p.mensaje) for p in problemas}
    for p in leer_log(ultima_pasada(texto)):
        if (p.nivel, p.mensaje) not in vistos:
            problemas.append(p)
    orden = {"error": 0, "aviso": 1, "tipografia": 2}
    return sorted(problemas, key=lambda p: orden[p.nivel])


# las líneas del `.blg` de Biber: «[123] Biber.pm:131> WARN - mensaje». Un error de sintaxis nombra la copia temporal
# del `.bib` que Biber pasa a UTF-8 («…/refs.bib_12345.utf8, line 5», o con un hash en lugar del nombre desde la 2.19):
# el `.bib` es el último «Found BibTeX data source '…'» antes del error
_BLG = re.compile(r"^\[\d+\]\s+\S+>\s+(?P<nivel>ERROR|WARN|INFO) - (?P<msg>.+)$", re.M)
_BLG_FUENTE = re.compile(r"Found BibTeX data source '(?P<bib>[^']+)'")
_BLG_LINEA = re.compile(r"(?:(?P<bib>[^\s/,]+\.bib)_\d+)?(?:\.utf8)?, line (?P<linea>\d+)")
_BIBER_CORRIO = re.compile(r"This is Biber|Logfile is '[^']+\.blg'")


def problemas_de_blg(texto: str) -> list[Problema]:
    """Los errores y avisos de Biber leídos de su `.blg` (no de las líneas que imprime): un error de sintaxis llega con
    el `.bib` y la línea; el `.blg` existe también cuando el compilador del proyecto calla a Biber (el del marco)."""
    problemas, fuente = [], ""
    for m in _BLG.finditer(texto):
        mensaje = m["msg"].strip()
        if m["nivel"] == "INFO":
            f = _BLG_FUENTE.search(mensaje)
            fuente = f["bib"] if f else fuente
            continue
        p = Problema("error" if m["nivel"] == "ERROR" else "aviso", "Biber: " + mensaje)
        b = _BLG_LINEA.search(mensaje) if "BibTeX subsystem" in mensaje else None
        if b:
            p.archivo, p.linea = b["bib"] or fuente, int(b["linea"])
        problemas.append(p)
    return problemas


def con_blg(problemas: list[Problema], blg: Path, registro: str = "", mtime_registro: float = 0.0, propio: bool = False) -> list[Problema]:
    """Los problemas de una corrida con los de Biber tomados de su `.blg`, en lugar de las líneas «Biber: …» del
    registro, si el `.blg` es de esta corrida: en el registro de la ventana, si Biber corrió en ella; con el `.log` del
    motor (latexmk, el marco), si el `.blg` es de los cinco minutos anteriores al `.log` (Biber corre entre pasadas)."""
    try:
        mtime_blg = blg.stat().st_mtime
    except OSError:
        return problemas
    if propio:
        if not _BIBER_CORRIO.search(registro):
            return problemas
    elif not (mtime_registro - 300 <= mtime_blg <= mtime_registro + 60):
        return problemas
    de_biber = problemas_de_blg(leer_registro(blg))
    resto = [p for p in problemas if not p.mensaje.startswith("Biber: ")]
    orden = {"error": 0, "aviso": 1, "tipografia": 2}
    return sorted(de_biber + resto, key=lambda p: orden[p.nivel])


def leer_registro(ruta: Path | None) -> str:
    try:
        return ruta.read_text(encoding="utf-8", errors="replace") if ruta and ruta.is_file() else ""
    except OSError:
        return ""


@dataclass
class Estado:
    clave: str                     # compilado · avisos · errores · desactualizado · sin_compilar · compilando
    errores: int = 0
    avisos: int = 0
    tipografia: int = 0
    problemas: list = field(default_factory=list)
    origen: str = ""               # de dónde salieron los problemas (el registro o el .log del motor)

    @property
    def texto(self) -> str:
        return ESTADOS[self.clave][0]

    @property
    def nivel(self) -> str:
        return ESTADOS[self.clave][1]


def estado_de(tex: Path, registro: Path | None = None, salida: str = "", en_curso: bool = False) -> Estado:
    """El estado de un documento leído del disco: el PDF frente al `.tex`, y los problemas del registro más reciente
    (el de la ventana, `registro`, o el `.log` que el motor deja junto al `.tex` cuando una corrida falla)."""
    if en_curso:
        return Estado("compilando")
    candidatos = [p for p in (registro, tex.with_suffix(".log")) if p is not None and p.is_file()]
    problemas, origen, mtime_log = [], "", 0.0
    if candidatos:
        reciente = max(candidatos, key=lambda p: p.stat().st_mtime)
        texto_log = leer_registro(reciente)
        problemas = problemas_de_registro(texto_log) if reciente == registro else leer_log(texto_log)
        origen, mtime_log = str(reciente), reciente.stat().st_mtime
    n = {k: sum(p.nivel == k for p in problemas) for k in ("error", "aviso", "tipografia")}
    pdf = pdf_de(tex, salida)
    hay_pdf = pdf.is_file()
    mtime_pdf = pdf.stat().st_mtime if hay_pdf else 0.0
    try:
        mtime_tex = tex.stat().st_mtime
    except OSError:
        mtime_tex = 0.0
    if n["error"] and (not hay_pdf or mtime_log >= mtime_pdf - 1):
        clave = "errores"
    elif not hay_pdf:
        clave = "sin_compilar"
    elif mtime_pdf < mtime_tex:
        clave = "desactualizado"
    elif n["aviso"] and mtime_log >= mtime_pdf - 60:
        clave = "avisos"
    else:
        clave = "compilado"
    return Estado(clave, n["error"], n["aviso"], n["tipografia"], problemas, origen)


def progreso_de_linea(texto: str):
    """«Pasada n/N con lualatex…» → (porcentaje, «pasada n de N»); otra línea → None (para `Tareas.proceso`)."""
    m = _PASADA.search(texto)
    if not m:
        return None
    n, total = int(m.group(1)), int(m.group(2))
    return (int((n - 1) * 100 / total), f"pasada {n} de {total}")


# ======================================================================================================================
# Recetas por proyecto (reingeniería 2026-11-02, R5 y R8): cada proyecto se compila con su compilador y su motor. La
# ventana no elige otro motor que el del proyecto, nunca escribe fuentes y conserva los auxiliares con `-k` (SyncTeX).

@dataclass
class Paso:
    descripcion: str
    argv: list[str]
    cwd: str
    entorno: dict = field(default_factory=dict)


def _entorno_rutas(rutas_tex: list[str]) -> dict:
    """TEXINPUTS con las rutas de TeX que el usuario añadió en Ajustes (las de un marco, p. ej.); vacío si no hay."""
    rutas = [r for r in rutas_tex if r and os.path.isdir(r)]
    if not rutas:
        return {}
    return {"TEXINPUTS": ".:" + ":".join(r.rstrip("/") + "//" for r in rutas) + ":" + os.environ.get("TEXINPUTS", "")}


def receta(proyecto, que: str = "compilar", registro: Path | None = None, rutas_tex: list[str] = ()) -> list[Paso]:
    """Los pasos de `que` (compilar · reconstruir · limpiar · simular · borrador) para un `proyectos.Proyecto`:
    - marco: `<marco>/scripts/build.sh <principal>` (limpiar: `--clean`; reconstruir: limpiar y compilar);
    - latexmk: `latexmk` con SyncTeX, sin parar en el primer error (lee su `latexmkrc`; limpiar: `-c`; reconstruir: `-g`);
    - main.sh: `main.sh -k -e <motor> [--biber|-b] [-i] [-g] --log <registro>` (limpiar: `-c`; simular: `-n`; reconstruir:
      `-c` y compilar; borrador: `--draft`, comprueba sin PDF). Con otro compilador, borrador es compilar.
    """
    tex = Path(proyecto.principal)
    cwd = str(tex.parent)
    entorno = _entorno_rutas(list(rutas_tex))
    if proyecto.compilador == "marco":
        build = str(Path(proyecto.marco) / "scripts" / "build.sh")
        limpiar = Paso("Limpiar auxiliares (marco)", ["bash", build, "--clean", str(tex)], cwd)
        compilar = Paso("Compilar con el compilador del marco", ["bash", build, str(tex)], cwd)
        if que == "limpiar":
            return [limpiar]
        if que == "reconstruir":
            return [limpiar, compilar]
        if que == "simular":
            return [Paso("Simular (orden del marco)", ["echo", "bash", build, str(tex)], cwd)]
        return [compilar]
    if proyecto.compilador == "latexmk":
        base = ["latexmk", "-synctex=1", "-interaction=nonstopmode", "-file-line-error"]
        if que == "limpiar":
            return [Paso("Limpiar auxiliares (latexmk -c)", ["latexmk", "-c", tex.name], cwd, entorno)]
        if que == "simular":
            return [Paso("Simular (la orden de latexmk)", ["echo", *base, tex.name], cwd, entorno)]
        return [Paso("Compilar con latexmk" + (" (todo de nuevo)" if que == "reconstruir" else ""),
                     base + (["-g"] if que == "reconstruir" else []) + [tex.name], cwd, entorno)]
    argv = ["bash", str(CLI), "-k", "-e", proyecto.motor]
    if proyecto.bibliografia == "biber":
        argv.append("--biber")
    elif proyecto.bibliografia == "bibtex":
        argv.append("-b")
    if getattr(proyecto, "indice", False):
        argv.append("-i")
    if getattr(proyecto, "glosarios", False):
        argv.append("-g")
    limpiar = Paso("Limpiar auxiliares (main.sh -c)", ["bash", str(CLI), "-c", str(tex)], cwd, entorno)
    if que == "limpiar":
        return [limpiar]
    if que == "simular":
        return [Paso("Simular (main.sh -n)", argv + ["-n", str(tex)], cwd, entorno)]
    if registro is not None:
        argv += ["--log", str(registro)]
    if que == "borrador":
        return [Paso("Comprobar sin PDF (borrador)", argv + ["--draft", str(tex)], cwd, entorno)]
    compilar = Paso("Compilar con " + NOMBRES_MOTOR.get(proyecto.motor, proyecto.motor), argv + [str(tex)], cwd, entorno)
    return [limpiar, compilar] if que == "reconstruir" else [compilar]


def orden_legible(pasos: list[Paso]) -> str:
    """Las órdenes de una receta como se escribirían en la terminal (la página Compilación las muestra)."""
    def cita(a: str) -> str:
        return a if re.fullmatch(r"[\w@%+=:,./-]+", a) else "'" + a.replace("'", "'\\''") + "'"
    return "\n".join(" ".join(cita(a) for a in p.argv) for p in pasos)


def registro_motor(proyecto) -> Path:
    """El `.log` del motor de un proyecto (en la carpeta de auxiliares del marco o de latexmk, o junto al principal)."""
    tex = Path(proyecto.principal)
    carpeta = tex.parent / proyecto.carpeta_aux if proyecto.carpeta_aux else tex.parent
    return carpeta / f"{tex.stem}.log"
