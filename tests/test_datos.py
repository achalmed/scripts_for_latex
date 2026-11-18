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
