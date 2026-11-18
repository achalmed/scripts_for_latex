#!/usr/bin/env python3
"""scripts/flujo_muestra.py — las secciones §12 (rúbrica), §10 (revisar el prompt), §13 (matriz), §14 (revisor) y §15 (plantillas) del marco de muestra: lo que leen los diálogos de LaTeX Studio.

Órdenes (todas imprimen JSON; las que escriben solo lo hacen con --aplicar, dentro de <proyecto>):
  matriz-leer <proyecto> · matriz-cuadro <proyecto> · matriz-nueva <proyecto> · matriz-guia · matriz-pregunta <proyecto> <json>
  revisor <archivo> <ruta> · plantillas · componer <json> · rubrica <proyecto> · autoevaluar <proyecto> <json>
  revisar-prompt <archivo>
Comprobaciones de juguete, sin datos reales: el marco real (escritura) las sirve con scripts/matriz.py, revisor.py,
plantillas.py, sensibles.py y antes_de_entregar.py. Lo usan las pruebas y las capturas.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

import yaml


def _json(d):
    print(json.dumps(d, ensure_ascii=False))
    sys.exit(0)


def _yaml(p: Path) -> dict:
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.is_file() else {}


args = [a for a in sys.argv[1:] if a != "--aplicar"]
aplicar = "--aplicar" in sys.argv
orden = args[0] if args else ""

# ------------------------------------------------------------------ §13 la matriz
FUENTE = "Hernández Sampieri et al. (2014, Calibre 732)"
PASOS = [
    {"clave": "tema", "titulo": "El tema", "pregunta": "¿Sobre qué quieres investigar?", "ayuda": "Un área, todavía no una pregunta.",
     "ejemplos": ["El empleo en las ciudades de muestra"], "campos": [{"clave": "tema", "rotulo": "Tema", "tipo": "texto", "obligatorio": True}],
     "porque": "Del tema a la pregunta.", "fuente": "Booth et al. (2016)"},
    {"clave": "hecho", "titulo": "El rompecabezas", "pregunta": "¿Qué hecho no cuadra?", "ayuda": "Un hecho estilizado o una contradicción.",
     "ejemplos": ["El empleo creció pero los ingresos no"], "campos": [{"clave": "hecho", "rotulo": "Hecho", "tipo": "lineas", "obligatorio": True}],
     "porque": "La pregunta nace de un rompecabezas.", "fuente": "Varian (1997)"},
    {"clave": "pregunta", "titulo": "La pregunta", "pregunta": "¿Qué preguntas exactamente?", "ayuda": "Población, periodo y comparación.",
     "ejemplos": ["¿Cuánto del empleo de 2019 a 2024 se explica por el sector?"],
     "campos": [{"clave": "poblacion", "rotulo": "Población", "tipo": "texto", "obligatorio": True},
                {"clave": "periodo", "rotulo": "Periodo", "tipo": "texto", "obligatorio": True},
                {"clave": "comparacion", "rotulo": "Comparación", "tipo": "texto", "obligatorio": True},
                {"clave": "texto", "rotulo": "Pregunta", "tipo": "lineas", "obligatorio": True}],
     "porque": "Una buena pregunta delimita.", "fuente": "King et al. (1994)"},
    {"clave": "evidencia", "titulo": "La evidencia", "pregunta": "¿Qué evidencia la contestaría?", "ayuda": "Datos e indicador.",
     "ejemplos": ["La encuesta de muestra, 2019 y 2024"], "campos": [{"clave": "evidencia", "rotulo": "Evidencia", "tipo": "lineas", "obligatorio": True}],
     "porque": "La pregunta anticipa su evidencia.", "fuente": "Booth et al. (2016)"},
]


def _matriz(proyecto: Path) -> dict:
    archivo = proyecto / "matriz.yml"
    d = _yaml(archivo)
    filas, huerfanos = [], []
    for n, f in enumerate(d.get("filas") or [], 1):
        problemas = []
        if not f.get("indicadores"):
            problemas.append({"estado": "falla", "texto": f"{f['id']}: la hipótesis no tiene indicador", "clase": "huerfano"})
        if not f.get("refutaria"):
            problemas.append({"estado": "aviso", "texto": f"{f['id']}: falta la evidencia que refutaría la hipótesis", "clase": "refutacion"})
        secciones = [{"ref": s, "existe": s == "sec:informe", "archivo": "informe.tex" if s == "sec:informe" else "", "linea": 6 if s == "sec:informe" else 0}
                     for s in f.get("secciones") or []]
        filas.append({**f, "nivel": f.get("nivel", "especifico"), "linea": 2 + 9 * (n - 1), "secciones": secciones,
                      "indicadores": [{"ref": i, "existe": True, "nombre": "Tasa de muestra"} for i in f.get("indicadores") or []],
                      "problemas": problemas})
        huerfanos += [{**p, "fila": f["id"], "archivo": "matriz.yml", "linea": 2 + 9 * (n - 1)} for p in problemas]
    return {"archivo": "matriz.yml", "existe": archivo.is_file(), "porque": "Cada hipótesis apunta a su sección y a su indicador.",
            "fuente": FUENTE, "pregunta": d.get("pregunta") or {}, "filas": filas, "huerfanos": huerfanos,
            "columnas": [{"clave": "refutaria", "nombre": "Evidencia que la refutaría", "porque": "Una hipótesis irrefutable no informa.", "fuente": "Popper (2007)"},
                         {"clave": "supuesto", "nombre": "Supuesto que se cuestiona", "porque": "Problematizar da mejores preguntas.", "fuente": "Alvesson y Sandberg (2011)"}],
            "cuadro": {"archivo": "tables/matriz.tex", "existe": (proyecto / "tables" / "matriz.tex").is_file(),
                       "al_dia": (proyecto / "tables" / "matriz.tex").is_file()}}


MUESTRA_MATRIZ = {"pregunta": {"texto": "¿Cuánto del empleo de muestra entre 2019 y 2024 se explica por el sector?"},
                  "filas": [{"id": "general", "nivel": "general", "problema": "¿Cuánto del empleo de muestra entre 2019 y 2024 se explica por el sector?",
                             "objetivo": "Medir la parte del sector.", "hipotesis": "El sector explica la mayor parte.",
                             "indicadores": ["indicadores-muestra@v2/tasa"], "secciones": ["sec:informe"],
                             "refutaria": "Una parte del sector menor que la del ingreso.", "supuesto": "Que el empleo crece igual en todos los sectores."},
                            {"id": "he1", "problema": "¿Influye la región?", "objetivo": "Comparar regiones.", "hipotesis": "La región importa.",
                             "indicadores": [], "secciones": ["sec:inexistente"]}]}

if orden == "matriz-leer":
    _json(_matriz(Path(args[1])))
if orden == "matriz-nueva":
    destino = Path(args[1]) / "matriz.yml"
    if destino.is_file():
        _json({"error": "matriz.yml ya existe."})
    if aplicar:
        destino.write_text(yaml.safe_dump(MUESTRA_MATRIZ, allow_unicode=True, sort_keys=False), encoding="utf-8")
    _json({"archivo": "matriz.yml", "escrito": aplicar})
if orden == "matriz-cuadro":
    destino = Path(args[1]) / "tables" / "matriz.tex"
    if aplicar:
        destino.parent.mkdir(exist_ok=True)
        destino.write_text("% GENERADO por flujo_muestra.py\n", encoding="utf-8")
    _json({"archivo": "tables/matriz.tex", "cambia": True, "escrito": aplicar})
if orden == "matriz-guia":
    _json({"titulo": "De un tema a una pregunta", "pasos": PASOS, "porque": "Cuatro pasos.", "fuente": "Booth et al. (2016)"})
if orden == "matriz-pregunta":
    datos = json.loads(args[2])
    avisos = [{"paso": p["clave"], "estado": "falla", "texto": f"Falta «{c['rotulo']}»."} for p in PASOS for c in p["campos"]
              if c.get("obligatorio") and not str(datos.get(c["clave"]) or "").strip()]
    if datos.get("texto") and "?" not in datos["texto"]:
        avisos.append({"paso": "pregunta", "estado": "aviso", "texto": "La pregunta no termina en signo de pregunta."})
    ok = not any(a["estado"] == "falla" for a in avisos)
    if ok and aplicar:
        archivo = Path(args[1]) / "matriz.yml"
        d = _yaml(archivo)
        d["pregunta"] = datos
        archivo.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    _json({"ok": ok, "avisos": avisos, "archivo": "matriz.yml", "escrito": ok and aplicar})

# ------------------------------------------------------------------ §14 el revisor
REGLAS = [{"clave": "oracion_larga", "clase": "estilo", "nombre": "Oración larga", "porque": "Una oración larga obliga a releer.",
           "fuente": "Williams y Bizup (2017)"},
          {"clave": "pasiva", "clase": "estilo", "nombre": "Voz pasiva", "porque": "El actor como sujeto se lee mejor.", "fuente": "Williams y Bizup (2017)"},
          {"clave": "obsoleto", "clase": "latex", "nombre": "Orden obsoleta", "porque": "Las órdenes de LaTeX 2.09 no respetan la fuente.",
           "fuente": "Trettin (2016)"}]
if orden == "revisor":
    texto = Path(args[1]).read_text(encoding="utf-8")
    hallazgos = []
    for n, l in enumerate(texto.split("\n"), 1):
        if l.lstrip().startswith("%"):
            continue
        for m in re.finditer(r"\\(bf|it|rm)\b", l):
            hallazgos.append({"linea": n, "columna": m.start() + 1, "largo": len(m.group(0)), "regla": "obsoleto", "clase": "latex",
                              "texto": m.group(0), "sugerencia": "Use \\textbf{…} o \\emph{…}."})
        for m in re.finditer(r"\b(fue|fueron)\s+\w+(ado|ido)s?\b", l):
            hallazgos.append({"linea": n, "columna": m.start() + 1, "largo": len(m.group(0)), "regla": "pasiva", "clase": "estilo",
                              "texto": m.group(0), "sugerencia": "Considere poner al actor como sujeto."})
        if len(l.split()) > 25:
            hallazgos.append({"linea": n, "columna": 1, "largo": len(l), "regla": "oracion_larga", "clase": "estilo",
                              "texto": " ".join(l.split()[:6]) + "…", "sugerencia": "Considere partirla en dos."})
    _json({"perfil": {"clave": "academico", "nombre": "Académico"}, "reglas": REGLAS, "hallazgos": hallazgos,
           "resumen": {"estilo": sum(h["clase"] == "estilo" for h in hallazgos), "latex": sum(h["clase"] == "latex" for h in hallazgos)}})
if orden == "reglas":
    _json({"reglas": REGLAS})

# ------------------------------------------------------------------ §15 las plantillas
PLANTILLAS = [
    {"clave": "figura", "nombre": "Figura con nota y fuente", "descripcion": "Una figura con su texto alternativo, nota y fuente",
     "porque": "Lo que más se repite, sin escribirlo de memoria.", "fuente": "Knauff y Nejasmic (2014)",
     "campos": [{"clave": "archivo", "rotulo": "Archivo", "tipo": "texto", "obligatorio": True, "omision": "figures/serie_anual.pdf"},
                {"clave": "titulo", "rotulo": "Título", "tipo": "texto", "obligatorio": True},
                {"clave": "alt", "rotulo": "Texto alternativo", "tipo": "lineas", "obligatorio": True, "ayuda": "Qué muestra la figura, para quien no la ve"},
                {"clave": "fuente", "rotulo": "Fuente", "tipo": "texto", "obligatorio": True}]},
    {"clave": "cuadro", "nombre": "Cuadro con booktabs", "descripcion": "Un cuadro de tres líneas con su nota",
     "porque": "Las líneas verticales estorban la lectura del cuadro.", "fuente": "Fear (2020)",
     "campos": [{"clave": "titulo", "rotulo": "Título", "tipo": "texto", "obligatorio": True},
                {"clave": "columnas", "rotulo": "Columnas", "tipo": "opcion", "opciones": [{"clave": "2", "nombre": "Dos"}, {"clave": "3", "nombre": "Tres"}]}]},
]
if orden == "plantillas":
    _json({"plantillas": PLANTILLAS})
if orden == "componer":
    d = json.loads(args[1])
    v = d.get("valores") or {}
    p = next((x for x in PLANTILLAS if x["clave"] == d.get("plantilla")), None)
    if p is None:
        _json({"error": "plantilla desconocida"})
    faltan = [c["rotulo"] for c in p["campos"] if c.get("obligatorio") and not str(v.get(c["clave"]) or "").strip()]
    if p["clave"] == "figura":
        texto = ("\\begin{figure}[htbp]\n  \\centering\n  \\caption{" + v.get("titulo", "") + "}\n"
                 "  \\includegraphics[width=\\linewidth, alt={" + v.get("alt", "") + "}]{" + v.get("archivo", "") + "}\n"
                 "  \\par\\small Fuente: " + v.get("fuente", "") + "\n\\end{figure}\n")
    else:
        n = int(v.get("columnas") or 2)
        texto = ("\\begin{table}[htbp]\n  \\caption{" + v.get("titulo", "") + "}\n  \\begin{tabular}{l" + "r" * (n - 1) + "}\n"
                 "    \\toprule\n    " + " & ".join(["Columna"] * n) + " \\\\\n    \\midrule\n    " + " & ".join(["…"] * n) + " \\\\\n"
                 "    \\bottomrule\n  \\end{tabular}\n\\end{table}\n")
    _json({"insertar": texto, "avisos": [f"Falta «{f}»." for f in faltan]})

# ------------------------------------------------------------------ §12 la rúbrica
RUBRICA = {"titulo": "Rúbrica de muestra", "fuente": "Jonsson y Svingby (2007)",
           "criterios": [{"clave": "claridad", "nombre": "Claridad", "peso": 60,
                          "niveles": [{"puntaje": 3, "nombre": "Logrado", "descriptor": "Se entiende sin releer."},
                                      {"puntaje": 1, "nombre": "Inicial", "descriptor": "Hay que releer cada párrafo."}]},
                         {"clave": "fuentes", "nombre": "Fuentes", "peso": 40,
                          "niveles": [{"puntaje": 2, "nombre": "Logrado", "descriptor": "Cada afirmación con su fuente."},
                                      {"puntaje": 0, "nombre": "Inicial", "descriptor": "Sin fuentes."}]}]}
if orden == "rubrica":
    reg = _yaml(Path(args[1]) / "autoevaluacion.yml")
    puntajes = reg.get("criterios") or {}
    total = sum(c["peso"] for c in RUBRICA["criterios"])
    nota = None
    if len(puntajes) == len(RUBRICA["criterios"]):
        nota = round(100 * sum(puntajes[c["clave"]]["puntaje"] / max(n["puntaje"] for n in c["niveles"]) * c["peso"]
                               for c in RUBRICA["criterios"]) / total, 1)
    _json({"rubrica": RUBRICA, "origen": "tipo", "puntajes": puntajes, "nota": {"nota": nota, "vetos": [], "faltan": []},
           "cambio": False, "problemas": [], "porque": "Puntuar antes de entregar mejora el trabajo.", "fuente": "Andrade (2019)"})
if orden == "autoevaluar":
    proyecto, d = Path(args[1]), json.loads(args[2])
    c = next((x for x in RUBRICA["criterios"] if x["clave"] == d.get("clave")), None)
    if c is None:
        _json({"error": "criterio desconocido"})
    if len(str(d.get("justificacion") or "").split()) < 3:
        _json({"error": f"{c['nombre']}: justifique el puntaje."})
    reg = _yaml(proyecto / "autoevaluacion.yml")
    reg.setdefault("criterios", {})[c["clave"]] = {"puntaje": float(d["puntaje"]), "justificacion": d["justificacion"],
                                                    "fecha": date.today().isoformat()}
    if aplicar:
        (proyecto / "autoevaluacion.yml").write_text(yaml.safe_dump(reg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    _json({"registro": "autoevaluacion.yml", "puntajes": reg["criterios"], "escrito": aplicar})

# ------------------------------------------------------------------ §12 el lector frío
if orden == "lector-frio":
    proyecto = Path(args[1])
    pdf = proyecto / "informe.pdf"
    if not pdf.is_file():
        _json({"error": "Compile el informe antes de preparar la versión sin nombres."})
    destino = proyecto / ".build" / "lector-frio" / "informe-lector-frio.pdf"
    if aplicar:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(pdf.read_bytes())
    _json({"pdf": str(destino) if aplicar else "", "quitado": [{"archivo": "informe.tex", "linea": 4, "campo": "responsable"}],
           "pendientes": [], "escrito": aplicar})

# ------------------------------------------------------------------ §10 revisar el prompt antes de copiarlo
if orden == "revisar-prompt":
    texto = Path(args[1]).read_text(encoding="utf-8")
    hallazgos = [{"tipo": "documento de identidad", "nivel": "alto", "linea": n, "texto": m.group(0)}
                 for n, l in enumerate(texto.split("\n"), 1) for m in re.finditer(r"\bDNI\s*\d{8}\b", l)]
    _json({"sensible": bool(hallazgos), "nivel": "alto" if hallazgos else "ninguno", "hallazgos": hallazgos, "total": len(hallazgos),
           "porque": "Los datos sensibles no salen a un chat externo sin que lo decidas.", "fuente": "Comisión Europea (2025)"})
_json({"error": f"orden desconocida: {orden}"})
