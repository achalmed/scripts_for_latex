"""tests/test_texstudio.py — compilar desde TeXstudio con la receta de LaTeX Studio: el puente `studio/compilar.py` (sobre la
muestra copiada a un temporal) y el configurador `latex_app/texstudio.py` (sobre un texstudio.ini temporal). Nunca se
lanza TeXstudio ni se toca su configuración real."""

from __future__ import annotations

import subprocess
import sys

import pytest

from conftest import STUDIO, copiar_muestra, requiere_biber

COMPILAR = STUDIO / "compilar.py"


def _puente(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(COMPILAR), *args], capture_output=True, text=True, timeout=300)


def test_puente_simula_la_receta_del_marco(tmp_path):
    muestra = copiar_muestra(tmp_path / "proyectos")
    tex = muestra / "marco" / "informes" / "informe-anual" / "informe.tex"
    r = _puente(str(tex), "--simular")
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("LaTeX Studio · informe.tex")
    assert "build.sh" in r.stdout                      # el compilador del marco, no un lualatex a secas
    assert "✓ listo" not in r.stdout                   # simular no ejecuta


def test_puente_rechaza_lo_que_no_es_documento(tmp_path):
    suelto = tmp_path / "suelto.tex"
    suelto.write_text("\\section{Sin clase}\n")
    assert _puente(str(suelto), "--simular").returncode == 2
    assert _puente(str(tmp_path / "no-existe.tex")).returncode == 2


@requiere_biber
def test_puente_compila_de_verdad(tmp_path):
    muestra = copiar_muestra(tmp_path / "proyectos")
    tex = next((muestra / "articulo-bibtex").glob("*.tex"))
    r = _puente(str(tex))
    assert r.returncode == 0, r.stdout[-2000:]
    assert "✓ listo" in r.stdout
    assert tex.with_suffix(".pdf").is_file() or any(tex.parent.rglob(tex.stem + ".pdf"))


INI = """[General]
version=4.8

[texmaker]
Tools\\Commands\\compile=txs:///pdflatex
Tools\\Commands\\bibliography=txs:///bibtex
Tools\\Log%20Paths=
Editor\\Font%20Size=11
Tools\\Recent=@Variant(\\0\\0\\0\\x7f\\0\\0\\0\\x10StringStringMap\\0)

[formatos]
x=1
"""


@pytest.fixture
def ini(tmp_path, monkeypatch):
    from latex_app import texstudio as txs
    monkeypatch.setattr(txs, "texstudio_abierto", lambda: False)
    ruta = tmp_path / "texstudio" / "texstudio.ini"
    ruta.parent.mkdir()
    ruta.write_text(INI)
    return ruta


def test_configurador_simula_y_aplica_solo_sus_claves(ini):
    from latex_app import texstudio as txs
    claves = {k for k, _a, _n in txs.cambios(ini)}
    assert claves == set(txs.deseado())                # PDF Paths no estaba: también se añade
    assert ini.read_text() == INI                      # mirar no escribe
    assert txs.aplicar(ini) == ""
    assert txs.configurado(ini)
    nuevo = ini.read_text().split("\n")
    viejo = INI.split("\n")
    assert len(nuevo) == len(viejo) + 1                # una clave añadida, ninguna perdida
    assert "Tools\\Recent=@Variant(\\0\\0\\0\\x7f\\0\\0\\0\\x10StringStringMap\\0)" in nuevo   # lo de Qt, intacto
    assert "Editor\\Font%20Size=11" in nuevo and "[formatos]" in nuevo
    i_seccion, i_formatos = nuevo.index("[texmaker]"), nuevo.index("[formatos]")
    assert all(i_seccion < nuevo.index(f"{k}={v}") < i_formatos for k, v in txs.deseado().items())
    assert f"compilar.py %.tex" in txs.deseado()["Tools\\Commands\\compile"]
    assert list(ini.parent.glob("texstudio.ini.antes-latex-studio-*"))   # respaldo al lado


def test_configurador_conserva_el_enlace(ini, tmp_path):
    """La configuración puede ser un enlace (paquete stow de dotfiles): se escribe en su destino y el enlace sigue."""
    from latex_app import texstudio as txs
    destino = tmp_path / "dotfiles" / "texstudio.ini"
    destino.parent.mkdir()
    ini.rename(destino)
    ini.symlink_to(destino)
    assert txs.aplicar(ini) == ""
    assert ini.is_symlink() and txs.configurado(destino)
    assert not list(destino.parent.glob("texstudio.ini.antes-*"))       # el respaldo no entra en el repo del destino
    assert txs.deshacer(ini) == ""
    assert ini.is_symlink() and destino.read_text() == INI


def test_configurador_deshace_y_respeta_texstudio_abierto(ini, monkeypatch):
    from latex_app import texstudio as txs
    assert txs.aplicar(ini) == ""
    assert txs.deshacer(ini) == ""
    assert ini.read_text() == INI
    monkeypatch.setattr(txs, "texstudio_abierto", lambda: True)
    assert "Cierra TeXstudio" in txs.aplicar(ini)
    assert ini.read_text() == INI                      # con TeXstudio abierto no se escribe nada
