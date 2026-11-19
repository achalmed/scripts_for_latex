#!/usr/bin/env python3
"""scripts/entrega_muestra.py — «Antes de entregar» del marco de muestra (§12 del contrato): lo que lee el diálogo de LaTeX Studio.

revisar <proyecto>: los controles en JSON, con comprobaciones de juguete sobre informe.tex y datos.yml (un número escrito
a mano, el paquete en una versión vieja, un punto que se comprueba solo y dos manuales); marcar <proyecto> <id> <estado>
[<nota>] [--aplicar]: el estado de un punto manual en <proyecto>/entrega.yml; registrar_ia <proyecto> <json> [--aplicar]:
un uso en <proyecto>/ia/registro.yml y su declaración en ia/declaracion.tex; medir y falso (C14.1): la corrida y los
falsos positivos en <proyecto>/controles.yml; tiempo [<etapa> empezar|terminar]: la etapa en curso en tiempos.yml;
entregar [--destino RUTA] [--motivo TEXTO]: el candado de entrega (con «Faltan N» y sin motivo, se detiene). Sin
--aplicar, nada se escribe. Lo usan las
pruebas y las capturas; ningún dato real (el marco real, escritura, lo sirve con scripts/antes_de_entregar.py).
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

import yaml

MANUALES = {"revision": "Otra persona leyó la versión final.", "origen": "Cada cifra coincide con su cuadro de origen."}


def _json(d):
    print(json.dumps(d, ensure_ascii=False))
    sys.exit(0)


def _yaml(p: Path) -> dict:
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.is_file() else {}


def _control(id, grupo, nombre, estado, detalle="", hallazgos=(), **extra):
    return {"id": id, "grupo": grupo, "nombre": nombre, "porque": f"Por qué de muestra para «{nombre}».",
            "fuente": "Fuente de muestra (2026)", "estado": estado, "detalle": detalle, "hallazgos": list(hallazgos), **extra}


orden, proyecto = sys.argv[1], Path(sys.argv[2])
aplicar = "--aplicar" in sys.argv
estado_yml = proyecto / "entrega.yml"
def revisar() -> dict:
    tex = (proyecto / "informe.tex").read_text(encoding="utf-8")
    a_mano = [{"archivo": "informe.tex", "linea": n, "texto": f"«{m.group(0)}» escrito a mano: {l.strip()}"}
              for n, l in enumerate(tex.split("\n"), 1) for m in re.finditer(r"\d+,\d+(?:~?\\%)?", l)]
    d = _yaml(proyecto / "datos.yml")
    viejo = [{"archivo": "datos.yml", "linea": 3, "texto": f"{d['paquete']}@{d['usada']} es una versión vieja: está publicada la {d['ultima']}"}] \
        if d.get("usada") != d.get("ultima") else []
    marcados = _yaml(estado_yml).get("puntos") or {}
    usos = (_yaml(proyecto / "ia" / "registro.yml").get("usos")) or []
    incluida = "\\input{ia/declaracion}" in tex
    controles = [
        _control("cifras", "cifras", "Cifras vivas", "falla" if viejo else "aviso" if a_mano else "ok",
                 f"{len(viejo)} falla · {len(a_mano)} número escrito a mano" if viejo else f"{len(a_mano)} número escrito a mano",
                 viejo + a_mano),
        _control("lista.seccion", "lista", "Tiene una sección.", "ok" if "\\section" in tex else "falla", modo="automatico"),
    ] + [_control(f"lista.{k}", "lista", v, "manual", {"hecho": "Hecho", "justificado": "No aplica"}.get((marcados.get(k) or {}).get("estado"), "Sin marcar"),
                  modo="manual", marcado=(marcados.get(k) or {}).get("estado", ""), nota=(marcados.get(k) or {}).get("nota", ""))
         for k, v in MANUALES.items()] + [
        _control("referencias", "referencias", "Referencias verificables", "ok", "Sin citas."),
        _control("matriz", "matriz", "Matriz de consistencia: nada huérfano", "aviso" if not (proyecto / "matriz.yml").is_file() else "ok",
                 "El proyecto no tiene matriz.yml" if not (proyecto / "matriz.yml").is_file() else "", accion="matriz"),
        _control("autoevaluacion", "autoevaluacion", "Autoevaluación con la rúbrica",
                 "ok" if (proyecto / "autoevaluacion.yml").is_file() else "aviso",
                 "Rúbrica de muestra" if (proyecto / "autoevaluacion.yml").is_file() else "Rúbrica de muestra · 2 criterios sin puntuar",
                 accion="autoevaluar"),
        _control("ia", "ia", "Uso de la IA declarado", "falla" if usos and not incluida else "ok",
                 f"{len(usos)} uso registrado" if usos else "Sin usos de la IA registrados.",
                 [{"archivo": "informe.tex", "linea": 1, "texto": "El documento no incluye la declaración: añada \\input{ia/declaracion}"}]
                 if usos and not incluida else []),
    ]
    medidos = _yaml(proyecto / "controles.yml")
    for c in controles:                                # lo medido de cada control (C14.1)
        corridas = [x["controles"][c["id"]] for x in medidos.get("corridas") or [] if c["id"] in x.get("controles", {})]
        if corridas:
            atrapo = sum(1 for x in corridas if x in ("falla", "aviso"))
            falsos = sum(1 for f in medidos.get("falsos") or [] if f["control"] == c["id"])
            c["medicion"] = {"corridas": len(corridas), "atrapo": atrapo, "falsos": falsos,
                             "marca": "molesta" if atrapo and falsos > atrapo - falsos else ""}
    return {"tipo": "memoria", "lista": {"clave": "memoria", "nombre": "Memoria de muestra", "fuente": "Fuente de muestra (2026)"},
           "grupos": [{"clave": "cifras", "nombre": "Cifras y datos"}, {"clave": "lista", "nombre": "Lista de control · Memoria de muestra"},
                      {"clave": "referencias", "nombre": "Referencias y citas"}, {"clave": "ia", "nombre": "Inteligencia artificial"},
                      {"clave": "matriz", "nombre": "Matriz de consistencia"}, {"clave": "autoevaluacion", "nombre": "Autoevaluación"}],
           "controles": controles}


def _faltan(r: dict) -> int:
    return sum(1 for c in r["controles"] if c["estado"] == "falla" or (c["estado"] == "manual" and not c.get("marcado")))


def _opcion(nombre: str) -> str:
    return sys.argv[sys.argv.index(nombre) + 1] if nombre in sys.argv else ""


if orden == "revisar":
    _json(revisar())
if orden == "medir":                                   # revisa y anota la corrida en controles.yml (C14.1)
    r = revisar()
    corrida = {"fecha": date.today().isoformat(), "segundos": 0.1, "controles": {c["id"]: c["estado"] for c in r["controles"]}}
    if aplicar:
        d = _yaml(proyecto / "controles.yml")
        d.setdefault("corridas", []).append(corrida)
        (proyecto / "controles.yml").write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
        r = revisar()
    _json({"corrida": corrida, "ruta": "controles.yml", "escrito": aplicar, "revision": r})
if orden == "falso":
    control, nota = sys.argv[3], (sys.argv[4] if len(sys.argv) > 4 else "").strip()
    if not nota or nota == "--aplicar":
        _json({"error": "Un falso positivo se declara con su nota."})
    if aplicar:
        d = _yaml(proyecto / "controles.yml")
        d.setdefault("falsos", []).append({"fecha": date.today().isoformat(), "control": control, "nota": nota})
        (proyecto / "controles.yml").write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    _json({"falso": {"control": control, "nota": nota}, "ruta": "controles.yml", "escrito": aplicar})
if orden == "tiempo":                                  # el tiempo por etapa (C14.1), sin horas: solo qué etapa corre
    ETAPAS = [("datos", "Datos"), ("escritura", "Escritura"), ("entrega", "Entrega")]
    d = _yaml(proyecto / "tiempos.yml")
    abierta = d.get("abierta") or ""
    args = [a for a in sys.argv[3:] if not a.startswith("--")]
    if args:
        etapa, accion = args[0], (args[1] if len(args) > 1 else "")
        if etapa not in dict(ETAPAS) or accion not in ("empezar", "terminar"):
            _json({"error": f"«{etapa} {accion}» no es una etapa y una acción."})
        if accion == "terminar" and abierta != etapa:
            _json({"error": f"«{dict(ETAPAS)[etapa]}» no está en curso."})
        d["abierta"] = etapa if accion == "empezar" else ""
        d.setdefault("minutos", {})
        if abierta and abierta != d["abierta"]:
            d["minutos"][abierta] = d["minutos"].get(abierta, 0) + 30
        if aplicar:
            (proyecto / "tiempos.yml").write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
        _json({"etapa": etapa, "accion": accion, "escrito": aplicar})
    minutos = d.get("minutos") or {}
    _json({"abierta": {"etapa": abierta, "nombre": dict(ETAPAS)[abierta], "minutos": 5} if abierta else None,
           "etapas": [{"etapa": k, "nombre": n, "minutos": minutos.get(k, 0)} for k, n in ETAPAS],
           "total": sum(minutos.values()), "opciones": [{"clave": k, "nombre": n} for k, n in ETAPAS],
           "porque": "Por qué de muestra.", "fuente": "Fuente de muestra (2026)"})
if orden == "entregar":                                # el candado: con «Faltan N» y sin motivo, se detiene
    faltan, motivo, destino = _faltan(revisar()), _opcion("--motivo").strip(), _opcion("--destino")
    pdf = proyecto / "informe.pdf"
    if not pdf.is_file():
        _json({"error": "No hay PDF: compile el documento antes de entregarlo."})
    if faltan and not motivo:
        _json({"bloqueado": True, "faltan": faltan, "escrito": False,
               "mensaje": f"Faltan {faltan}: para entregar de todos modos, escriba el motivo."})
    entrada = {"fecha": date.today().isoformat(), "pdf": "informe.pdf", "destino": destino, "faltan": faltan,
               **({"motivo": motivo} if motivo else {})}
    if aplicar:
        if destino:
            Path(destino).write_bytes(pdf.read_bytes())
        d = _yaml(estado_yml)
        d.setdefault("entregas", []).append(entrada)
        estado_yml.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    _json({"bloqueado": False, "faltan": faltan, "entrega": entrada, "archivo": "entrega.yml", "escrito": aplicar})
if orden == "marcar":
    clave, estado = sys.argv[3].removeprefix("lista."), sys.argv[4]
    nota = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] != "--aplicar" else ""
    if clave not in MANUALES:
        _json({"error": f"«{clave}» no es un punto manual"})
    if estado == "justificado" and not nota.strip():
        _json({"error": "Para dar un punto por no aplicable, escriba por qué en la nota."})
    d = _yaml(estado_yml)
    puntos = d.setdefault("puntos", {})
    if estado == "pendiente" and not nota:
        puntos.pop(clave, None)
    else:
        puntos[clave] = {"estado": estado, "fecha": date.today().isoformat(), "nota": nota}
    if aplicar:
        estado_yml.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    _json({"id": f"lista.{clave}", "estado": estado, "nota": nota, "archivo": "entrega.yml", "escrito": aplicar})
if orden == "registrar_ia":
    uso = json.loads(sys.argv[3])
    if not uso.get("archivo") or not uso.get("resumen"):
        _json({"error": "Falta el archivo o el resumen del uso."})
    uso = {"fecha": uso.get("fecha") or date.today().isoformat(), **uso}
    uso["prompt"] = {k: v for k, v in (uso.get("prompt") or {}).items() if k != "texto"}
    registro = proyecto / "ia" / "registro.yml"
    usos = (_yaml(registro).get("usos") or []) + [uso]
    if aplicar:
        registro.parent.mkdir(exist_ok=True)
        registro.write_text(yaml.safe_dump({"usos": usos}, allow_unicode=True, sort_keys=False), encoding="utf-8")
        (proyecto / "ia" / "declaracion.tex").write_text(
            "\\noindent\\textbf{Uso de IA (muestra).}\n" + "".join(f"{u['fecha']}: {u['resumen']}. Lo revisó el autor.\\par\n" for u in usos),
            encoding="utf-8")
    _json({"uso": uso, "total": len(usos), "registro": "ia/registro.yml", "declaracion": "ia/declaracion.tex", "escrito": aplicar})
_json({"error": f"orden desconocida: {orden}"})
