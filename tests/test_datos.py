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
