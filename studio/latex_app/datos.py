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
