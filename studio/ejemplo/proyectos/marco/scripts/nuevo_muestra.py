#!/usr/bin/env python3
"""scripts/nuevo_muestra.py — «Nuevo documento» del marco de muestra (§11 del contrato): qué se puede crear y crearlo.

tipos: el JSON de los tipos (nombre, una línea, variantes y campos del formulario). crear '<json>' [--aplicar]
[--raiz DIR]: sin --aplicar crea el documento en un temporal y devuelve {destino, carpeta, archivos, principal,
escrito: false} (la carpeta del marco no se toca); con --aplicar lo crea en <marco>/<carpeta del tipo>/AAAA-MM-DD-<slug>
(o bajo --raiz). Lo usan las pruebas y las capturas; ningún dato real.
"""
import json
import re
import shutil
import sys
import tempfile
import unicodedata
from datetime import date
from pathlib import Path

MARCO = Path(__file__).resolve().parents[1]
AUTORES = {"clave": "autores", "rotulo": "Autores (uno por línea)", "obligatorio": True, "tipo": "lineas"}
TIPOS = [
    {"clave": "memoria", "nombre": "Memoria", "descripcion": "Lo hecho en el periodo, con sus cifras.", "carpeta": "informes",
     "variante": {"rotulo": "Variante", "omision": "anual",
                  "opciones": [{"clave": "anual", "nombre": "Anual", "descripcion": "El año completo, con su resumen."},
                               {"clave": "semestral", "nombre": "Semestral", "descripcion": "Medio año, en pocas páginas."}]},
     "campos": [{"clave": "titulo", "rotulo": "Título", "obligatorio": True, "tipo": "texto"},
                {"clave": "subtitulo", "rotulo": "Subtítulo", "obligatorio": False, "tipo": "texto"}, AUTORES,
                {"clave": "organizacion", "rotulo": "Organización", "obligatorio": False, "tipo": "opcion", "omision": "muestra",
                 "opciones": [{"clave": "muestra", "nombre": "Organización de muestra"}, {"clave": "otra", "nombre": "Otra organización"}]},
                {"clave": "profundidad", "rotulo": "Profundidad", "obligatorio": False, "tipo": "opcion", "omision": "",
                 "opciones": [{"clave": "breve", "nombre": "Breve"}, {"clave": "completo", "nombre": "Completo"}],
                 "segun_variante": {"anual": ["breve", "completo"], "semestral": []}}]},
    {"clave": "nota", "nombre": "Nota técnica", "descripcion": "Un asunto en dos o tres páginas.", "carpeta": "notas",
     "variante": {"rotulo": "Variante", "omision": "simple",
                  "opciones": [{"clave": "simple", "nombre": "Simple", "descripcion": "Antecedentes, análisis y recomendación."}]},
     "campos": [{"clave": "titulo", "rotulo": "Título", "obligatorio": True, "tipo": "texto"}, AUTORES]},
    {"clave": "acta", "nombre": "Acta", "descripcion": "Lo acordado en una reunión.", "carpeta": "actas",
     "variante": {"rotulo": "Variante", "omision": "ordinaria",
                  "opciones": [{"clave": "ordinaria", "nombre": "Ordinaria", "descripcion": "Con su agenda y sus acuerdos."},
                               {"clave": "extraordinaria", "nombre": "Extraordinaria", "descripcion": "Un solo punto."}]},
     "campos": [{"clave": "titulo", "rotulo": "Título", "obligatorio": True, "tipo": "texto"}, AUTORES]},
]


def _json(d) -> int:
    print(json.dumps(d, ensure_ascii=False))
    return 0


def _slug(titulo: str) -> str:
    s = unicodedata.normalize("NFKD", re.sub(r"[^\w]+", " ", titulo)).encode("ascii", "ignore").decode().lower()
    return "-".join([p for p in re.split(r"[^a-z0-9]+", s) if p and p not in ("de", "la", "el", "y", "en")][:6])


def _escribir(carpeta: Path, tipo: dict, datos: dict) -> None:
    autores = [a.strip() for a in (datos.get("autores") if isinstance(datos.get("autores"), list)
                                   else str(datos.get("autores") or "").splitlines()) if a.strip()]
    (carpeta / "capitulos").mkdir(parents=True)
    (carpeta / "informe.tex").write_text(
        "\\documentclass{memoria}\n"
        f"% {tipo['nombre']} · {datos.get('variante') or tipo['variante']['omision']}\n"
        f"\\title{{{datos.get('titulo', '')}}}\n\\author{{{' \\and '.join(autores)}}}\n"
        "\\begin{document}\n\\maketitle\n\\input{capitulos/01-introduccion}\n\\end{document}\n", encoding="utf-8")
    (carpeta / "capitulos" / "01-introduccion.tex").write_text("\\section{Introducción}\nPendiente de redactar.\n", encoding="utf-8")
    (carpeta / "README.md").write_text(f"# {datos.get('titulo', '')}\n", encoding="utf-8")


def crear(datos: dict, aplicar: bool, raiz: Path) -> dict:
    tipo = next((t for t in TIPOS if t["clave"] == datos.get("tipo")), None)
    if tipo is None:
        return {"error": "Elige el tipo de documento."}
    for c in tipo["campos"]:
        if c["obligatorio"] and not str(datos.get(c["clave"]) or "").strip():
            return {"error": f"Falta «{c['rotulo'].split(' (')[0]}»."}
    slug = _slug(str(datos.get("titulo") or ""))
    if len(slug) < 3:
        return {"error": "El título necesita al menos una palabra de tres letras para nombrar la carpeta."}
    carpeta = f"{tipo['carpeta']}/{date.today().isoformat()}-{slug}"
    destino = raiz / carpeta
    if destino.exists():
        return {"error": f"Ya existe {carpeta}: cambia el título.", "destino": str(destino)}
    temporal = None if aplicar else Path(tempfile.mkdtemp(prefix="nuevo-muestra-"))
    try:
        hecha = (temporal or raiz) / carpeta
        _escribir(hecha, tipo, datos)
        archivos = sorted(str(p.relative_to(hecha)) for p in hecha.rglob("*") if p.is_file())
    finally:
        if temporal is not None:
            shutil.rmtree(temporal, ignore_errors=True)
    return {"destino": str(destino), "carpeta": carpeta, "slug": slug, "tipo": tipo["clave"],
            "principal": str(destino / "informe.tex"), "archivos": archivos, "avisos": [], "escrito": aplicar}


def main(argv: list[str]) -> int:
    if argv[:1] == ["tipos"]:
        return _json({"marco": "muestra", "tipos": TIPOS})
    if argv[:1] != ["crear"] or len(argv) < 2:
        print("uso: nuevo_muestra.py tipos | crear '<json>' [--aplicar] [--raiz DIR]", file=sys.stderr)
        return 2
    raiz = Path(argv[argv.index("--raiz") + 1]) if "--raiz" in argv else MARCO
    try:
        datos = json.loads(argv[1])
    except ValueError:
        return _json({"error": "Los datos no son un JSON."})
    return _json(crear(datos, "--aplicar" in argv, raiz))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
