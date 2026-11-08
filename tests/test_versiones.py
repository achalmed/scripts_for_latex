"""tests/test_versiones.py — las versiones que un marco produce de un mismo .tex (`versiones:` de su latex-studio.yml,
docs/configuracion-de-documentos.md §7): el modelo (job, PDF, SyncTeX y .log de la elegida), la receta (el argumento del
marco), el puente compilar.py, «Configurar el documento» (el comentario mágico y la línea del visor de TeXstudio) y la
elección en la ventana. Sobre la muestra (studio/ejemplo/proyectos/marco: versiones «completa» y «resumen») copiada a
un temporal; nada de documentos reales."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from conftest import STUDIO, copiar_muestra, requiere_binding, requiere_lualatex
from test_controladores import piezas  # noqa: F401  (el fixture con los controladores sobre la muestra)
from latex_app import compilador as svc
from latex_app import configuracion as cf
from latex_app import proyectos as pr


@pytest.fixture
def informe(tmp_path) -> Path:
    muestra = copiar_muestra(tmp_path / "muestra")
    return muestra / "marco" / "informes" / "informe-anual" / "informe.tex"


def test_el_marco_declara_versiones_y_la_omision(informe):
    p = pr.proyecto_de(informe, pr.Cache())
    assert [v["clave"] for v in p.versiones] == ["completa", "resumen"]
    assert p.version_argumento == "--version" and p.version_comentario == "VERSION"
    assert p.version == p.version_declarada == "completa" and p.job == "informe"


def test_el_documento_declara_su_version_y_elegir_otra_no_escribe(informe):
    informe.write_text("% !VERSION = Resumen\n" + informe.read_text())
    antes = informe.read_text()
    p = pr.proyecto_de(informe, pr.Cache())
    assert p.version_declarada == "resumen" and p.job == "informe-resumen"
    assert p.elegir_version("completa") and p.job == "informe"
    assert not p.elegir_version("inexistente") and p.version == "completa"
    assert informe.read_text() == antes


def test_un_comentario_invalido_cae_en_la_omision(informe):
    informe.write_text("% !VERSION = rara\n" + informe.read_text())
    assert pr.proyecto_de(informe, pr.Cache()).version_declarada == "completa"


def test_la_receta_pide_la_version_al_compilador_del_marco(informe):
    p = pr.proyecto_de(informe, pr.Cache())
    p.elegir_version("resumen")
    paso = svc.receta(p, "compilar")[0]
    assert paso.argv[-2:] == ["--version", "resumen"] and "Resumen" in paso.descripcion
    assert svc.receta(p, "limpiar")[0].argv[-2:] != ["--version", "resumen"]     # limpiar no lleva versión
    assert svc.registro_motor(p).name == "informe-resumen.log"


def _puente(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(STUDIO / "compilar.py"), *args], capture_output=True, text=True, timeout=300)


def test_el_puente_lista_y_valida_versiones(informe):
    r = _puente(str(informe), "--versiones")
    assert r.returncode == 0 and "resumen" in r.stdout and "informe-resumen.pdf" in r.stdout
    r = _puente(str(informe), "--version", "resumen", "--simular")
    assert r.returncode == 0 and r.stdout.rstrip().endswith("--version resumen") and "versión: Resumen" in r.stdout
    r = _puente(str(informe), "--version", "nada")
    assert r.returncode == 2 and "completa, resumen" in r.stderr


@requiere_lualatex
def test_compilar_otra_version_deja_su_pdf_y_su_synctex(informe):
    r = _puente(str(informe), "--version", "resumen")
    assert r.returncode == 0, r.stdout[-1500:]
    assert (informe.parent / "informe-resumen.pdf").is_file() and not (informe.parent / "informe.pdf").exists()
    p = pr.proyecto_de(informe, pr.Cache())
    p.elegir_version("resumen")
    pr.leer_estado(p, pr.Cache())
    assert p.pdf.endswith("informe-resumen.pdf") and p.synctex.endswith("informe-resumen.synctex.gz")
    assert p.estado == "compilado" and p.log.endswith("informe-resumen.log")


def test_configurar_escribe_la_version_y_la_linea_del_visor_de_texstudio(informe):
    conf = cf.configuracion_de(informe)
    assert conf.secciones[0].titulo == "Versión" and conf.campos()["_version"].valor == "completa"
    cf.aplicar(cf.cambios(conf, {"_version": "resumen"}))
    texto = informe.read_text()
    assert "% !VERSION = resumen\n% !TeX TXS-program:view = txs:///view-pdf-internal --embedded ?m)-resumen.pdf\n\\documentclass" in texto
    assert cf.configuracion_de(informe).campos()["_version"].valor == "resumen"
    assert pr.proyecto_de(informe, pr.Cache()).version_declarada == "resumen"
    cf.aplicar(cf.cambios(cf.configuracion_de(informe), {"_version": "completa"}))     # la omisión: quita las dos líneas
    assert "!VERSION" not in informe.read_text() and "TXS-program" not in informe.read_text()


@requiere_binding
def test_la_ventana_elige_version_sin_escribir_y_configurar_manda(piezas):
    proyectos = piezas["proyectos"]
    proyectos.detectar_ya()
    informe = piezas["muestra"] / "marco" / "informes" / "informe-anual" / "informe.tex"
    antes = informe.read_text()
    assert proyectos.abrir(str(informe)) == ""
    proyectos.elegirVersion("resumen")
    assert proyectos.abierto["version"] == "resumen" and proyectos.abierto["job"] == "informe-resumen"
    proyectos.refrescar(str(informe.resolve()))                       # tras compilar: la elección sigue
    assert proyectos.proyecto_abierto().version == "resumen"
    proyectos.detectar_ya()                                           # y tras volver a detectar
    assert proyectos.proyecto_abierto().version == "resumen"
    assert informe.read_text() == antes                               # elegir no escribe
    proyectos.olvidar_version(str(informe.resolve()))                 # «Configurar» escribió: manda el documento
    proyectos.refrescar(str(informe.resolve()))
    assert proyectos.proyecto_abierto().version == "completa"


def test_el_esquema_valida_el_bloque_de_versiones(tmp_path):
    malo = tmp_path / "latex-studio.yml"
    malo.write_text("documentos:\n  - nombre: X\n    versiones: {lista: []}\n")
    with pytest.raises(cf.ErrorEsquema, match="versiones"):
        cf.cargar_esquema(malo)
    assert cf.verificar_esquema(STUDIO / "ejemplo" / "proyectos" / "marco" / "config" / "latex-studio.yml") == []
