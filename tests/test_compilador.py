"""tests/test_compilador.py — el servicio sin Qt (`studio/latex_app/compilador.py`): la lectura del registro, la orden de la
CLI y las consultas de la ventana 2.x (motor declarado, auxiliares, salidas, estado leído del disco, progreso).

Se prueba fuera de los repos: cada .tex vive en una carpeta temporal.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from conftest import REPO, copiar_ejemplo, requiere_lualatex

from latex_app import compilador as svc  # noqa: E402
from latex_app.compilador import Opciones, leer_log, resumen  # noqa: E402

LOG = r"""This is LuaHBTeX, Version 1.18.0
(./prueba.tex
LaTeX Warning: Reference `nada' on page 1 undefined on input line 3.

! Undefined control sequence.
l.4 \comandoquenoexiste

Overfull \hbox (12.0pt too wide) in paragraph at lines 5--5
Package hyperref Warning: Token not allowed in a PDF string on input line 7.
)
"""


def test_lee_errores_y_avisos_con_su_linea():
    ps = leer_log(LOG)
    assert [(p.nivel, p.linea) for p in ps] == [("error", 4), ("aviso", 3), ("aviso", 7), ("tipografia", 5)]
    assert ps[0].mensaje == "Undefined control sequence." and ps[0].archivo == "./prueba.tex"
    assert ps[2].mensaje.startswith("hyperref:")
    assert resumen(ps) == "1 error(es) · 2 aviso(s) · 1 de tipografía"


def test_atribuye_cada_problema_al_tex_abierto_y_omite_las_consecuencias():
    """Un error dentro de un paquete del sistema se atribuye al .tex del documento que lo cargó; la pila de paréntesis
    sigue los \\input; «Fatal error occurred» y «Emergency stop» no son problemas, son consecuencias."""
    log = ("(./a.tex (/usr/share/texlive/x/babel.sty\n! LaTeX hooks Error: Generic hooks cannot be added.\nl.12 \\begin{document}\n) "
           "(./cap.tex\n! Undefined control sequence.\nl.9 \\y\n)\n! Emergency stop.\n!  ==> Fatal error occurred, no output PDF file produced!\n")
    ps = leer_log(log)
    assert [(p.linea, p.archivo, p.mensaje[:12]) for p in ps] == [(12, "./a.tex", "LaTeX hooks "), (9, "./cap.tex", "Undefined co")]


def test_el_registro_de_una_corrida_toma_la_ultima_pasada_y_los_errores_de_biber():
    """El --log de main.sh lleva las tres pasadas: los «Citation undefined» de la primera no son problemas; los de Biber sí."""
    pasada = "This is LuaHBTeX, Version 1.18.0\n(./a.tex\nLaTeX Warning: Citation `k' on page 1 undefined on input line 5.\n)\n"
    ultima = "This is LuaHBTeX, Version 1.18.0\n(./a.tex\nLaTeX Warning: Reference `fig:x' on page 1 undefined on input line 9.\n)\n"
    biber = "INFO - This is Biber 2.20\nERROR - Cannot find 'referencias.bib'!\nWARN - Duplicate entry key: 'k'\n"
    ps = svc.problemas_de_registro(pasada + biber + pasada + ultima)
    assert [(p.nivel, p.mensaje[:22], p.linea) for p in ps] == [("error", "Biber: Cannot find 're", None), ("aviso", "Biber: Duplicate entry", None),
                                                                 ("aviso", "Reference `fig:x' on p", 9)]
    assert svc.ultima_pasada("sin banner") == "sin banner"


def test_la_orden_es_la_de_la_cli(tmp_path):
    o = Opciones(tmp_path / "a.tex", motor="lualatex", pasadas=3, bibliografia="biber", indice=True,
                 salida=str(tmp_path / "pdf"), log=tmp_path / "a.log")
    argv = o.orden()
    assert argv[1].endswith("script_compilar_latex/main.sh") and argv[-1].endswith("a.tex")
    for parte in ("-e", "lualatex", "-p", "3", "--biber", "-i", "-o", "--log"):
        assert parte in argv
    assert "-n" in o.orden(simular=True) and "-c" in o.orden(limpiar=True)
    assert o.pdf() == tmp_path / "pdf" / "a.pdf"


def test_motor_declarado_y_efectivo(tmp_path):
    a = tmp_path / "a.tex"
    a.write_text("% !TEX program = pdflatex\n\\documentclass{article}\n", encoding="utf-8")
    b = tmp_path / "b.tex"
    b.write_text("\\documentclass{article}\n", encoding="utf-8")
    assert svc.motor_declarado(a) == "pdflatex" and svc.motor_efectivo(a) == "pdflatex" and svc.motor_efectivo(a, "lualatex") == "lualatex"
    assert svc.motor_declarado(b) == "" and svc.motor_efectivo(b) == "lualatex"
    assert svc.motor_declarado(tmp_path / "no-existe.tex") == ""


def test_extensiones_auxiliares_salen_de_config_sh():
    exts = svc.extensiones_auxiliares()
    assert "aux" in exts and "log" in exts and "run.xml" in exts and "synctex.gz" in exts
    assert "tex" not in exts and "pdf" not in exts and "bib" not in exts


def test_auxiliares_y_salidas_como_la_cli(tmp_path):
    tex = tmp_path / "doc.tex"
    tex.write_text("\\documentclass{article}\\begin{document}x\\end{document}\n", encoding="utf-8")
    for nombre in ("doc.aux", "doc.log", "doc.run.xml", "doc.pdf", "doc.bib", "cap.aux", "otro.aux"):
        (tmp_path / nombre).write_text("x\n", encoding="utf-8")
    (tmp_path / "doc.aux").write_text("\\relax\n\\@input{cap.aux}\n\\@input{../fuera.aux}\n", encoding="utf-8")
    nombres = [p.name for p in svc.auxiliares_de(tex)]
    assert nombres == ["doc.aux", "doc.log", "doc.run.xml", "cap.aux"]          # ni el .bib, ni el PDF, ni otro.aux, ni ../fuera.aux
    salidas = svc.salidas_de(tex)
    assert salidas[0]["tipo"] == "PDF" and salidas[0]["nombre"] == "doc.pdf" and [s["tipo"] for s in salidas[1:]] == ["auxiliar"] * 4
    assert svc.pdf_de(tex) == tmp_path / "doc.pdf" and svc.pdf_de(tex, "build") == tmp_path / "build" / "doc.pdf"
    # lo que la CLI listaría con -c -n coincide
    r = subprocess.run(["bash", str(REPO / "script_compilar_latex" / "main.sh"), "-c", "-n", str(tex)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    for nombre in nombres:
        assert nombre in r.stdout
    assert "otro.aux" not in r.stdout


def test_estado_leido_del_disco(tmp_path):
    tex = tmp_path / "doc.tex"
    tex.write_text("x\n", encoding="utf-8")
    assert svc.estado_de(tex).clave == "sin_compilar"
    assert svc.estado_de(tex, en_curso=True).clave == "compilando"
    # un .log del motor con un error junto al .tex: con errores
    (tmp_path / "doc.log").write_text("(./doc.tex\n! Undefined control sequence.\nl.3 \\x\n)\n", encoding="utf-8")
    e = svc.estado_de(tex)
    assert e.clave == "errores" and e.errores == 1 and e.origen.endswith("doc.log")
    (tmp_path / "doc.log").unlink()
    # PDF más nuevo que el .tex, sin problemas: compilado; más viejo: desactualizado
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    os.utime(tex, (time.time() - 100, time.time() - 100))
    assert svc.estado_de(tex).clave == "compilado"
    os.utime(pdf, (time.time() - 200, time.time() - 200))
    assert svc.estado_de(tex).clave == "desactualizado"
    # el registro de la ventana con avisos, más reciente que el PDF: con avisos
    os.utime(pdf, None)
    registro = tmp_path / "cache" / "x.log"
    registro.parent.mkdir()
    registro.write_text("(./doc.tex\nLaTeX Warning: Reference `a' on page 1 undefined on input line 3.\n)\n", encoding="utf-8")
    e = svc.estado_de(tex, registro)
    assert e.clave == "avisos" and e.avisos == 1 and e.texto == "Con avisos" and e.nivel == "neutro"
    assert svc.registro_de(tex, tmp_path / "cache").parent == tmp_path / "cache" / "registros"
    assert svc.registro_de(tex, tmp_path / "cache").name.endswith("-doc.log")


def test_progreso_de_linea_y_tamanos():
    assert svc.progreso_de_linea("▶  Pasada 1/3 con lualatex...") == (0, "pasada 1 de 3")
    assert svc.progreso_de_linea("▶  Pasada 3/3 con lualatex...") == (66, "pasada 3 de 3")
    assert svc.progreso_de_linea("otra cosa") is None
    assert svc.tamano_legible(512) == "512 B" and svc.tamano_legible(2048) == "2.0 KB"


def test_documentos_en_solo_los_tex_de_la_carpeta(tmp_path):
    copiar_ejemplo(tmp_path)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "otro.tex").write_text("x", encoding="utf-8")
    assert [p.name for p in svc.documentos_en(tmp_path)] == ["articulo.tex", "con-error.tex"]
    assert svc.documentos_en(tmp_path / "no-existe") == []


@requiere_lualatex
def test_la_cli_compila_el_ejemplo_y_el_registro_se_lee(tmp_path):
    """El documento de ejemplo del repo compila con la CLI (LuaLaTeX + Biber si hay biber) fuera del repo, y del
    registro salen el aviso de la referencia y el aviso tipográfico, con el archivo del documento."""
    import shutil
    carpeta = copiar_ejemplo(tmp_path / "doc")
    tex = carpeta / "articulo.tex"
    registro = tmp_path / "registro.log"
    bib = "biber" if shutil.which("biber") else "ninguna"
    argv = Opciones(tex, motor="lualatex", bibliografia=bib, log=registro).orden()
    r = subprocess.run(argv, cwd=carpeta, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-1000:]
    assert (carpeta / "articulo.pdf").is_file() and not (carpeta / "articulo.aux").exists()     # la CLI limpia al terminar bien
    ps = leer_log(registro.read_text(encoding="utf-8", errors="replace"))
    assert not [p for p in ps if p.nivel == "error"], [p.mensaje for p in ps]
    assert any(p.nivel == "aviso" and "fig:modelo" in p.mensaje and p.linea == 17 and p.archivo == "./articulo.tex" for p in ps), [(p.nivel, p.mensaje, p.linea, p.archivo) for p in ps]
    assert any(p.nivel == "tipografia" for p in ps)
    estado = svc.estado_de(tex, registro)
    assert estado.clave == "avisos" and estado.errores == 0
    # la lectura del PDF
    info = svc.info_pdf(carpeta / "articulo.pdf")
    assert info["existe"] and info["bytes"] > 1000 and info["tamano"].endswith("KB")
