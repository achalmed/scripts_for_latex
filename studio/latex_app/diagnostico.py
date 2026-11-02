"""latex_app/diagnostico.py — los errores presentables y la revisión de dependencias (sin Qt, se prueba solo).

`explicar(nivel, mensaje)` da a cada problema del registro su causa probable y la acción recomendada (R9): el mensaje
crudo de TeX («LaTeX Error: File `x.sty' not found») no basta para entender qué pasó. `revisar(proyecto)` es la
revisión de dependencias (R16): clases y paquetes que TeX no encuentra, archivos incluidos y `.bib` que no existen,
motor, Biber/BibTeX y el compilador del marco instalados. Solo lee: `kpsewhich` y la carpeta del proyecto.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

# (patrón sobre el mensaje, título comprensible, causa probable, acción recomendada); el primero que casa gana
REGLAS: list[tuple[re.Pattern, str, str, str]] = [
    (re.compile(r"File [`'](?P<x>[^']+\.(?:sty|cls))' not found", re.I),
     "Falta {tipo} «{x}»",
     "TeX no encuentra {x}: el paquete no está instalado en TeX Live, o es la clase de un marco (escritura, el marco "
     "documental) y el documento se compila fuera de él.",
     "Si es de TeX Live: `tlmgr info {base}` o instala el paquete de la distribución (texlive-…). Si es de un marco, "
     "compila con su compilador o añade su carpeta en Ajustes › Rutas de TeX."),
    (re.compile(r"File [`'](?P<x>[^']+)' not found", re.I),
     "No se encuentra el archivo «{x}»",
     "Un \\input, \\include o \\includegraphics apunta a un archivo que no existe o con otra ruta (TeX resuelve "
     "\\input desde la carpeta del documento principal, no desde el capítulo).",
     "Revisa la ruta en la línea indicada; la revisión de dependencias (Ctrl+Mayús+D) lista lo que falta."),
    (re.compile(r"Undefined control sequence", re.I),
     "Orden no definida",
     "Una orden mal escrita o de un paquete que no se cargó en el preámbulo.",
     "Corrige la orden de la línea indicada o añade el \\usepackage que la define."),
    (re.compile(r"Missing \$ inserted", re.I),
     "Falta un $ (modo matemático)",
     "Un símbolo matemático (_, ^, \\alpha…) fuera de $…$, o un $ sin cerrar.",
     "Encierra la fórmula entre $…$ o escapa el carácter (\\_ para un guion bajo en texto)."),
    (re.compile(r"\\begin\{(?P<x>[^}]+)\} on input line (?P<l>\d+) ended by \\end\{(?P<y>[^}]+)\}", re.I),
     "Entorno «{x}» sin cerrar",
     "El \\begin{{{x}}} de la línea {l} se cierra con \\end{{{y}}}: falta un \\end o sobra uno.",
     "Empareja cada \\begin con su \\end entre esas dos líneas."),
    (re.compile(r"Environment (?P<x>\S+) undefined", re.I),
     "Entorno «{x}» no definido",
     "El entorno no existe o es de un paquete que no se cargó.",
     "Añade el paquete que lo define (p. ej. amsmath para align, tabularx para tabularx)."),
    (re.compile(r"Missing \\begin\{document\}", re.I),
     "Texto antes de \\begin{document}",
     "Hay texto o una orden que escribe en el preámbulo.",
     "Mueve ese texto debajo de \\begin{document}."),
    (re.compile(r"Runaway argument|File ended while scanning", re.I),
     "Llave sin cerrar",
     "Un argumento abre { y no lo cierra antes del fin del párrafo o del archivo.",
     "Busca la llave que falta cerca de la línea indicada."),
    (re.compile(r"Extra \}|Missing \} inserted|Too many \}'s", re.I),
     "Llaves desparejadas",
     "Sobra o falta una } en la línea indicada.",
     "Empareja las llaves de esa línea."),
    (re.compile(r"(?:Reference|Etiqueta) [`'](?P<x>[^']+)' .*undefined|There were undefined references", re.I),
     "Referencia indefinida «{x}»",
     "Un \\ref apunta a una \\label que no existe, o falta una pasada más para resolverla.",
     "Comprueba el nombre de la etiqueta (el autocompletado de \\ref la ofrece) y vuelve a compilar."),
    (re.compile(r"Citation [`'](?P<x>[^']+)' .*undefined|There were undefined citations|Empty bibliography", re.I),
     "Cita indefinida «{x}»",
     "La clave no está en los .bib del proyecto, o Biber/BibTeX no corrió (o falló) en esta compilación.",
     "Comprueba la clave en la pestaña Bibliografía; si está, reconstruye (F6) para que corra Biber."),
    (re.compile(r"(?:Cannot find|can't find|Can't find) control file '(?P<x>[^']+\.bcf)'|\.bcf.*(?:not found|No such file)", re.I),
     "Biber sin .bcf",
     "Biber necesita el .bcf que deja la primera pasada del motor: el motor falló antes, o el documento no usa "
     "biblatex (usa \\bibliography, que es BibTeX).",
     "Corrige primero el error del motor y vuelve a compilar; si el documento usa \\bibliography, su bibliografía es "
     "BibTeX (% !BIB program = bibtex)."),
    (re.compile(r"I found no \\(?:citation|bibdata|bibstyle) command", re.I),
     "BibTeX sin citas",
     "BibTeX corrió pero el documento no tiene \\cite, \\bibliography o \\bibliographystyle (o usa biblatex).",
     "Si el documento usa biblatex, su bibliografía es Biber; si no, añade \\bibliography y \\bibliographystyle."),
    (re.compile(r"Label\(s\) may have changed|Rerun to get", re.I),
     "Hace falta otra pasada",
     "Las referencias cambiaron en esta pasada.",
     "Vuelve a compilar (F5)."),
    (re.compile(r"Font .* not (?:found|loadable)|fontspec error", re.I),
     "Fuente no disponible",
     "El documento pide una fuente que no está instalada en el sistema.",
     "Instala la fuente o cambia \\setmainfont; `fc-list | grep -i <nombre>` dice si está."),
    (re.compile(r"TeX capacity exceeded", re.I),
     "Capacidad de TeX excedida",
     "Casi siempre una recursión: un \\input que se incluye a sí mismo o una macro que se llama sin fin.",
     "Revisa la última orden o \\input antes de la línea indicada."),
    (re.compile(r"Overfull \\hbox", re.I),
     "Línea demasiado ancha",
     "Una palabra larga, una URL o una tabla no cabe en la caja.",
     "Reescribe o permite cortes (\\url, \\allowbreak, tabularx); es tipografía, no impide el PDF."),
    (re.compile(r"Underfull \\[hv]box", re.I),
     "Caja poco llena",
     "Espaciado irregular (\\\\ tras un párrafo, \\newline innecesario).",
     "Normalmente es inofensivo; revisa los saltos de línea manuales."),
]


def explicar(nivel: str, mensaje: str) -> dict:
    """{titulo, causa, accion} para un problema; con un mensaje que ninguna regla reconoce, el propio mensaje como
    título y una acción genérica (nunca una explicación inventada)."""
    for patron, titulo, causa, accion in REGLAS:
        m = patron.search(mensaje)
        if m:
            datos = {k: (v or "") for k, v in m.groupdict().items()}
            x = datos.get("x", "")
            datos.setdefault("x", x)
            datos["tipo"] = "la clase" if x.endswith(".cls") else "el paquete"
            datos["base"] = x.rsplit(".", 1)[0] if x else ""
            formato = lambda t: t.format(**datos).replace(" «»", "")
            return {"titulo": formato(titulo), "causa": formato(causa), "accion": formato(accion)}
    if nivel == "error":
        return {"titulo": mensaje.split(".")[0][:120], "causa": "",
                "accion": "Ve a la línea indicada (Intro) y lee el registro completo debajo."}
    return {"titulo": mensaje[:120], "causa": "", "accion": ""}


# ======================================================================================================================
# revisión de dependencias (R16)

def _entorno_tex(proyecto) -> dict:
    """El entorno con el que TeX buscaría los archivos de este proyecto: el del sistema, más las carpetas del marco."""
    env = dict(os.environ)
    if proyecto.marco:
        marco = Path(proyecto.marco)
        extras = [f"{marco / d}//" for d in ("core", "classes", "structures", "esquemas", "universities", "covers", "themes", "assets", "bib")
                  if (marco / d).is_dir()]
        env["TEXINPUTS"] = ".:" + str(marco) + ":" + ":".join(extras) + ":" + env.get("TEXINPUTS", "")
    return env


def kpsewhich(nombres: list[str], carpeta: str, env: dict | None = None) -> set[str]:
    """Cuáles de `nombres` encuentra TeX desde `carpeta` (en lote: una sola llamada)."""
    if not nombres:
        return set()
    if not shutil.which("kpsewhich"):
        return set(nombres)              # sin kpsewhich no se puede comprobar: no se acusa lo que no se sabe
    try:
        r = subprocess.run(["kpsewhich", *nombres], cwd=carpeta, env=env, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return set()
    return {Path(l.strip()).name for l in r.stdout.splitlines() if l.strip()}


def revisar(proyecto) -> list[dict]:
    """Los problemas de dependencias de un proyecto, como filas de Problemas: {nivel, mensaje, archivo, linea, causa,
    accion}. Una lista vacía es «todo está»."""
    salida: list[dict] = []

    def agregar(nivel, mensaje, causa, accion, archivo=""):
        salida.append({"nivel": nivel, "mensaje": mensaje, "archivo": archivo or proyecto.principal, "linea": 0,
                       "titulo": mensaje, "causa": causa, "accion": accion, "detalle": ""})

    motor = proyecto.motor
    if not shutil.which(motor):
        agregar("error", f"No está instalado {motor}", "El motor que declara el proyecto no está en el PATH.",
                f"Instala {motor} (TeX Live) o cambia la declaración del proyecto.")
    if proyecto.bibliografia in ("biber", "bibtex") and not shutil.which(proyecto.bibliografia):
        agregar("error", f"No está instalado {proyecto.bibliografia}", "El proyecto usa bibliografía y su programa falta.",
                f"Instala {proyecto.bibliografia}.")
    if proyecto.compilador == "latexmk" and not shutil.which("latexmk"):
        agregar("error", "No está instalado latexmk", "El proyecto tiene latexmkrc y se compila con latexmk.", "Instala latexmk.")
    if proyecto.compilador == "marco" and not Path(proyecto.marco, "scripts", "build.sh").is_file():
        agregar("error", "No está el compilador del marco", f"Falta {proyecto.marco}/scripts/build.sh.", "Comprueba el marco.")
    for nombre in proyecto.no_encontrados:
        agregar("error", f"No existe «{nombre}»", "Un \\input, \\include o \\subfile apunta a un archivo que no está "
                "(TeX resuelve \\input desde la carpeta del principal).", "Corrige la ruta o crea el archivo.")
    for nombre in proyecto.bibs_no_encontradas:
        env = _entorno_tex(proyecto)
        if not kpsewhich([nombre if nombre.endswith(".bib") else nombre + ".bib"], proyecto.carpeta, env):
            agregar("aviso", f"No se encuentra la bibliografía «{nombre}»", "El .bib no está junto al documento ni en las "
                    "rutas de TeX (BIBINPUTS).", "Comprueba el nombre en \\addbibresource o \\bibliography.")
    pedidos = ([f"{proyecto.clase}.cls"] if proyecto.clase else []) + [f"{p}.sty" for p in proyecto.paquetes if re.fullmatch(r"[\w.-]+", p)]
    if pedidos:
        hallados = kpsewhich(pedidos, proyecto.carpeta, _entorno_tex(proyecto))
        locales = {p.name for p in Path(proyecto.carpeta).glob("*.sty")} | {p.name for p in Path(proyecto.carpeta).glob("*.cls")}
        for nombre in pedidos:
            if nombre not in hallados and nombre not in locales:
                e = explicar("error", f"File `{nombre}' not found")
                agregar("error", e["titulo"], e["causa"], e["accion"])
    return salida
