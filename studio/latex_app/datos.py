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
Las demás secciones del contrato se leen igual: `biblioteca:` (§9), `ayuda:` (§10), `nuevo:` (§11) y `entrega:` (§12,
  «Antes de entregar»: `declaracion_entrega`, `resultado_entrega`, `veredicto` y `uso_de_ia`; decisiones §1.21).
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
            **{k: _resolver(a.get(k) or [], esquema, proyecto) for k in ("prompt", "pegar")}}


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
# un uso de la IA.
ORDENES_ENTREGA = ("revisar", "marcar", "registrar_ia")
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
            **veredicto(controles)}


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
