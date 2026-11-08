"""latex_app/configuracion.py — la configuración de un documento desde la ventana (sin Qt, se prueba solo).

Cada marco publica un `latex-studio.yml` (contrato: `docs/configuracion-de-documentos.md`) que dice qué se puede
configurar en sus documentos y dónde vive cada valor: una orden del preámbulo (`\\curso{…}`), una orden con clave
(`\\setmeta{titulo}{…}`), una opción de `\\documentclass[…]` o una clave dentro de una lista (`\\configuracion{nivel=false}`).
Este módulo busca el esquema del documento, lee los valores actuales, calcula los cambios (archivo, texto antes y
después, diferencia) y los escribe solo cuando se le pide (`aplicar`). Nada aquí escribe al leer.
"""

from __future__ import annotations

import difflib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

NOMBRES_ESQUEMA = ("latex-studio.yml", "config/latex-studio.yml", "core/config/latex-studio.yml")
NIVELES = 10
TIPOS = ("texto", "texto_largo", "interruptor", "opcion", "numero", "archivo", "fecha")

_BEGIN_DOC = re.compile(r"^[^%\n]*\\begin\s*\{document\}", re.M)
_CLASE = re.compile(r"\\documentclass\s*(?:\[(?P<op>[^\]]*)\])?\s*\{(?P<clase>[^}]+)\}", re.S)

GENERICA = {
    "titulo": "Documento",
    "icono": "document-properties",
    "descripcion": "Lo común a todo documento LaTeX.",
    "campos": [
        {"clave": "_title", "etiqueta": "Título (\\title)", "tipo": "texto", "destino": {"orden": "\\title"}},
        {"clave": "_author", "etiqueta": "Autor (\\author)", "tipo": "texto", "destino": {"orden": "\\author"}},
        {"clave": "_date", "etiqueta": "Fecha (\\date)", "tipo": "texto", "destino": {"orden": "\\date"}},
        {"clave": "_opciones", "etiqueta": "Opciones de la clase", "tipo": "texto",
         "ayuda": "Lo que va entre corchetes en \\documentclass[…], separado por comas.",
         "destino": {"opciones_clase": True}},
    ],
}


class ErrorEsquema(ValueError):
    """Un latex-studio.yml mal formado: el mensaje dice el archivo y el campo."""


@dataclass
class Campo:
    clave: str
    etiqueta: str
    tipo: str
    destino: dict
    ayuda: str = ""
    omision: object = None
    opciones: list = field(default_factory=list)
    valor: object = None            # el valor leído del documento (o la omisión)
    archivo: str = ""               # dónde vive (ruta absoluta)

    def a_dict(self) -> dict:
        return {"clave": self.clave, "etiqueta": self.etiqueta, "tipo": self.tipo, "ayuda": self.ayuda,
                "opciones": list(self.opciones), "valor": self.valor, "archivo": self.archivo,
                "omision": self.omision}


@dataclass
class Seccion:
    titulo: str
    icono: str = "configure"
    descripcion: str = ""
    campos: list[Campo] = field(default_factory=list)

    def a_dict(self) -> dict:
        return {"titulo": self.titulo, "icono": self.icono, "descripcion": self.descripcion,
                "campos": [c.a_dict() for c in self.campos]}


@dataclass
class Configuracion:
    principal: Path
    clase: str
    esquema: Path | None
    marco: str
    nombre: str
    secciones: list[Seccion]

    def campos(self) -> dict[str, Campo]:
        return {c.clave: c for s in self.secciones for c in s.campos}


@dataclass
class Cambio:
    archivo: Path
    antes: str
    despues: str

    def diferencia(self) -> str:
        return "".join(difflib.unified_diff(self.antes.splitlines(True), self.despues.splitlines(True),
                                            fromfile=f"{self.archivo.name} (actual)", tofile=f"{self.archivo.name} (nuevo)",
                                            n=1))


# ----------------------------------------------------------------------------------------------- el esquema

def buscar_esquema(principal: Path) -> Path | None:
    """El `latex-studio.yml` del marco del documento: el primero, subiendo desde su carpeta."""
    carpeta = Path(principal).resolve().parent
    for _ in range(NIVELES):
        for nombre in NOMBRES_ESQUEMA:
            candidato = carpeta / nombre
            if candidato.is_file():
                return candidato
        if carpeta.parent == carpeta:
            break
        carpeta = carpeta.parent
    return None


def cargar_esquema(ruta: Path) -> dict:
    try:
        datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        raise ErrorEsquema(f"{ruta}: no se puede leer ({e})") from e
    if not isinstance(datos, dict) or not isinstance(datos.get("documentos"), list):
        raise ErrorEsquema(f"{ruta}: falta la lista `documentos`")
    for i, doc in enumerate(datos["documentos"]):
        versiones = doc.get("versiones")
        if versiones is not None:
            lista = versiones.get("lista") if isinstance(versiones, dict) else None
            if not isinstance(lista, list) or not lista or not all(isinstance(v, dict) and v.get("clave") for v in lista):
                raise ErrorEsquema(f"{ruta}: documentos[{i}].versiones necesita `lista` con una `clave` por versión")
            if versiones.get("comentario") and not re.fullmatch(r"[A-Za-z][\w-]*", str(versiones["comentario"])):
                raise ErrorEsquema(f"{ruta}: documentos[{i}].versiones.comentario es una palabra (p. ej. MODO)")
        for j, sec in enumerate(doc.get("secciones") or []):
            for k, campo in enumerate(sec.get("campos") or []):
                donde = f"{ruta}: documentos[{i}].secciones[{j}].campos[{k}]"
                if not isinstance(campo, dict) or not campo.get("clave") or not isinstance(campo.get("destino"), dict):
                    raise ErrorEsquema(f"{donde}: cada campo necesita `clave` y `destino`")
                if campo.get("tipo", "texto") not in TIPOS:
                    raise ErrorEsquema(f"{donde}: tipo «{campo.get('tipo')}» desconocido")
    return datos


def _opciones_desde(esquema: Path, regla: dict) -> list[str]:
    carpeta = (esquema.parent / str(regla.get("carpeta", ""))).resolve()
    extension = str(regla.get("extension", ""))
    if not carpeta.is_dir():
        return []
    return sorted(p.name[: -len(extension)] if extension else p.name for p in carpeta.iterdir()
                  if p.is_file() and not p.name.startswith(("_", ".")) and p.name.endswith(extension))


# ----------------------------------------------------------------------------------------------- lectura

def _sin_comentario(linea: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", linea)


def preambulo(texto: str) -> tuple[int, int]:
    """(inicio, fin) del preámbulo dentro del texto: todo lo anterior a \\begin{document} (o el texto entero)."""
    m = _BEGIN_DOC.search(texto)
    return 0, (m.start() if m else len(texto))


def _orden_re(orden: str, clave: str | None) -> re.Pattern:
    base = re.escape(orden) + r"\s*"
    if clave is not None:
        base += r"\{\s*" + re.escape(clave) + r"\s*\}\s*"
    return re.compile(r"^(?P<sangria>[ \t]*)" + base + r"\{(?P<valor>.*)\}(?P<resto>[ \t]*(?:%.*)?)$")


def _buscar_linea(texto: str, patron: re.Pattern) -> tuple[int, re.Match] | None:
    """La última línea del preámbulo (sin contar comentadas) que casa con el patrón: (índice de línea, coincidencia)."""
    _ini, fin = preambulo(texto)
    lineas = texto[:fin].split("\n")
    hallada = None
    for i, linea in enumerate(lineas):
        if linea.lstrip().startswith("%"):
            continue
        m = patron.match(linea)
        if m:
            hallada = (i, m)
    return hallada


def _clase(texto: str) -> re.Match | None:
    _ini, fin = preambulo(texto)
    for m in _CLASE.finditer(texto[:fin]):
        inicio_linea = texto.rfind("\n", 0, m.start()) + 1
        prefijo = texto[inicio_linea:m.start()]
        if _sin_comentario(prefijo) == prefijo:
            return m
    return None


def _partir_opciones(op: str) -> list[str]:
    salida, nivel, actual = [], 0, ""
    for ch in op:
        if ch == "{":
            nivel += 1
        elif ch == "}":
            nivel -= 1
        if ch == "," and nivel == 0:
            salida.append(actual.strip())
            actual = ""
        else:
            actual += ch
    if actual.strip():
        salida.append(actual.strip())
    return [s for s in salida if s]


def _como_bool(valor: object, omision: object = None) -> bool:
    if isinstance(valor, bool):
        return valor
    if valor is None or str(valor).strip() == "":
        return bool(omision)
    return str(valor).strip().lower() in ("true", "1", "si", "sí", "yes")


def _magico_re(nombre: str) -> re.Pattern:
    return re.compile(r"^[ \t]*%[ \t]*![ \t]*" + re.escape(nombre) + r"[ \t]*=[ \t]*(?P<valor>\S[^\n]*?)[ \t]*$", re.M | re.I)


# la línea que hace que el visor de TeXstudio abra el PDF de la versión (manual de TeXstudio, «magic comments»)
_VISOR_TXS = re.compile(r"^[ \t]*%[ \t]*!TeX[ \t]+TXS-program:view[ \t]*=[^\n]*view-pdf-internal[^\n]*\n?", re.M | re.I)


def leer(texto: str, destino: dict, tipo: str, omision: object = None) -> object:
    """El valor de un campo en el texto del archivo (None si no está escrito)."""
    if "version" in destino:
        m = _magico_re(destino["version"]["comentario"]).search(texto[:4000])
        valor = m.group("valor").strip().lower() if m else None
        return valor if valor in destino["version"]["jobs"] else None
    if destino.get("opciones_clase"):
        m = _clase(texto)
        return (m.group("op") or "").strip() if m else None
    if "opcion_clase" in destino:
        m = _clase(texto)
        ops = _partir_opciones(m.group("op") or "") if m else []
        nombre = str(destino["opcion_clase"])
        if tipo == "interruptor":
            return nombre in ops or f"{nombre}=true" in ops
        for o in ops:
            k, _, v = o.partition("=")
            if k.strip() == nombre:
                return v.strip()
        return None
    if "lista" in destino:
        hallada = _buscar_linea(texto, _orden_re(destino["lista"], None))
        if not hallada:
            return None
        for par in _partir_opciones(hallada[1].group("valor")):
            k, _, v = par.partition("=")
            if k.strip() == str(destino.get("clave")):
                return _como_bool(v or "true") if tipo == "interruptor" else v.strip()
        return None
    if "orden" in destino:
        hallada = _buscar_linea(texto, _orden_re(destino["orden"], destino.get("clave")))
        return hallada[1].group("valor") if hallada else None
    return None


# ----------------------------------------------------------------------------------------------- escritura

def _insertar_linea(texto: str, linea: str, anclas: list[re.Pattern]) -> str:
    """Inserta `linea` tras la última línea del preámbulo que case con alguna ancla; si no, tras \\documentclass; si no
    hay clase (un metadata.tex), al final del archivo."""
    _ini, fin = preambulo(texto)
    lineas = texto.split("\n")
    n_pre = texto[:fin].count("\n")
    ultima = -1
    for i in range(min(n_pre + 1, len(lineas))):
        if lineas[i].lstrip().startswith("%"):
            continue
        if any(a.match(lineas[i]) for a in anclas):
            ultima = i
    if ultima < 0:
        m = _clase(texto)
        if m:
            ultima = texto[:m.end()].count("\n")
        else:
            cuerpo = texto.rstrip("\n")
            return (cuerpo + "\n" if cuerpo else "") + linea + "\n"
    lineas.insert(ultima + 1, linea)
    return "\n".join(lineas)


def escribir(texto: str, destino: dict, tipo: str, valor: object, omision: object = None,
             anclas: list[re.Pattern] | None = None) -> str:
    """El texto con el campo puesto en `valor` (sin tocar nada más)."""
    anclas = anclas or []
    if "version" in destino:
        # «% !MODO = soluciones» y la línea del visor de TeXstudio, justo antes de \documentclass; la de omisión no se
        # escribe (quita las dos)
        v = destino["version"]
        texto = re.compile(_magico_re(v["comentario"]).pattern + r"\n?", re.M | re.I).sub("", texto)
        texto = _VISOR_TXS.sub("", texto)
        valor = str(valor or "").strip().lower()
        if not valor or valor == str(v.get("omision") or "") or valor not in v["jobs"]:
            return texto
        pdf = v["jobs"][valor].replace("{nombre}", "?m)") + ".pdf"     # ?m) = el nombre del maestro sin comillas (% las pone)
        nuevas = (f"% !{v['comentario']} = {valor}\n"
                  f"% !TeX TXS-program:view = txs:///view-pdf-internal --embedded {pdf}\n")
        m = _clase(texto)
        inicio = texto.rfind("\n", 0, m.start()) + 1 if m else 0
        return texto[:inicio] + nuevas + texto[inicio:]
    if destino.get("opciones_clase") or "opcion_clase" in destino:
        m = _clase(texto)
        if not m:
            return texto
        ops = _partir_opciones(m.group("op") or "")
        if destino.get("opciones_clase"):
            ops = _partir_opciones(str(valor or ""))
        else:
            nombre = str(destino["opcion_clase"])
            ops = [o for o in ops if o.split("=", 1)[0].strip() != nombre]
            if tipo == "interruptor":
                if _como_bool(valor):
                    ops.append(nombre)
            elif str(valor or "").strip():
                ops.append(f"{nombre}={str(valor).strip()}")
        nueva = "\\documentclass" + (f"[{', '.join(ops)}]" if ops else "") + "{" + m.group("clase") + "}"
        return texto[:m.start()] + nueva + texto[m.end():]

    if "lista" in destino:
        patron = _orden_re(destino["lista"], None)
        hallada = _buscar_linea(texto, patron)
        clave = str(destino.get("clave"))
        pares = _partir_opciones(hallada[1].group("valor")) if hallada else []
        pares = [p for p in pares if p.split("=", 1)[0].strip() != clave]
        es_omision = (_como_bool(valor) == _como_bool(omision, True)) if tipo == "interruptor" else \
            (str(valor or "") == str(omision or ""))
        if not es_omision:
            pares.append(f"{clave}={'true' if _como_bool(valor) else 'false'}" if tipo == "interruptor" else f"{clave}={valor}")
        lineas = texto.split("\n")
        if hallada:
            i, m = hallada
            if pares:
                lineas[i] = f"{m.group('sangria')}{destino['lista']}{{{', '.join(pares)}}}{m.group('resto')}"
            else:
                del lineas[i]
            return "\n".join(lineas)
        if not pares:
            return texto
        return _insertar_linea(texto, f"{destino['lista']}{{{', '.join(pares)}}}", anclas)

    if "orden" in destino:
        orden, clave = destino["orden"], destino.get("clave")
        patron = _orden_re(orden, clave)
        hallada = _buscar_linea(texto, patron)
        valor_txt = "" if valor is None else ("true" if valor is True else "false" if valor is False else str(valor))
        argumentos = (f"{{{clave}}}" if clave is not None else "") + f"{{{valor_txt}}}"
        lineas = texto.split("\n")
        if hallada:
            i, m = hallada
            if valor_txt.strip() == "":
                del lineas[i]
            else:
                lineas[i] = f"{m.group('sangria')}{orden}{argumentos}{m.group('resto')}"
            return "\n".join(lineas)
        if valor_txt.strip() == "":
            return texto
        return _insertar_linea(texto, f"{orden}{argumentos}", anclas + [patron])
    return texto


# ----------------------------------------------------------------------------------------------- el documento

def _archivo_de(principal: Path, destino: dict) -> Path:
    if destino.get("archivo"):
        candidato = principal.parent / str(destino["archivo"])
        if candidato.is_file():
            return candidato
    return principal


def _anclas(campos: list[Campo]) -> list[re.Pattern]:
    salida = []
    for c in campos:
        d = c.destino
        if "orden" in d:
            salida.append(_orden_re(d["orden"], d.get("clave")))
        elif "lista" in d:
            salida.append(_orden_re(d["lista"], None))
    return salida


def buscar_clase(clase: str, rutas: list[Path] | None = None) -> Path | None:
    """El archivo de la clase: en las rutas de TeX extra (las del ajuste, los marcos detectados) o por kpsewhich."""
    import os
    import shutil
    import subprocess
    if not clase:
        return None
    nombre = f"{clase}.cls"
    for ruta in rutas or []:
        ruta = Path(ruta)
        if (ruta / nombre).is_file():
            return ruta / nombre
        for sub in ("classes", "core", "latex", "clases"):
            if (ruta / sub / nombre).is_file():
                return ruta / sub / nombre
    if shutil.which("kpsewhich"):
        entorno = dict(os.environ)
        extra = os.pathsep.join(f"{r}//" for r in (rutas or []))
        if extra:
            entorno["TEXINPUTS"] = extra + os.pathsep + entorno.get("TEXINPUTS", "")
        try:
            r = subprocess.run(["kpsewhich", nombre], capture_output=True, text=True, timeout=10, env=entorno)
            if r.returncode == 0 and r.stdout.strip():
                return Path(r.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            return None
    return None


def _seccion_version(versiones: dict) -> dict:
    """La sección «Versión» de un marco que produce varias versiones de un mismo .tex (`versiones:`, §7 del contrato)."""
    lista = [v for v in versiones["lista"] if isinstance(v, dict) and v.get("clave")]
    omision = str(versiones.get("omision") or lista[0]["clave"])
    nombres = " · ".join(f"{v['clave']}: {v.get('nombre', v['clave'])}" for v in lista)
    return {"titulo": "Versión", "icono": "document-multiple",
            "descripcion": "La versión que compila F5 aquí y en TeXstudio (se escribe como «% !"
                           f"{versiones['comentario']} = …» antes de \\documentclass, con la línea que hace que el visor de "
                           "TeXstudio abra ese PDF). Para compilar otra una sola vez, sin tocar el documento, está el "
                           "selector «Versión» de la ventana.",
            "campos": [{"clave": "_version", "etiqueta": "Versión que compila F5", "tipo": "opcion",
                        "opciones": [v["clave"] for v in lista], "omision": omision, "ayuda": nombres,
                        "destino": {"version": {"comentario": str(versiones["comentario"]), "omision": omision,
                                                "jobs": {str(v["clave"]): str(v.get("job") or "{nombre}") for v in lista}}}}]}


def configuracion_de(principal: Path, clase: str | None = None, rutas: list[Path] | None = None) -> Configuracion:
    """Lo configurable del documento con sus valores actuales. `rutas`: dónde buscar la clase si el esquema no está
    subiendo desde el documento (documentos fuera del árbol de su marco)."""
    principal = Path(principal).resolve()
    texto = principal.read_text(encoding="utf-8", errors="replace")
    if clase is None:
        m = _clase(texto)
        clase = m.group("clase").strip() if m else ""
    esquema = buscar_esquema(principal)
    if esquema is None:
        archivo_clase = buscar_clase(clase or "", rutas)
        if archivo_clase is not None:
            esquema = buscar_esquema(archivo_clase)
    marco, nombre, crudo, generica, versiones = "", "Documento LaTeX", [], True, None
    if esquema:
        datos = cargar_esquema(esquema)
        marco = str(datos.get("marco", esquema.parent.name))
        for doc in datos["documentos"]:
            clases = doc.get("clases") or []
            if not clases or clase in clases:
                nombre = str(doc.get("nombre", nombre))
                crudo = list(doc.get("secciones") or [])
                generica = doc.get("generica", True) is not False
                versiones = doc.get("versiones")
                break
    if generica:
        crudo = crudo + [GENERICA]
    if versiones and versiones.get("comentario"):
        crudo = [_seccion_version(versiones)] + crudo
    secciones = []
    cache: dict[Path, str] = {principal: texto}
    for sec in crudo:
        s = Seccion(titulo=str(sec.get("titulo", "")), icono=str(sec.get("icono", "configure")),
                    descripcion=str(sec.get("descripcion", "")))
        for c in sec.get("campos") or []:
            destino = dict(c["destino"])
            tipo = str(c.get("tipo", "texto"))
            opciones = list(c.get("opciones") or [])
            if not opciones and isinstance(c.get("opciones_desde"), dict) and esquema:
                opciones = _opciones_desde(esquema, c["opciones_desde"])
            archivo = _archivo_de(principal, destino)
            if archivo not in cache:
                cache[archivo] = archivo.read_text(encoding="utf-8", errors="replace")
            valor = leer(cache[archivo], destino, tipo, c.get("omision"))
            if valor is None:
                valor = c.get("omision")
            if tipo == "interruptor":
                valor = _como_bool(valor, c.get("omision"))
            elif valor is None:
                valor = ""
            s.campos.append(Campo(clave=str(c["clave"]), etiqueta=str(c.get("etiqueta", c["clave"])), tipo=tipo,
                                  destino=destino, ayuda=str(c.get("ayuda", "")), omision=c.get("omision"),
                                  opciones=opciones, valor=valor, archivo=str(archivo)))
        secciones.append(s)
    return Configuracion(principal=principal, clase=clase or "", esquema=esquema, marco=marco, nombre=nombre,
                         secciones=secciones)


def cambios(conf: Configuracion, nuevos: dict[str, object]) -> list[Cambio]:
    """Lo que cambiaría en cada archivo si se aplican los valores `nuevos` (clave → valor); sin escribir."""
    campos = conf.campos()
    anclas = _anclas(list(campos.values()))
    textos: dict[Path, str] = {}
    originales: dict[Path, str] = {}
    for clave, valor in nuevos.items():
        c = campos.get(clave)
        if c is None:
            continue
        actual = c.valor
        if c.tipo == "interruptor":
            valor = _como_bool(valor)
        elif valor is None:
            valor = ""
        if valor == actual:
            continue
        archivo = Path(c.archivo)
        if archivo not in textos:
            originales[archivo] = textos[archivo] = archivo.read_text(encoding="utf-8", errors="replace")
        textos[archivo] = escribir(textos[archivo], c.destino, c.tipo, valor, c.omision, anclas)
    return [Cambio(a, originales[a], t) for a, t in textos.items() if t != originales[a]]


def aplicar(lista: list[Cambio]) -> list[Path]:
    """Escribe los cambios, solo si cada archivo sigue como cuando se calcularon (si no, ErrorEsquema)."""
    for c in lista:
        if c.archivo.read_text(encoding="utf-8", errors="replace") != c.antes:
            raise ErrorEsquema(f"{c.archivo.name} cambió desde que se calculó la diferencia: vuelve a abrir la configuración")
    for c in lista:
        escribir_atomico(c.archivo, c.despues)
    return [c.archivo for c in lista]


def escribir_atomico(archivo: Path, texto: str) -> None:
    """Escribe en un temporal de la misma carpeta y lo renombra encima: quien vigila el archivo (el editor, TeXstudio)
    nunca lo ve a medio escribir ni vacío. Si es un enlace, se escribe su destino (el enlace queda); se conservan los
    permisos."""
    destino = Path(os.path.realpath(archivo))
    temporal = destino.with_name(f".{destino.name}.latex-studio-{os.getpid()}")
    temporal.write_text(texto, encoding="utf-8")
    try:
        os.chmod(temporal, os.stat(destino).st_mode & 0o7777)
    except OSError:
        pass
    os.replace(temporal, destino)


# ----------------------------------------------------------------------------------------------- verificación

ORDENES_DE_LATEX = {"\\title", "\\author", "\\date", "\\institute", "\\subtitle", "\\titlegraphic", "\\logo",
                    "\\newcommand", "\\renewcommand", "\\providecommand", "\\def", "\\geometry", "\\setstretch",
                    "\\setlength", "\\setcounter", "\\hypersetup", "\\setmainfont", "\\setsansfont", "\\setmonofont",
                    "\\setmathfont", "\\addbibresource", "\\usetheme", "\\usecolortheme"}


def _raiz_del_marco(esquema: Path) -> Path:
    carpeta = esquema.parent
    if carpeta.name == "config":
        carpeta = carpeta.parent
        if carpeta.name == "core":
            carpeta = carpeta.parent
    return carpeta


def verificar_esquema(ruta: Path) -> list[str]:
    """Los problemas de un latex-studio.yml (vacía si está bien): forma, órdenes y opciones que las clases del marco no
    definen, carpetas de `opciones_desde` que no existen, claves repetidas dentro de un documento."""
    ruta = Path(ruta).resolve()
    try:
        datos = cargar_esquema(ruta)
    except ErrorEsquema as e:
        return [str(e)]
    raiz = _raiz_del_marco(ruta)
    codigo = ""
    for patron in ("*.cls", "*.sty", "*.tex"):
        for f in raiz.rglob(patron):
            if any(p.startswith(".") or p in ("_site", "node_modules", ".build") for p in f.relative_to(raiz).parts):
                continue
            codigo += _leer_seguro(f)
    problemas = []
    for i, doc in enumerate(datos["documentos"]):
        vistas: set[str] = set()
        for sec in doc.get("secciones") or []:
            for c in sec.get("campos") or []:
                donde = f"{doc.get('nombre', i)} › {sec.get('titulo', '')} › {c['clave']}"
                if c["clave"] in vistas:
                    problemas.append(f"{donde}: clave repetida en el documento")
                vistas.add(c["clave"])
                d = c["destino"]
                for orden in (d.get("orden"), d.get("lista")):
                    if orden and orden not in ORDENES_DE_LATEX and not re.search(
                            r"(newcommand|providecommand|renewcommand|NewDocumentCommand|DeclareDocumentCommand|"
                            r"DeclareRobustCommand|def|let)\*?\s*\{?\s*" + re.escape(orden) + r"(?![A-Za-z@])", codigo):
                        problemas.append(f"{donde}: {orden} no está definida en las clases del marco")
                if d.get("lista") and d.get("clave") and not re.search(r"\b" + re.escape(str(d["clave"])) + r"\b", codigo):
                    problemas.append(f"{donde}: la clave «{d['clave']}» de {d['lista']} no aparece en el código del marco")
                if "opcion_clase" in d and not re.search(r"\b" + re.escape(str(d["opcion_clase"])) + r"\b", codigo) \
                        and str(d["opcion_clase"]) not in ("twocolumn", "landscape", "draft", "final", "a4paper", "letterpaper",
                                                           "10pt", "11pt", "12pt", "oneside", "twoside", "openany", "openright",
                                                           "titlepage", "notitlepage", "onecolumn", "fleqn", "leqno"):
                    problemas.append(f"{donde}: la opción de clase «{d['opcion_clase']}» no aparece en las clases del marco")
                if isinstance(c.get("opciones_desde"), dict) and not _opciones_desde(ruta, c["opciones_desde"]):
                    problemas.append(f"{donde}: opciones_desde no lista nada ({c['opciones_desde']})")
    return problemas


def _leer_seguro(f: Path) -> str:
    try:
        return f.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


if __name__ == "__main__":                      # python3 studio/latex_app/configuracion.py <latex-studio.yml>…
    import sys
    codigo_salida = 0
    for argumento in sys.argv[1:]:
        lista = verificar_esquema(Path(argumento))
        print(f"{argumento}: {'bien' if not lista else str(len(lista)) + ' problema(s)'}")
        for p in lista:
            print("  ·", p)
        codigo_salida |= bool(lista)
    sys.exit(codigo_salida)
