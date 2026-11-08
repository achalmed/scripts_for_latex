"""tests/test_okular.py — Okular como visor (2026-11-08): las órdenes (abrir y SyncTeX hacia el PDF), su editor externo
(Mayús+clic → `main.py --ir`) editado en un okularpartrc temporal, y la instancia única que recibe ese salto. Nunca se
lanza Okular ni se toca su configuración real."""

from __future__ import annotations

import time

import pytest

from conftest import requiere_binding
from latex_app import instancia, okular


def test_ordenes_de_okular(tmp_path):
    pdf, tex = str(tmp_path / "doc.pdf"), str(tmp_path / "cap.tex")
    assert okular.orden_abrir(pdf) == ["okular", "--unique", pdf]
    assert okular.orden_abrir(pdf, tex, 12) == ["okular", "--unique", f"{pdf}#src:12{tex}"]
    assert okular.deseado()["ExternalEditorCommand"].endswith("main.py --ir %f %l")


RC = """[General]
ttsEngine=

[Core General]
ExternalEditor=Kate
ObeyDRM=false

[PageView]
MouseMode=TextSelect
"""


@pytest.fixture
def rc(tmp_path, monkeypatch):
    monkeypatch.setattr(okular, "okular_abierto", lambda: False)
    destino = tmp_path / "dotfiles" / "okularpartrc"
    destino.parent.mkdir()
    destino.write_text(RC)
    enlace = tmp_path / "config" / "okularpartrc"
    enlace.parent.mkdir()
    enlace.symlink_to(destino)                       # como el paquete stow de dotfiles
    return enlace


def test_editor_externo_solo_sus_claves_con_respaldo_y_enlace(rc, monkeypatch):
    assert {k for k, _a, _n in okular.cambios(rc)} == {"ExternalEditor", "ExternalEditorCommand"}
    assert okular.aplicar(rc) == ""
    texto = rc.read_text()
    assert rc.is_symlink() and okular.configurado(rc)
    assert "ExternalEditor=Custom" in texto and "ObeyDRM=false" in texto and "MouseMode=TextSelect" in texto
    seccion = texto.split("[Core General]")[1].split("[PageView]")[0]
    assert "ExternalEditorCommand=" in seccion                     # en su grupo, no al final del archivo
    assert list(rc.parent.glob("okularpartrc.antes-latex-studio-*"))
    assert okular.deshacer(rc) == "" and rc.read_text() == RC
    monkeypatch.setattr(okular, "okular_abierto", lambda: True)
    assert "Cierra Okular" in okular.aplicar(rc) and rc.read_text() == RC


def test_sin_grupo_lo_crea(tmp_path, monkeypatch):
    monkeypatch.setattr(okular, "okular_abierto", lambda: False)
    rc = tmp_path / "okularpartrc"
    rc.write_text("[General]\nttsEngine=\n")
    assert okular.aplicar(rc) == "" and okular.configurado(rc) and rc.read_text().startswith("[General]\nttsEngine=\n")


def test_argumentos_ir(tmp_path):
    assert instancia.argumentos_ir(["--ir", str(tmp_path / "a.tex"), "17"]) == (str(tmp_path / "a.tex"), 17)
    assert instancia.argumentos_ir(["a.tex"]) is None
    assert instancia.argumentos_ir(["--ir", "a.tex", "x"])[1] == 0


@requiere_binding
def test_el_salto_llega_a_la_ventana_abierta(app, tmp_path):
    nombre = str(tmp_path / "prueba.sock")
    assert not instancia.enviar("a.tex", 1, nombre)                  # sin ventana: arranca una
    servidor = instancia.Servidor(nombre)
    assert servidor.escuchando
    recibidos = []
    servidor.irA.connect(lambda a, l: recibidos.append((a, l)))
    assert instancia.enviar("/x/cap.tex", 42, nombre)
    inicio = time.monotonic()
    while not recibidos and time.monotonic() - inicio < 3:
        app.processEvents()
        time.sleep(0.02)
    assert recibidos == [("/x/cap.tex", 42)]
    otra = instancia.Servidor(nombre)                                # una segunda ventana no le quita el socket
    assert not otra.escuchando
    servidor.cerrar()
