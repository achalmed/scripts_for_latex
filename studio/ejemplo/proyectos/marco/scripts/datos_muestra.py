#!/usr/bin/env python3
"""scripts/datos_muestra.py — la orden de datos del marco de muestra (§8 del contrato): lo que lee la pestaña «Datos».

recursos <proyecto>: el JSON de figuras, tablas y cifras que declara su datos.yml (sin calcular nada); actualizar
<proyecto>: lleva `usada` a `ultima` en datos.yml. Lo usan las pruebas y las capturas; ningún dato real.
"""
import json
import sys
from pathlib import Path

import yaml

orden, proyecto = sys.argv[1], Path(sys.argv[2])
ficha = proyecto / "datos.yml"
d = yaml.safe_load(ficha.read_text(encoding="utf-8")) or {}
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
