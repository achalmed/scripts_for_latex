"""tests/test_datos.py — la pestaña «Datos»: lo que declara la sección `datos:` del latex-studio.yml de un marco (§8 de
docs/configuracion-de-documentos.md), resuelto y corrido sobre el marco de muestra copiado a un temporal; ningún
documento real."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from latex_app import datos

MUESTRA = Path(__file__).resolve().parents[1] / "studio" / "ejemplo" / "proyectos" / "marco"


@pytest.fixture
def marco(tmp_path):
    destino = tmp_path / "marco"
    shutil.copytree(MUESTRA, destino)
    return destino


def test_declaracion_resuelve_rutas_y_proyecto(marco):
    principal = marco / "informes" / "informe-anual" / "informe.tex"
    d = datos.declaracion(principal)
    assert d["nombre"] == "Datos de muestra"
    assert d["proyecto"] == str(principal.parent.resolve())
    assert d["recursos"][1] == str((marco / "scripts" / "datos_muestra.py").resolve())   # «../» relativo al esquema
    assert d["recursos"][-1] == d["proyecto"] and d["actualizar"][2] == "actualizar"
    assert d["productor"] == {"nombre": "", "orden": []}


def test_sin_marcador_o_sin_esquema_no_hay_datos(marco, tmp_path):
    assert datos.declaracion(marco / "pruebas" / "caso.tex") is None                     # su carpeta no tiene datos.yml
    suelto = tmp_path / "suelto.tex"
    suelto.write_text("\\documentclass{article}\\begin{document}x\\end{document}\n")
    assert datos.declaracion(suelto) is None and datos.declaracion("") is None


def test_recursos_y_actualizar(marco):
    d = datos.declaracion(marco / "informes" / "informe-anual" / "informe.tex")
    r = datos.recursos(d)
    assert not r.get("error")
    assert [f["id"] for f in r["figuras"]] == ["serie_anual", "barras_region"]
    assert r["figuras"][0]["insertar"] == "\\includegraphics{figures/serie_anual.pdf}"
    assert r["paquetes"][0]["nueva"] and {c["macro"] for c in r["cifras"]} == {"\\cifraTotal", "\\cifraTasa"}
    subprocess.run(d["actualizar"], check=True, capture_output=True, cwd=d["proyecto"])
    assert not datos.recursos(d)["paquetes"][0]["nueva"]


def test_una_orden_rota_es_un_error_sin_datos(marco):
    d = datos.declaracion(marco / "informes" / "informe-anual" / "informe.tex")
    r = datos.recursos({**d, "recursos": [d["recursos"][0], "-c", "print('no es json')"]})
    assert r["error"] and r["figuras"] == []
    r = datos.recursos({**d, "recursos": ["/no/existe/orden"]})
    assert r["error"]


def test_biblioteca_del_marco_buscar_fichas_y_citar(marco):
    """La sección `biblioteca:` (contrato §9): buscar, las fichas del proyecto y citar en dos tiempos."""
    principal = marco / "informes" / "informe-anual" / "informe.tex"
    d = datos.declaracion_biblioteca(principal)
    assert d["nombre"] == "Biblioteca de muestra" and d["proyecto"] == str(principal.parent.resolve())
    libros, error = datos._json(datos.con(d["buscar"], texto="ciudades"), d["proyecto"])
    assert not error and [l["clave"] for l in libros] == ["quispe2021ciudades"]
    fichas, _ = datos._json(d["fichas"], d["proyecto"])
    assert fichas[0]["insertar"].startswith("“") and "\\parencite[p.~12]{quispe2021ciudades}" in fichas[0]["insertar"]
    simulado, _ = datos._json(datos.con(d["citar"], id="1"), d["proyecto"])
    assert simulado["nueva"] and not simulado["escrito"]                      # primero pregunta: es nueva
    aplicado, _ = datos._json(datos.con(d["citar"], id="1") + ["--aplicar"], d["proyecto"])
    assert aplicado["escrito"] and aplicado["insertar"] == "\\parencite{quispe2021ciudades}"
    assert not datos._json(datos.con(d["citar"], id="1"), d["proyecto"])[0]["nueva"]   # ya es fuente: se cita en el acto
    assert datos.declaracion_biblioteca(marco / "pruebas" / "caso.tex") is None


def test_fichar_desde_la_ventana_simula_escribe_y_respeta_la_huella(marco):
    """Fichar (§9 ampliado, decisiones §1.19): el formulario lo describe el marco; nueva_ficha simula y escribe con
    --aplicar; guardar_ficha exige la huella con que se abrió (ficha_cambiada si no)."""
    import json
    principal = marco / "informes" / "informe-anual" / "informe.tex"
    d = datos.declaracion_biblioteca(principal)
    formulario, _ = datos._json(d["formulario"], d["proyecto"])
    assert [t["clave"] for t in formulario["tipos"]][:2] == ["textual", "parafrasis"] and formulario["categorias"]
    campos = {"tipo": "textual", "calibre_id": 1, "pagina": "12", "categoria": "Cita clave", "tema": "escala",
              "secciones": {"Cita exacta": "Las ciudades pequeñas crecen cuando se integran a su región.", "Análisis": "", "Observaciones": ""}}
    sim, _ = datos._json(datos.con(d["nueva_ficha"], datos=json.dumps(campos)), d["proyecto"])
    assert sim["archivo"] == "quispe2021ciudades-p012-textual-escala.md" and not sim["escrito"]
    assert not (principal.parent / "fichas").exists(), "simular no escribe"
    hecho, _ = datos._json(datos.con(d["nueva_ficha"], datos=json.dumps(campos)) + ["--aplicar"], d["proyecto"])
    assert hecho["escrito"] and (principal.parent / "fichas" / hecho["archivo"]).is_file()
    leida, _ = datos._json(datos.con(d["ficha"], archivo=hecho["archivo"]), d["proyecto"])
    assert leida["secciones"][0]["texto"].startswith("Las ciudades") and len(leida["huella"]) == 64
    viejo, _ = datos._json(datos.con(d["guardar_ficha"], archivo=hecho["archivo"], huella="0" * 64, datos="{}") + ["--aplicar"], d["proyecto"])
    assert viejo["codigo"] == "ficha_cambiada"
    bien, _ = datos._json(datos.con(d["guardar_ficha"], archivo=hecho["archivo"], huella=leida["huella"],
                                    datos=json.dumps({"secciones": {"Cita exacta": "Otra.", "Análisis": "Nuevo."}})) + ["--aplicar"], d["proyecto"])
    assert bien["escrito"] and "Nuevo." in (principal.parent / "fichas" / hecho["archivo"]).read_text(encoding="utf-8")


def test_ayuda_del_marco_prompt_y_pegado_sin_escribir(marco, tmp_path):
    """La sección `ayuda:` (contrato §10): el prompt de la parte y lo pegado como cambio sugerido; nada se escribe."""
    principal = marco / "informes" / "informe-anual" / "informe.tex"
    a = datos.declaracion_ayuda(principal)
    assert a["nombre"].startswith("Ayuda de la IA") and a["proyecto"] == str(principal.parent.resolve())
    p, error = datos._json(datos.con(a["prompt"], archivo="informe.tex"), a["proyecto"])
    assert not error and "<entrada>" in p["prompt"] and p["componente"] == "informe"
    pegado, editor = tmp_path / "pegado.txt", tmp_path / "editor.tex"
    pegado.write_text("```latex\nUn párrafo nuevo.\n```", encoding="utf-8")
    antes = principal.read_text(encoding="utf-8")
    editor.write_text(antes, encoding="utf-8")
    r, _ = datos._json(datos.con(a["pegar"], archivo="informe.tex", pegado=str(pegado), tex=str(editor)), a["proyecto"])
    assert r["ok"] and r["despues"] == "Un párrafo nuevo.\n" and r["antes"] in antes
    assert principal.read_text(encoding="utf-8") == antes, "comprobar no escribe el documento"
    assert datos.declaracion_ayuda(marco / "pruebas" / "caso.tex") is None


def test_nuevo_documento_declara_simula_y_crea(marco, tmp_path):
    """La sección `nuevo:` (contrato §11, decisiones §1.20): los tipos con su formulario; `crear` sin --aplicar simula
    (devuelve la carpeta, los archivos y el principal, y no escribe en el marco); con --aplicar crea."""
    import json
    d = datos.declaracion_nuevo(marco)
    assert d["nombre"] == "Marco de muestra" and d["marco"] == "muestra"
    assert d["esquema"] == str((marco / "config" / "latex-studio.yml").resolve())
    assert d["tipos"][1] == str((marco / "scripts" / "nuevo_muestra.py").resolve())      # «../» relativo al esquema
    assert datos.declaracion_nuevo(marco / "informes") == {**d, "carpeta": str((marco / "informes").resolve())}   # sube
    assert datos.declaracion_nuevo(tmp_path / "no-existe") is None and datos.declaracion_nuevo("") is None
    vacia = tmp_path / "vacia"
    vacia.mkdir()
    assert datos.declaracion_nuevo(vacia) is None
    assert [x["esquema"] for x in datos.declaraciones_nuevo([marco, marco / "informes", vacia])] == [d["esquema"]]

    cat, error = datos._json(d["tipos"], d["carpeta"])
    assert not error and [t["clave"] for t in cat["tipos"]] == ["memoria", "nota", "acta"]
    memoria = cat["tipos"][0]
    assert memoria["descripcion"] and [v["clave"] for v in memoria["variante"]["opciones"]] == ["anual", "semestral"]
    assert {c["clave"]: c["tipo"] for c in memoria["campos"]}["autores"] == "lineas"

    antes = sorted(str(p.relative_to(marco)) for p in marco.rglob("*"))
    campos = {"tipo": "memoria", "variante": "anual", "titulo": "Memoria institucional 2026", "autores": "Rosa Quispe\nTomás Arango"}
    sim, _ = datos._json(datos.con(d["crear"], datos=json.dumps(campos, ensure_ascii=False)), d["carpeta"])
    assert not sim.get("error") and not sim["escrito"]
    assert sim["carpeta"].startswith("informes/") and sim["carpeta"].endswith("-memoria-institucional-2026")
    assert sim["principal"] == str(marco.resolve() / sim["carpeta"] / "informe.tex") and "informe.tex" in sim["archivos"]
    assert sorted(str(p.relative_to(marco)) for p in marco.rglob("*")) == antes, "simular no escribe en el marco"
    hecho, _ = datos._json(datos.con(d["crear"], datos=json.dumps(campos, ensure_ascii=False)) + ["--aplicar"], d["carpeta"])
    assert hecho["escrito"] and Path(hecho["principal"]).is_file() and hecho["archivos"] == sim["archivos"]
    otra, _ = datos._json(datos.con(d["crear"], datos=json.dumps(campos)), d["carpeta"])
    assert otra["error"].startswith("Ya existe")
    falta, _ = datos._json(datos.con(d["crear"], datos=json.dumps({**campos, "autores": ""})), d["carpeta"])
    assert "Autores" in falta["error"]


def test_entrega_declara_revisa_marca_y_registra(marco):
    """La sección `entrega:` (contrato §12, decisiones §1.21): `revisar` devuelve los controles (la ventana les pone la
    ruta y el veredicto); `marcar` y `registrar_ia` simulan sin --aplicar y escriben con él."""
    import json
    principal = marco / "informes" / "informe-anual" / "informe.tex"
    d = datos.declaracion_entrega(principal)
    assert d["nombre"] == "Antes de entregar" and d["proyecto"] == str(principal.parent.resolve())
    assert d["revisar"][1] == str((marco / "scripts" / "entrega_muestra.py").resolve()) and d["revisar"][-1] == d["proyecto"]
    assert datos.declaracion_entrega(marco / "pruebas" / "caso.tex") is None and datos.declaracion_entrega("") is None

    dato, error = datos._json(d["revisar"], d["proyecto"])
    r = datos.resultado_entrega(dato, d["proyecto"])
    assert not error and not r["error"] and [g["clave"] for g in r["grupos"]] == ["cifras", "lista", "referencias", "ia", "matriz", "autoevaluacion"]
    cifras = r["controles"][0]
    assert cifras["estado"] == "falla" and cifras["hallazgos"][1]["ruta"] == str(principal) and cifras["hallazgos"][1]["linea"] == 8
    assert (r["fallas"], r["pendientes"], r["faltan"], r["listo"]) == (1, 2, 3, False)

    sim, _ = datos._json(datos.con(d["marcar"], id="lista.revision", estado="hecho", nota="La leyó Tomás"), d["proyecto"])
    assert not sim["escrito"] and not (principal.parent / "entrega.yml").exists(), "marcar sin --aplicar no escribe"
    for id_, estado, nota in (("lista.revision", "hecho", "La leyó Tomás"), ("lista.origen", "justificado", "Sin cuadros")):
        hecho, _ = datos._json(datos.con(d["marcar"], id=id_, estado=estado, nota=nota) + ["--aplicar"], d["proyecto"])
        assert hecho["escrito"]
    error, _ = datos._json(datos.con(d["marcar"], id="lista.origen", estado="justificado", nota="") + ["--aplicar"], d["proyecto"])
    assert error["error"]
    subprocess.run(datos.declaracion(principal)["actualizar"], check=True, capture_output=True, cwd=d["proyecto"])
    r = datos.resultado_entrega(datos._json(d["revisar"], d["proyecto"])[0], d["proyecto"])
    assert r["listo"] and r["avisos"] == 3                        # los avisos no bloquean: listo para entregar
    assert {c["accion"] for c in r["controles"] if c.get("accion")} == {"matriz", "autoevaluar"}   # abren su ventana (§1.22)

    uso = datos.uso_de_ia(d["proyecto"], str(principal), "Informe anual", {"titulo": "Redacción", "version": "1.0", "ruta": ""},
                          "Una línea.\nOtra.\n", "Una sola.\n")
    assert uso == {"archivo": "informe.tex", "parte": "Informe anual", "prompt": {"titulo": "Redacción", "version": "1.0"},
                   "resumen": "reemplazó 2 líneas de texto por 1"}
    sim, _ = datos._json(datos.con(d["registrar_ia"], datos=json.dumps(uso, ensure_ascii=False)), d["proyecto"])
    assert not sim["escrito"] and not (principal.parent / "ia").exists(), "registrar sin --aplicar no escribe"
    hecho, _ = datos._json(datos.con(d["registrar_ia"], datos=json.dumps(uso, ensure_ascii=False)) + ["--aplicar"], d["proyecto"])
    assert hecho["escrito"] and (principal.parent / "ia" / "declaracion.tex").is_file()
    r = datos.resultado_entrega(datos._json(d["revisar"], d["proyecto"])[0], d["proyecto"])
    assert not r["listo"] and next(c for c in r["controles"] if c["id"] == "ia")["estado"] == "falla"


def test_veredicto_y_lo_mal_formado():
    """El veredicto lo da la ventana con lo revisado: listo solo sin fallas y con todo lo manual marcado o justificado;
    un resultado mal formado es un error, nunca «listo»."""
    controles = [{"estado": "ok"}, {"estado": "aviso"}, {"estado": "manual", "marcado": "justificado"}]
    assert datos.veredicto(controles)["listo"]
    assert datos.veredicto(controles + [{"estado": "manual", "marcado": ""}]) == {"fallas": 0, "pendientes": 1, "avisos": 1, "faltan": 1, "listo": False}
    assert datos.veredicto(controles + [{"estado": "falla"}])["faltan"] == 1
    assert not datos.veredicto([])["listo"]
    for malo in (None, [], "texto", {"error": "no hay maestro"}):
        r = datos.resultado_entrega(malo, "/x")
        assert r["error"] and not r["listo"] and r["controles"] == []
    r = datos.resultado_entrega({"controles": [{"id": "x", "estado": "raro"}, {"id": "y", "grupo": "nuevo", "estado": "ok",
                                                "hallazgos": [{"archivo": "/abs/a.tex", "linea": "3", "texto": "t"}]}]}, "/p")
    assert [c["id"] for c in r["controles"]] == ["y"] and r["grupos"] == [{"clave": "nuevo", "nombre": "Nuevo"}]
    assert r["controles"][0]["hallazgos"][0] == {"archivo": "/abs/a.tex", "ruta": "/abs/a.tex", "linea": 3, "texto": "t"}


def test_matriz_declara_lee_crea_y_guarda_la_pregunta(marco):
    """La sección `matriz:` (contrato §13, decisiones §1.22): `leer` devuelve las filas con lo huérfano (la ventana les pone
    rutas absolutas y cuenta fallas y avisos); `nueva`, `cuadro` y `pregunta` simulan sin --aplicar y escriben con él."""
    import json
    principal = marco / "informes" / "informe-anual" / "informe.tex"
    d = datos.declaracion_seccion(principal, "matriz")
    assert d["nombre"] == "Matriz de consistencia" and d["proyecto"] == str(principal.parent.resolve())
    assert datos.declaracion_seccion(marco / "pruebas" / "caso.tex", "matriz") is None and datos.declaracion_seccion("", "matriz") is None
    r = datos.resultado_matriz(datos._json(d["leer"], d["proyecto"])[0], d["proyecto"])
    assert not r["existe"] and r["filas"] == [] and not r["error"]
    sim, _ = datos._json(d["nueva"], d["proyecto"])
    assert not sim["escrito"] and not (principal.parent / "matriz.yml").exists(), "nueva sin --aplicar no escribe"
    datos._json(d["nueva"] + ["--aplicar"], d["proyecto"])
    r = datos.resultado_matriz(datos._json(d["leer"], d["proyecto"])[0], d["proyecto"])
    assert r["existe"] and r["ruta"] == str(principal.parent / "matriz.yml") and len(r["filas"]) == 2
    general, he1 = r["filas"]
    assert general["estado"] == "ok" and general["secciones"][0]["ruta"] == str(principal.parent / "informe.tex")
    assert he1["estado"] == "falla" and (r["fallas"], r["avisos"]) == (1, 1)
    assert all(h["ruta"].endswith("matriz.yml") and h["linea"] > 0 for h in r["huerfanos"])
    guia, _ = datos._json(d["guia"], d["proyecto"])
    assert len(guia["pasos"]) == 4 and all(p["fuente"] for p in guia["pasos"])
    revisada, _ = datos._json(datos.con(d["pregunta"], datos=json.dumps({"tema": "x"})), d["proyecto"])
    assert not revisada["ok"] and not revisada["escrito"]
    valores = {"tema": "Empleo", "hecho": "No cuadra", "poblacion": "Ciudades", "periodo": "2019 a 2024", "comparacion": "por sector",
               "texto": "¿Cuánto del empleo se explica por el sector?", "evidencia": "La encuesta"}
    hecho, _ = datos._json(datos.con(d["pregunta"], datos=json.dumps(valores)) + ["--aplicar"], d["proyecto"])
    assert hecho["escrito"] and "sector" in (principal.parent / "matriz.yml").read_text(encoding="utf-8")


def test_revisor_y_plantillas_del_marco(marco, tmp_path):
    """`revisor:` (§14) recibe una copia del texto del editor y devuelve hallazgos que la ventana junta con su regla
    (nombre, porqué, fuente), ordenados por línea; `plantillas:` (§15) lista y compone sin escribir nada."""
    import json
    principal = marco / "informes" / "informe-anual" / "informe.tex"
    d = datos.declaracion_seccion(principal, "revisor")
    copia = tmp_path / "editor.tex"
    copia.write_text("Texto.\n{\\bf negrita}\nLos datos fueron recogidos en campo.\n", encoding="utf-8")
    r = datos.resultado_revisor(datos._json(datos.con(d["revisar"], archivo=str(copia), ruta=str(principal)), d["proyecto"])[0])
    assert not r["error"] and (r["estilo"], r["latex"]) == (1, 1)
    obsoleto, pasiva = r["hallazgos"]
    assert obsoleto["linea"] == 2 and obsoleto["fuente"] == "Trettin (2016)" and obsoleto["porque"]
    assert pasiva["linea"] == 3 and pasiva["clase"] == "estilo" and pasiva["sugerencia"]
    assert datos.resultado_revisor({"error": "x"})["error"] == "x" and datos.resultado_revisor(None)["error"]
    p = datos.declaracion_seccion(principal, "plantillas")
    lista, _ = datos._json(p["listar"], p["proyecto"])
    assert {x["clave"] for x in lista["plantillas"]} == {"figura", "cuadro"} and all(x["fuente"] for x in lista["plantillas"])
    antes = sorted(x.name for x in principal.parent.iterdir())
    c, _ = datos._json(datos.con(p["componer"], datos=json.dumps({"plantilla": "figura", "valores": {"archivo": "f.pdf", "titulo": "T"}})), p["proyecto"])
    assert "alt={}" in c["insertar"] and "Falta «Texto alternativo»." in c["avisos"]
    assert sorted(x.name for x in principal.parent.iterdir()) == antes, "componer no escribe"


def test_rubrica_y_revisar_prompt(marco, tmp_path):
    """La autoevaluación (`rubrica` y `autoevaluar` de §12) y el aviso antes de copiar un prompt (`revisar_prompt` de §10)."""
    import json
    principal = marco / "informes" / "informe-anual" / "informe.tex"
    d = datos.declaracion_entrega(principal)
    r = datos.resultado_rubrica(datos._json(d["rubrica"], d["proyecto"])[0])
    assert r["hay"] and r["faltan"] == 2 and r["criterios"][0]["niveles"][0]["texto"] == "3" and r["fuente"]
    carga = json.dumps({"clave": "claridad", "puntaje": "3", "justificacion": "Se lee de corrido sin volver atrás."})
    sim, _ = datos._json(datos.con(d["autoevaluar"], datos=carga), d["proyecto"])
    assert not sim["escrito"] and not (principal.parent / "autoevaluacion.yml").exists()
    datos._json(datos.con(d["autoevaluar"], datos=carga) + ["--aplicar"], d["proyecto"])
    r = datos.resultado_rubrica(datos._json(d["rubrica"], d["proyecto"])[0])
    assert r["faltan"] == 1 and r["criterios"][0]["puntaje"] == "3" and r["criterios"][0]["justificacion"]
    assert datos.resultado_rubrica({"rubrica": None})["hay"] is False and datos.resultado_rubrica("x")["error"]
    a = datos.declaracion_ayuda(principal)
    prompt = tmp_path / "p.txt"
    prompt.write_text("Corrige la parte. DNI 12345678 del estudiante.\n", encoding="utf-8")
    s, _ = datos._json(datos.con(a["revisar_prompt"], prompt=str(prompt)), a["proyecto"])
    assert s["sensible"] and s["hallazgos"][0]["linea"] == 1 and s["fuente"]
    prompt.write_text("Corrige la parte.\n", encoding="utf-8")
    assert not datos._json(datos.con(a["revisar_prompt"], prompt=str(prompt)), a["proyecto"])[0]["sensible"]
