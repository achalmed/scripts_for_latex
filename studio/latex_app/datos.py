"""latex_app/datos.py — los datos del proyecto que declara su marco: qué figuras, tablas y cifras puede citar el documento, con qué orden se insertan, cómo se traen a la última versión y qué programa las produce (sin Qt).

Objetivo: que el autor que escribe un informe vea, junto al editor, lo que sus paquetes de datos le dan para citar
  (`\\figv{…}`, `\\input{tables/…}`, `\\cifra…`), sepa si hay una versión más nueva y la traiga sin salir de la ventana.
Método: la sección `datos:` del `latex-studio.yml` del marco (contrato: `docs/configuracion-de-documentos.md` §8) da
  tres órdenes: `recursos` (devuelve JSON), `actualizar` y `productor.orden`. Los argumentos que empiezan con «.» son
  rutas relativas al esquema y `{proyecto}`, la carpeta más cercana al principal que tiene el `marcador` del marco.
  La ventana no sabe qué es un paquete ni quién lo produce: corre lo que el marco declara.
Fundamento: decisión de diseño (docs/decisiones.md §1.16): lo configurable lo declara el marco, la ventana no sabe
  nada de ningún marco (regla del repo); el contrato de escritura con datafw es suyo (`escritura/docs/datos-y-fuentes.md`).
Alternativa: leer los paquetes de datafw desde aquí. Se descarta: LaTeX Studio es público y autónomo, y un marco sin
  datafw (docencia, el CV) no debe cargar nada de eso.
Las demás secciones del contrato se leen igual: `biblioteca:` (§9), `ayuda:` (§10), `nuevo:` (§11), `entrega:` (§12,
  «Antes de entregar»: `declaracion_entrega`, `resultado_entrega`, `veredicto` y `uso_de_ia`; decisiones §1.21), y con
  `declaracion_seccion` las de §13 a §15: `matriz:` (la matriz de consistencia), `revisor:` (estilo y LaTeX en el
  editor) y `plantillas:` (decisiones §1.22 a §1.24).
Límite: `recursos` tiene 60 s; una orden que no existe o no devuelve JSON se informa como error, sin datos.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from latex_app import configuracion

TOPE_RECURSOS = 60
NIVELES_PROYECTO = 6


def _resolver(argv: list, esquema: Path, proyecto: Path) -> list[str]:
    salida = []
    for a in argv or []:
        a = str(a).replace("{proyecto}", str(proyecto))
        salida.append(str((esquema.parent / a).resolve()) if a.startswith(".") else a)
    return salida


def con(argv: list[str], **valores) -> list[str]:
    """La orden con sus huecos llenos ({texto}, {id}…), ya resueltas las rutas."""
    return [a.format(**valores) if "{" in a else a for a in argv]


def _json(argv: list[str], cwd: str, tope: int = TOPE_RECURSOS):
    """Corre una orden del marco que imprime JSON; (dato, error)."""
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=tope, cwd=cwd)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, f"{argv[0]}: {e}"
    if r.returncode != 0:
        texto = (r.stderr or r.stdout).strip()
        return None, texto.splitlines()[-1] if texto else f"código {r.returncode}"
    try:
        return json.loads(r.stdout), ""
    except ValueError:
        return None, "la orden no devolvió JSON"


def declaracion_biblioteca(principal: str | Path) -> dict | None:
    """La sección `biblioteca:` del esquema del marco (contrato §9), con sus órdenes resueltas; None si no la declara."""
    if not principal:
        return None
    esquema = configuracion.buscar_esquema(Path(principal))
    if esquema is None:
        return None
    try:
        import yaml
        b = (yaml.safe_load(esquema.read_text(encoding="utf-8")) or {}).get("biblioteca")
    except Exception:
        return None
    if not isinstance(b, dict) or not b.get("buscar"):
        return None
    proyecto = _proyecto(Path(principal), str(b.get("marcador") or "")) if b.get("marcador") else Path(principal).resolve().parent
    if proyecto is None:
        return None
    return {"nombre": str(b.get("nombre") or "Biblioteca"), "proyecto": str(proyecto),
            **{k: _resolver(b.get(k) or [], esquema, proyecto) for k in ORDENES_BIBLIOTECA}}


# Las órdenes de `biblioteca:` (§9): buscar, fichas, citar y abrir (§1.18); fichar desde la ventana (§1.19): el formulario
# de una ficha, leer una para editarla, simular o escribir una nueva y corregir una con su huella.
ORDENES_BIBLIOTECA = ("buscar", "fichas", "citar", "abrir", "formulario", "ficha", "nueva_ficha", "guardar_ficha")


def declaracion_ayuda(principal: str | Path) -> dict | None:
    """La sección `ayuda:` del esquema del marco (contrato §10: el prompt de la parte abierta y la lectura de lo que el
    chat devolvió), con sus órdenes resueltas; None si no la declara o no aplica."""
    if not principal:
        return None
    esquema = configuracion.buscar_esquema(Path(principal))
    if esquema is None:
        return None
    try:
        import yaml
        a = (yaml.safe_load(esquema.read_text(encoding="utf-8")) or {}).get("ayuda")
    except Exception:
        return None
    if not isinstance(a, dict) or not a.get("prompt"):
        return None
    proyecto = _proyecto(Path(principal), str(a.get("marcador") or "")) if a.get("marcador") else Path(principal).resolve().parent
    if proyecto is None:
        return None
    return {"nombre": str(a.get("nombre") or "Ayuda de la IA"), "proyecto": str(proyecto),
            **{k: _resolver(a.get(k) or [], esquema, proyecto) for k in ("prompt", "pegar", "revisar_prompt")}}


def declaracion_nuevo(carpeta: str | Path) -> dict | None:
    """La sección `nuevo:` (contrato §11: qué documentos se pueden crear y crearlos) del esquema del marco de la carpeta
    de trabajo `carpeta` (el esquema en ella o en una carpeta de arriba), con sus órdenes resueltas; None si no la declara."""
    if not carpeta or not Path(carpeta).is_dir():
        return None
    esquema = configuracion.buscar_esquema(Path(carpeta) / "_")          # buscar_esquema sube desde la carpeta del archivo
    if esquema is None:
        return None
    try:
        import yaml
        todo = yaml.safe_load(esquema.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    n = todo.get("nuevo") if isinstance(todo, dict) else None
    if not isinstance(n, dict) or not n.get("tipos") or not n.get("crear"):
        return None
    return {"nombre": str(n.get("nombre") or todo.get("marco") or esquema.parent.name), "marco": str(todo.get("marco") or ""),
            "esquema": str(esquema), "carpeta": str(Path(carpeta).resolve()),
            "tipos": _resolver(n["tipos"], esquema, Path(carpeta)), "crear": _resolver(n["crear"], esquema, Path(carpeta))}


def declaraciones_nuevo(carpetas) -> list[dict]:
    """Las secciones `nuevo:` de las carpetas de trabajo y de los marcos detectados: una por esquema, en su orden."""
    salida, vistos = [], set()
    for carpeta in carpetas:
        d = declaracion_nuevo(carpeta)
        if d is not None and d["esquema"] not in vistos:
            vistos.add(d["esquema"])
            salida.append(d)
    return salida


def _proyecto(principal: Path, marcador: str) -> Path | None:
    carpeta = Path(principal).resolve().parent
    for _ in range(NIVELES_PROYECTO):
        if (carpeta / marcador).is_file():
            return carpeta
        if carpeta.parent == carpeta:
            break
        carpeta = carpeta.parent
    return None


def declaracion(principal: str | Path) -> dict | None:
    """Lo que el marco declara para los datos del documento, con las órdenes resueltas; None si no declara o no aplica."""
    if not principal:
        return None
    esquema = configuracion.buscar_esquema(Path(principal))
    if esquema is None:
        return None
    try:
        import yaml
        datos = (yaml.safe_load(esquema.read_text(encoding="utf-8")) or {}).get("datos")
    except Exception:
        return None
    if not isinstance(datos, dict) or not datos.get("recursos"):
        return None
    proyecto = _proyecto(Path(principal), str(datos.get("marcador") or "")) if datos.get("marcador") else Path(principal).resolve().parent
    if proyecto is None:
        return None
    productor = datos.get("productor") or {}
    return {"nombre": str(datos.get("nombre") or "Datos"), "proyecto": str(proyecto), "esquema": str(esquema),
            "recursos": _resolver(datos["recursos"], esquema, proyecto),
            "actualizar": _resolver(datos.get("actualizar") or [], esquema, proyecto),
            "productor": {"nombre": str(productor.get("nombre") or ""), "orden": _resolver(productor.get("orden") or [], esquema, proyecto)}}


def recursos(decl: dict) -> dict:
    """{paquetes, figuras, tablas, cifras} que devuelve la orden `recursos` del marco; con `error` si falló."""
    vacio = {"paquetes": [], "figuras": [], "tablas": [], "cifras": []}
    try:
        r = subprocess.run(decl["recursos"], capture_output=True, text=True, timeout=TOPE_RECURSOS, cwd=decl["proyecto"])
    except (OSError, subprocess.TimeoutExpired) as e:
        return {**vacio, "error": f"{decl['recursos'][0]}: {e}"}
    if r.returncode != 0:
        return {**vacio, "error": (r.stderr or r.stdout).strip().splitlines()[-1:][0] if (r.stderr or r.stdout).strip() else f"código {r.returncode}"}
    try:
        d = json.loads(r.stdout)
    except ValueError:
        return {**vacio, "error": "la orden de recursos no devolvió JSON"}
    return {**vacio, **{k: d.get(k) or [] for k in vacio}}


# Las órdenes de `entrega:` (§12, decisiones §1.21): los controles antes de entregar, marcar un punto manual y registrar
# un uso de la IA; desde §1.21, medir los controles, declarar un falso positivo, el tiempo por etapa y entregar
# el PDF con el candado de «Faltan N».
ORDENES_ENTREGA = ("revisar", "marcar", "registrar_ia", "rubrica", "autoevaluar", "lector_frio", "medir", "falso", "tiempo",
                   "entregar")
ESTADOS_ENTREGA = ("ok", "aviso", "falla", "manual")


def declaracion_entrega(principal: str | Path) -> dict | None:
    """La sección `entrega:` del esquema del marco (contrato §12), con sus órdenes resueltas; None si no la declara o no
    aplica (sin `revisar`, o sin la carpeta del `marcador`)."""
    if not principal:
        return None
    esquema = configuracion.buscar_esquema(Path(principal))
    if esquema is None:
        return None
    try:
        import yaml
        e = (yaml.safe_load(esquema.read_text(encoding="utf-8")) or {}).get("entrega")
    except Exception:
        return None
    if not isinstance(e, dict) or not e.get("revisar"):
        return None
    proyecto = _proyecto(Path(principal), str(e.get("marcador") or "")) if e.get("marcador") else Path(principal).resolve().parent
    if proyecto is None:
        return None
    return {"nombre": str(e.get("nombre") or "Antes de entregar"), "proyecto": str(proyecto),
            **{k: _resolver(e.get(k) or [], esquema, proyecto) for k in ORDENES_ENTREGA}}


def resultado_entrega(dato, proyecto: str | Path) -> dict:
    """Lo que devolvió `revisar`, listo para la ventana: cada hallazgo con su `ruta` absoluta (el `archivo` es relativo a
    {proyecto}), los grupos en su orden y el veredicto. Nunca lanza: lo mal formado vuelve como {error}."""
    if not isinstance(dato, dict):
        return {"error": "la orden no devolvió los controles", "controles": [], "grupos": [], **veredicto([])}
    if dato.get("error"):
        return {"error": str(dato["error"]), "controles": [], "grupos": [], **veredicto([])}
    base = Path(proyecto)
    controles = []
    for c in dato.get("controles") or []:
        if not isinstance(c, dict) or c.get("estado") not in ESTADOS_ENTREGA:
            continue
        hallazgos = []
        for h in c.get("hallazgos") or []:
            archivo = str(h.get("archivo") or "")
            ruta = str(archivo if Path(archivo).is_absolute() else base / archivo) if archivo else ""
            hallazgos.append({"archivo": archivo, "ruta": ruta, "linea": int(h.get("linea") or 0), "texto": str(h.get("texto") or "")})
        controles.append({**c, "grupo": str(c.get("grupo") or ""), "modo": str(c.get("modo") or ""),
                          "marcado": str(c.get("marcado") or ""), "nota": str(c.get("nota") or ""), "hallazgos": hallazgos})
    grupos = [g for g in dato.get("grupos") or [] if isinstance(g, dict) and g.get("clave")]
    vistos = {g["clave"] for g in grupos}
    for c in controles:                                     # un grupo que el marco no nombró, con su clave
        if c["grupo"] not in vistos:
            vistos.add(c["grupo"])
            grupos.append({"clave": c["grupo"], "nombre": c["grupo"].capitalize() or "Otros"})
    lista = dato.get("lista") if isinstance(dato.get("lista"), dict) else {}
    return {"error": "", "controles": controles, "grupos": grupos, "lista": lista or {}, "tipo": str(dato.get("tipo") or ""),
            "maestro": str(dato.get("maestro") or ""), "carpeta": str(dato.get("carpeta") or proyecto or ""), **veredicto(controles)}


def resultado_tiempos(dato) -> dict:
    """Lo que devolvió `tiempo` de `entrega:` sin etapa (§12, decisiones §1.21): la etapa en curso, los minutos por etapa,
    el total y las etapas que se pueden marcar, con su porqué y su fuente. Nunca lanza."""
    vacio = {"error": "", "abierta": None, "etapas": [], "opciones": [], "total": 0, "porque": "", "fuente": ""}
    if not isinstance(dato, dict):
        return {**vacio, "error": "la orden no devolvió el tiempo por etapa"}
    if dato.get("error"):
        return {**vacio, "error": str(dato["error"])}
    abierta = dato.get("abierta") if isinstance(dato.get("abierta"), dict) else None
    etapas = [{"etapa": str(e.get("etapa") or ""), "nombre": str(e.get("nombre") or e.get("etapa") or ""),
               "minutos": int(e.get("minutos") or 0)} for e in dato.get("etapas") or [] if isinstance(e, dict)]
    opciones = [{"clave": str(o.get("clave") or ""), "nombre": str(o.get("nombre") or o.get("clave") or "")}
                for o in dato.get("opciones") or [] if isinstance(o, dict) and o.get("clave")]
    return {**vacio, "etapas": etapas, "opciones": opciones or [{"clave": e["etapa"], "nombre": e["nombre"]} for e in etapas],
            "total": int(dato.get("total") or 0), "porque": str(dato.get("porque") or ""), "fuente": str(dato.get("fuente") or ""),
            "abierta": ({"etapa": str(abierta.get("etapa") or ""), "nombre": str(abierta.get("nombre") or abierta.get("etapa") or ""),
                         "minutos": int(abierta.get("minutos") or 0)} if abierta and abierta.get("etapa") else None)}


def duracion(minutos: int) -> str:
    """«45 min», «2 h», «3 h 10 min»."""
    h, m = divmod(max(0, int(minutos or 0)), 60)
    return f"{h} h {m} min" if h and m else f"{h} h" if h else f"{m} min"


def veredicto(controles: list[dict]) -> dict:
    """«Listo para entregar» solo si no hay fallas y todo lo manual está marcado o justificado (decisiones §1.21): la
    ventana decide con lo que el marco revisó; ninguna lista bloquea por su cuenta."""
    fallas = sum(1 for c in controles if c.get("estado") == "falla")
    pendientes = sum(1 for c in controles if c.get("estado") == "manual" and not c.get("marcado"))
    avisos = sum(1 for c in controles if c.get("estado") == "aviso")
    return {"fallas": fallas, "pendientes": pendientes, "avisos": avisos, "faltan": fallas + pendientes,
            "listo": bool(controles) and fallas == 0 and pendientes == 0}


def uso_de_ia(proyecto: str | Path, ruta: str, parte: str, prompt: dict, antes: str, despues: str, fecha: str = "") -> dict:
    """El uso de la IA que se registra al aceptar un cambio sugerido (contrato §12, `registrar_ia`): el archivo relativo a
    {proyecto}, la parte, el prompt (título, ruta, versión y su texto, del que el marco guarda la huella) y el resumen."""
    try:
        archivo = str(Path(ruta).resolve().relative_to(Path(proyecto).resolve()))
    except (ValueError, OSError):
        archivo = str(ruta)
    n_antes = len([l for l in (antes or "").splitlines() if l.strip()])
    n_despues = len([l for l in (despues or "").splitlines() if l.strip()])
    resumen = (f"reemplazó {n_antes} línea{'s' if n_antes != 1 else ''} de texto por {n_despues}" if n_antes
               else f"añadió {n_despues} línea{'s' if n_despues != 1 else ''} de texto")
    uso = {"archivo": archivo, "parte": parte or "", "prompt": {k: v for k, v in (prompt or {}).items() if v}, "resumen": resumen}
    if fecha:
        uso["fecha"] = fecha
    return uso


# Las secciones §13 a §15 (decisiones §1.22 a §1.24): la matriz de consistencia, el revisor del editor y las plantillas.
# Todas se leen igual: el esquema del marco, la carpeta del `marcador` y las órdenes resueltas.
SECCIONES = {
    "matriz": {"nombre": "Matriz de consistencia", "requerida": "leer", "ordenes": ("leer", "cuadro", "nueva", "guia", "pregunta")},
    "revisor": {"nombre": "Revisión", "requerida": "revisar", "ordenes": ("revisar", "reglas")},
    "plantillas": {"nombre": "Plantillas", "requerida": "listar", "ordenes": ("listar", "componer")},
}


def declaracion_seccion(principal: str | Path, seccion: str) -> dict | None:
    """La sección `seccion` (matriz, revisor o plantillas) del esquema del marco, con sus órdenes resueltas; None si no
    la declara, le falta su orden principal o no se encuentra la carpeta de su `marcador`."""
    forma = SECCIONES[seccion]
    if not principal:
        return None
    esquema = configuracion.buscar_esquema(Path(principal))
    if esquema is None:
        return None
    try:
        import yaml
        s = (yaml.safe_load(esquema.read_text(encoding="utf-8")) or {}).get(seccion)
    except Exception:
        return None
    if not isinstance(s, dict) or not s.get(forma["requerida"]):
        return None
    proyecto = _proyecto(Path(principal), str(s.get("marcador") or "")) if s.get("marcador") else Path(principal).resolve().parent
    if proyecto is None:
        return None
    return {"nombre": str(s.get("nombre") or forma["nombre"]), "proyecto": str(proyecto),
            **{k: _resolver(s.get(k) or [], esquema, proyecto) for k in forma["ordenes"]}}


ESTADOS_MATRIZ = ("ok", "aviso", "falla")


def resultado_matriz(dato, proyecto: str | Path) -> dict:
    """Lo que devolvió `leer` de `matriz:` (§13), listo para la ventana: cada huérfano y cada sección con su `ruta`
    absoluta, las columnas y el resumen. Nunca lanza: lo mal formado vuelve como {error}."""
    vacio = {"error": "", "existe": False, "archivo": "", "ruta": "", "filas": [], "huerfanos": [], "columnas": [],
             "pregunta": {}, "porque": "", "fuente": "", "cuadro": {}, "fallas": 0, "avisos": 0, "no_aplica": ""}
    if not isinstance(dato, dict):
        return {**vacio, "error": "la orden no devolvió la matriz"}
    if dato.get("error") and not dato.get("filas"):
        return {**vacio, "error": str(dato["error"])}
    base = Path(proyecto)
    absoluta = lambda a: str(a if Path(a).is_absolute() else base / a) if a else ""
    filas = []
    for f in dato.get("filas") or []:
        if not isinstance(f, dict):
            continue
        secciones = [{**s, "ruta": absoluta(str(s.get("archivo") or ""))} for s in f.get("secciones") or [] if isinstance(s, dict)]
        indicadores = [i for i in f.get("indicadores") or [] if isinstance(i, dict)]
        problemas = [x for x in f.get("problemas") or [] if isinstance(x, dict) and x.get("estado") in ESTADOS_MATRIZ]
        estado = "falla" if any(x["estado"] == "falla" for x in problemas) else "aviso" if problemas else "ok"
        filas.append({**{k: str(f.get(k) or "") for k in ("id", "nivel", "problema", "objetivo", "hipotesis", "prueba",
                                                           "refutaria", "supuesto", "tipo")},
                      "variables": [str(v) for v in f.get("variables") or []], "indicadores": indicadores,
                      "secciones": secciones, "problemas": problemas, "estado": estado, "linea": int(f.get("linea") or 0)})
    huerfanos = [{**h, "ruta": absoluta(str(h.get("archivo") or "")), "linea": int(h.get("linea") or 0)}
                 for h in dato.get("huerfanos") or [] if isinstance(h, dict) and h.get("estado") in ESTADOS_MATRIZ]
    archivo = str(dato.get("archivo") or "")
    return {**vacio, "error": str(dato.get("error") or ""), "existe": bool(dato.get("existe")), "archivo": archivo,
            "ruta": absoluta(archivo), "filas": filas, "huerfanos": huerfanos,
            "columnas": [c for c in dato.get("columnas") or [] if isinstance(c, dict)],
            "pregunta": dato.get("pregunta") if isinstance(dato.get("pregunta"), dict) else {},
            "porque": str(dato.get("porque") or ""), "fuente": str(dato.get("fuente") or ""),
            "cuadro": dato.get("cuadro") if isinstance(dato.get("cuadro"), dict) else {},
            "no_aplica": str(dato.get("no_aplica") or ""),
            "fallas": sum(h["estado"] == "falla" for h in huerfanos), "avisos": sum(h["estado"] == "aviso" for h in huerfanos)}


def resultado_revisor(dato) -> dict:
    """Lo que devolvió `revisar` de `revisor:` (§14), con cada hallazgo junto a su regla (nombre, porqué y fuente) y
    ordenado por línea. Nunca lanza."""
    vacio = {"error": "", "perfil": {}, "reglas": [], "hallazgos": [], "estilo": 0, "latex": 0}
    if not isinstance(dato, dict):
        return {**vacio, "error": "la orden no devolvió la revisión"}
    if dato.get("error"):
        return {**vacio, "error": str(dato["error"])}
    reglas = {str(r.get("clave")): r for r in dato.get("reglas") or [] if isinstance(r, dict) and r.get("clave")}
    hallazgos = []
    for h in dato.get("hallazgos") or []:
        if not isinstance(h, dict):
            continue
        r = reglas.get(str(h.get("regla") or ""), {})
        hallazgos.append({"linea": int(h.get("linea") or 0), "columna": int(h.get("columna") or 0), "largo": int(h.get("largo") or 0),
                          "regla": str(h.get("regla") or ""), "clase": str(h.get("clase") or r.get("clase") or "estilo"),
                          "texto": str(h.get("texto") or ""), "sugerencia": str(h.get("sugerencia") or ""),
                          "nombre": str(r.get("nombre") or h.get("regla") or ""), "porque": str(r.get("porque") or ""),
                          "fuente": str(r.get("fuente") or ""), "archivo": str(h.get("archivo") or "")})
    hallazgos.sort(key=lambda h: (h["archivo"], h["linea"], h["columna"]))
    return {**vacio, "perfil": dato.get("perfil") if isinstance(dato.get("perfil"), dict) else {},
            "reglas": list(reglas.values()), "hallazgos": hallazgos,
            "estilo": sum(h["clase"] == "estilo" for h in hallazgos), "latex": sum(h["clase"] == "latex" for h in hallazgos)}


def resultado_rubrica(dato) -> dict:
    """Lo que devolvió `rubrica` de `entrega:` (§12): la rúbrica en el formato común (criterios con sus niveles, del mejor
    al peor) con lo puntuado en cada criterio, la nota y de dónde viene. Nunca lanza."""
    vacio = {"error": "", "titulo": "", "fuente": "", "origen": "", "porque": "", "criterios": [], "nota": None,
             "vetos": [], "faltan": 0, "cambio": False, "hay": False}
    if not isinstance(dato, dict):
        return {**vacio, "error": "la orden no devolvió la rúbrica"}
    if dato.get("error") or dato.get("problemas"):
        return {**vacio, "error": str(dato.get("error") or "; ".join(map(str, dato.get("problemas") or [])))}
    r = dato.get("rubrica") if isinstance(dato.get("rubrica"), dict) else None
    if r is None:
        return {**vacio, "porque": str(dato.get("porque") or ""), "fuente": str(dato.get("fuente") or "")}
    puntajes = dato.get("puntajes") if isinstance(dato.get("puntajes"), dict) else {}
    criterios = []
    for c in r.get("criterios") or []:
        if not isinstance(c, dict):
            continue
        p = puntajes.get(c.get("clave")) or {}
        niveles = [{"puntaje": n.get("puntaje"), "texto": f"{n.get('puntaje'):g}" if isinstance(n.get("puntaje"), (int, float)) else str(n.get("puntaje")),
                    "nombre": str(n.get("nombre") or ""), "descriptor": str(n.get("descriptor") or "")}
                   for n in c.get("niveles") or [] if isinstance(n, dict)]
        elegido = p.get("puntaje")
        criterios.append({"clave": str(c.get("clave")), "nombre": str(c.get("nombre") or ""), "peso": c.get("peso"),
                          "descripcion": str(c.get("descripcion") or ""), "niveles": niveles,
                          "puntaje": "" if elegido is None else (f"{elegido:g}" if isinstance(elegido, (int, float)) else str(elegido)),
                          "justificacion": str(p.get("justificacion") or ""), "fecha": str(p.get("fecha") or "")})
    nota = dato.get("nota") if isinstance(dato.get("nota"), dict) else {}
    return {**vacio, "hay": True, "titulo": str(r.get("titulo") or ""), "fuente": str(r.get("fuente") or ""),
            "porque": str(dato.get("porque") or ""), "origen": str(dato.get("origen") or ""), "criterios": criterios,
            "nota": nota.get("nota"), "vetos": list(nota.get("vetos") or []), "faltan": sum(1 for c in criterios if not c["puntaje"]),
            "cambio": bool(dato.get("cambio"))}
