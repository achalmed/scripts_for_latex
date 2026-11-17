#!/usr/bin/env python3
"""scripts/datos_muestra.py — la orden de datos del marco de muestra (§8 del contrato): lo que lee la pestaña «Datos».

recursos <proyecto>: el JSON de figuras, tablas y cifras que declara su datos.yml (sin calcular nada); actualizar
<proyecto>: lleva `usada` a `ultima` en datos.yml. Y la biblioteca (§9): buscar <texto>, fichas <proyecto> y citar
<proyecto> <id> [--aplicar] (añade el libro a `fuentes:` de datos.yml). Lo usan las pruebas y las capturas; ningún
dato real.
"""
import json
import sys
from pathlib import Path

import yaml

LIBROS = [{"calibre_id": 1, "clave": "quispe2021ciudades", "titulo": "Economía de las ciudades pequeñas", "autores": ["Rosa Quispe"],
           "anio": "2021", "pdf": "", "portada": "", "fichas": 1},
          {"calibre_id": 2, "clave": "arango2015estadistica", "titulo": "Estadística para economistas", "autores": ["Tomás Arango"],
           "anio": "2015", "pdf": "", "portada": "", "fichas": 0}]
if sys.argv[1] == "buscar":
    texto = (sys.argv[2] if len(sys.argv) > 2 else "").lower()
    print(json.dumps([dict(l, insertar=f"\\parencite{{{l['clave']}}}") for l in LIBROS
                      if texto in (l["titulo"] + " " + l["clave"] + " " + " ".join(l["autores"])).lower()], ensure_ascii=False))
    sys.exit(0)
orden, proyecto = sys.argv[1], Path(sys.argv[2])
ficha = proyecto / "datos.yml"
d = yaml.safe_load(ficha.read_text(encoding="utf-8")) or {}
if orden == "fichas":
    print(json.dumps([{"archivo": str(proyecto / "fichas" / "quispe2021ciudades-p012-textual-escala.md"), "nombre": "quispe2021ciudades-p012-textual-escala",
                       "tipo": "textual", "clave": "quispe2021ciudades", "calibre_id": 1, "pagina": "12", "categoria": "dato",
                       "verificacion": "verificada_script", "texto": "Las ciudades pequeñas crecen cuando se integran a su región.",
                       "insertar": "“Las ciudades pequeñas crecen cuando se integran a su región.” \\parencite[p.~12]{quispe2021ciudades}"}], ensure_ascii=False))
    sys.exit(0)
if orden == "citar":
    libro = next(l for l in LIBROS if l["calibre_id"] == int(sys.argv[3]))
    nueva = libro["clave"] not in (d.get("fuentes") or [])
    if nueva and "--aplicar" in sys.argv:
        d["fuentes"] = (d.get("fuentes") or []) + [libro["clave"]]
        ficha.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(json.dumps({"clave": libro["clave"], "nueva": nueva and "--aplicar" not in sys.argv, "escrito": "--aplicar" in sys.argv,
                      "insertar": f"\\parencite{{{libro['clave']}}}"}, ensure_ascii=False))
    sys.exit(0)
if orden == "actualizar":
    d["usada"] = d.get("ultima", d.get("usada"))
    ficha.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"[ok] {d['paquete']}@{d['usada']}")
    sys.exit(0)
print(json.dumps({
    "paquetes": [{"estudio": d["paquete"], "usada": d["usada"], "ultima": d["ultima"], "nueva": d["usada"] != d["ultima"]}],
    "figuras": [{"id": f, "titulo": t, "insertar": f"\\includegraphics{{figures/{f}.pdf}}", "existe": False} for f, t in d.get("figuras", {}).items()],
    "tablas": [{"id": f, "titulo": t, "insertar": f"\\input{{tables/{f}.tex}}", "existe": False} for f, t in d.get("tablas", {}).items()],
    "cifras": [{"macro": m, "valor": v} for m, v in d.get("cifras", {}).items()],
}, ensure_ascii=False))
