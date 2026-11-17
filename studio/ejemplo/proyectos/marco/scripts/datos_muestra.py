#!/usr/bin/env python3
"""scripts/datos_muestra.py — la orden de datos del marco de muestra (§8 del contrato): lo que lee la pestaña «Datos».

recursos <proyecto>: el JSON de figuras, tablas y cifras que declara su datos.yml (sin calcular nada); actualizar
<proyecto>: lleva `usada` a `ultima` en datos.yml. Y la biblioteca (§9): buscar <texto>, fichas <proyecto> y citar
<proyecto> <id> [--aplicar] (añade el libro a `fuentes:` de datos.yml); fichar (§9, decisiones §1.19): formulario,
ficha <proyecto> <archivo>, nueva_ficha <proyecto> <json> [--aplicar] y guardar_ficha <proyecto> <archivo> <huella>
<json> [--aplicar] (en <proyecto>/fichas/); y la ayuda de la IA (§10): prompt <proyecto> <archivo> y pegar <proyecto>
<archivo> <pegado> --tex <texto del editor> (la parte de la muestra es lo que va de la primera sección al
fin del documento). Lo usan las pruebas y las capturas; ningún dato real.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

FORMULARIO = {"tipos": [{"clave": "textual", "nombre": "Textual", "secciones": ["Cita exacta", "Análisis", "Observaciones"],
                         "literal": "Cita exacta", "pagina": True, "categoria": True, "libro": True},
                        {"clave": "parafrasis", "nombre": "Paráfrasis", "secciones": ["Paráfrasis", "Origen literal", "Control de fidelidad"],
                         "literal": "Origen literal", "pagina": True, "categoria": True, "libro": True},
                        {"clave": "fuente", "nombre": "Fuente", "secciones": ["Resumen", "Observaciones"], "literal": "",
                         "pagina": False, "categoria": False, "libro": True}],
              "categorias": ["Concepto/definición", "Idea principal", "Cita clave", "Dato/estadística", "Hallazgo", "Conclusión"]}


def _json(d):
    print(json.dumps(d, ensure_ascii=False))
    sys.exit(0)


def _huella(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def _leer_ficha(p: Path) -> dict:
    t = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", t, re.S)
    meta = yaml.safe_load(m.group(1)) if m else {}
    secs = dict(re.findall(r"^## (.+?)\n(.*?)(?=^## |\Z)", m.group(2) if m else t, re.S | re.M))
    tipo = str(meta.get("tipo", "ficha_textual")).replace("ficha_", "")
    nombres = next(x["secciones"] for x in FORMULARIO["tipos"] if x["clave"] == tipo)
    return {"archivo": p.name, "huella": _huella(t), "tipo": tipo, "calibre_id": meta.get("calibre_id", ""), "clave": meta.get("clave_bibtex", ""),
            "pagina": str(meta.get("pagina", "")), "categoria": meta.get("categoria", ""), "uso": meta.get("uso", ""), "error": "",
            "secciones": [{"titulo": s, "texto": secs.get(s, "").strip().strip("“”")} for s in nombres], "problemas": []}


def _escribir_ficha(proyecto: Path, campos: dict, nombre: str, previa: dict | None) -> dict:
    tipo = campos.get("tipo") or (previa or {}).get("tipo", "textual")
    clave = (previa or {}).get("clave") or next((l["clave"] for l in LIBROS if l["calibre_id"] == int(campos.get("calibre_id") or 0)), "")
    pagina = str(campos.get("pagina", (previa or {}).get("pagina", "")))
    if tipo != "fuente" and not pagina:
        return {"error": "Escriba la página («12») o el lugar («art. 5»): toda ficha lleva dónde está el pasaje."}
    if not nombre:
        tema = "-".join(re.sub(r"[^a-z0-9 ]", "", str(campos.get("tema") or "ficha").lower()).split()[:3]) or "ficha"
        nombre = f"{clave}-fuente.md" if tipo == "fuente" else f"{clave}-p{int(pagina):03d}-{tipo}-{tema}.md"
    secs = campos.get("secciones") or {}
    literal = next(x["literal"] for x in FORMULARIO["tipos"] if x["clave"] == tipo)
    cuerpo = "\n\n".join(f"## {s}\n" + (f"“{v}”" if s == literal and v else v) for s, v in secs.items())
    estado = "verificada_script" if "integran a su región" in secs.get(literal, "") else "observada" if secs.get(literal) else "pendiente"
    texto = (f"---\ntipo: ficha_{tipo}\ncalibre_id: {campos.get('calibre_id') or (previa or {}).get('calibre_id', '')}\nclave_bibtex: {clave}\n"
             f"pagina: {pagina}\ncategoria: {campos.get('categoria', '')}\nuso: {campos.get('uso', '')}\nverificacion:\n  estado: {estado}\n---\n\n{cuerpo}\n")
    r = {"archivo": nombre, "verificacion": {"estado": estado, "metodo": "muestra", "fecha": ""}, "problemas": [],
         "detalle": "p. 12 (muestra)" if estado == "verificada_script" else "", "nueva_fuente": clave == "arango2015estadistica",
         "renombra": False, "antes": "", "escrito": False}
    if "--aplicar" in sys.argv:
        (proyecto / "fichas").mkdir(exist_ok=True)
        (proyecto / "fichas" / nombre).write_text(texto, encoding="utf-8")
        r["escrito"] = True
    return r

LIBROS = [{"calibre_id": 1, "clave": "quispe2021ciudades", "titulo": "Economía de las ciudades pequeñas", "autores": ["Rosa Quispe"],
           "anio": "2021", "pdf": "", "portada": "", "fichas": 1},
          {"calibre_id": 2, "clave": "arango2015estadistica", "titulo": "Estadística para economistas", "autores": ["Tomás Arango"],
           "anio": "2015", "pdf": "", "portada": "", "fichas": 0}]
if sys.argv[1] == "formulario":
    _json(FORMULARIO)
if sys.argv[1] == "buscar":
    texto = (sys.argv[2] if len(sys.argv) > 2 else "").lower()
    print(json.dumps([dict(l, insertar=f"\\parencite{{{l['clave']}}}") for l in LIBROS
                      if texto in (l["titulo"] + " " + l["clave"] + " " + " ".join(l["autores"])).lower()], ensure_ascii=False))
    sys.exit(0)
orden, proyecto = sys.argv[1], Path(sys.argv[2])
ficha = proyecto / "datos.yml"
d = yaml.safe_load(ficha.read_text(encoding="utf-8")) or {}
if orden == "ficha":
    _json(_leer_ficha(proyecto / "fichas" / sys.argv[3]))
if orden == "nueva_ficha":
    _json(_escribir_ficha(proyecto, json.loads(sys.argv[3]), "", None))
if orden == "guardar_ficha":
    previa = _leer_ficha(proyecto / "fichas" / sys.argv[3])
    if previa["huella"] != sys.argv[4]:
        _json({"codigo": "ficha_cambiada", "error": "La ficha cambió fuera desde que la abrió.", "actual": previa})
    _json(_escribir_ficha(proyecto, json.loads(sys.argv[5]), sys.argv[3], previa))
if orden in ("prompt", "pegar"):
    tex = (proyecto / sys.argv[3]).read_text(encoding="utf-8")
    if "--tex" in sys.argv:
        tex = Path(sys.argv[sys.argv.index("--tex") + 1]).read_text(encoding="utf-8")
    m = re.search(r"\\section\{[^}]*\}\n(.*?)\\end\{document\}", tex, re.S)
    antes = m.group(1) if m else ""
    if orden == "prompt":
        _json({"prompt": "# Prompt de muestra · para «Informe anual»\n\n<entrada>\n" + antes + "</entrada>\n", "componente": "informe",
               "titulo": "Informe anual", "componentes": [{"clave": "informe", "titulo": "Informe anual"}],
               "fuente": {"ruta": "muestra.md", "titulo": "Redacción de una parte (muestra)", "version": "1.0.0"}, "aviso": "",
               "largo": False, "contexto": {"fichas": 1, "fichas_de_la_parte": False, "obras": 2}})
    pegado = Path(sys.argv[4]).read_text(encoding="utf-8")
    b = re.search(r"```(?:latex)?\n(.*?)```", pegado, re.S)
    cuerpo = (b.group(1) if b else pegado).strip()
    errores = ["Trae algo que no va: el componente ya es la sección."] if "\\section" in cuerpo else []
    _json({"ok": not errores, "errores": errores, "avisos": [], "componente": "informe", "antes": antes,
           "despues": cuerpo + "\n", "diff": f"- {antes.strip()}\n+ {cuerpo}\n"})
if orden == "fichas":
    propias = [_leer_ficha(f) for f in sorted((proyecto / "fichas").glob("*.md"))] if (proyecto / "fichas").is_dir() else []
    if propias:
        print(json.dumps([{"archivo": str(proyecto / "fichas" / f["archivo"]), "nombre": f["archivo"][:-3], "tipo": f["tipo"], "clave": f["clave"],
                           "calibre_id": f["calibre_id"], "pagina": f["pagina"], "categoria": f["categoria"], "verificacion": "",
                           "texto": f["secciones"][0]["texto"], "insertar": f"\\parencite[p.~{f['pagina']}]{{{f['clave']}}}"} for f in propias],
                         ensure_ascii=False))
        sys.exit(0)
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
