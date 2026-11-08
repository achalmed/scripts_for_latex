"""tests/test_sincronizacion.py — trabajar junto a TeXstudio: el vigía del proyecto abierto (fuentes y PDF que cambian
fuera de la ventana) y la orden de TeXstudio. Todo en un temporal; nunca se lanza TeXstudio."""

from __future__ import annotations

import os
import time

from conftest import requiere_binding


def _esperar(app, condicion, segundos=5.0):
    inicio = time.monotonic()
    while not condicion() and time.monotonic() - inicio < segundos:
        app.processEvents()
        time.sleep(0.03)


@requiere_binding
def test_fuentes_y_pdf_que_cambian_fuera(app, tmp_path):
    from latex_app.controladores.sincronizacion import Sincronizacion

    principal = tmp_path / "doc.tex"
    capitulo = tmp_path / "cap.tex"
    pdf = tmp_path / "doc.pdf"
    for f in (principal, capitulo):
        f.write_text("x\n")
    s = Sincronizacion()
    fuentes, pdfs = [], []
    s.fuentesCambiadas.connect(lambda r: fuentes.append(list(r)))
    s.pdfCambiado.connect(pdfs.append)
    s.vigilar([str(principal), str(capitulo)], str(pdf))          # el PDF aún no existe: se vigila la carpeta

    # otro editor guarda reemplazando el archivo (como TeXstudio): llega una vez, agrupado
    nuevo = tmp_path / "cap.tex.tmp"
    nuevo.write_text("y\n")
    os.replace(nuevo, capitulo)
    _esperar(app, lambda: fuentes)
    assert fuentes == [[str(capitulo)]]

    # otro programa compila: aparece el PDF
    pdf.write_bytes(b"%PDF-1.5\n")
    _esperar(app, lambda: pdfs)
    assert pdfs == [str(pdf)]

    # la ventana compila: su PDF no cuenta como cambio de fuera
    pdf.write_bytes(b"%PDF-1.5\n% propio\n")
    s.anotar_pdf_propio()
    _esperar(app, lambda: len(pdfs) > 1, segundos=1.5)
    assert pdfs == [str(pdf)]
    s.soltar()


def test_orden_de_texstudio(tmp_path):
    from latex_app.aplicacion import Sistema

    principal, capitulo = str(tmp_path / "doc.tex"), str(tmp_path / "cap.tex")
    assert Sistema.orden_texstudio(capitulo, 12, principal) == ["texstudio", "--line", "12", capitulo]
    assert Sistema.orden_texstudio(principal, 0, principal) == ["texstudio", "--master", "--line", "1", principal]
