"""tests/test_rediseno.py — lo que trajo el rediseño del 2026-11-17 (decisiones §1.17): la fecha «como la dice una
persona», las miniaturas de la primera página (pdftoppm, a un temporal) y las tarjetas de la página de proyectos (los
campos que pintan y las filas visibles). Sobre la muestra; ningún documento real."""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest

from latex_app import compilador as svc
from latex_app import miniaturas as mn

# un PDF de una página, mínimo y válido, escrito a mano (sin compilar nada)
PDF_MINIMO = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
              b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 280]>>endobj\n"
              b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000101 00000 n \n"
              b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n164\n%%EOF\n")


def test_hace_como_lo_dice_una_persona():
    ahora = 1_800_000_000.0
    assert svc.hace(0) == "nunca"
    assert svc.hace(ahora - 20, ahora) == "hace un momento"
    assert svc.hace(ahora - 5 * 60, ahora) == "hace 5 min"
    assert svc.hace(ahora - 3 * 3600, ahora) == "hace 3 h"
    assert svc.hace(ahora - 30 * 3600, ahora) == "ayer"
    assert svc.hace(ahora - 4 * 86400, ahora) == "hace 4 días"
    assert svc.hace(ahora - 90 * 86400, ahora).count("/") == 2


@pytest.mark.skipif(not shutil.which("pdftoppm"), reason="sin pdftoppm (poppler-utils)")
def test_miniatura_de_la_primera_pagina_y_su_renovacion(tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(PDF_MINIMO)
    cache = tmp_path / "cache"
    png = mn.generar(pdf, cache)
    assert png is not None and png.is_file() and png.read_bytes()[:4] == b"\x89PNG"
    assert mn.generar(pdf, cache) == png                         # la segunda vez no dibuja: ya está
    assert not list(cache.glob("miniaturas/*-parcial*"))          # nunca queda una a medias
    time.sleep(0.01)
    pdf.write_bytes(PDF_MINIMO + b"\n")                           # el PDF cambió: otra miniatura y la vieja se va
    nueva = mn.generar(pdf, cache)
    assert nueva != png and nueva.is_file() and not png.exists()
    assert mn.generar(tmp_path / "no-existe.pdf", cache) is None
