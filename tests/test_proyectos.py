"""tests/test_proyectos.py — la reingeniería sin Qt (2026-11-02): detección de proyectos (R1–R6) sobre el árbol de muestra
propio (studio/ejemplo/proyectos/, copiado a una carpeta temporal), la estructura y el autocompletado (R12), los
errores presentables y la revisión de dependencias (R9, R16), las recetas por proyecto (R5, R8), el visor con
`pdftoppm` y su caché acotada (R10, R11) y SyncTeX real (`synctex view` y `synctex edit`) sobre una compilación real.

Ninguna prueba toca documentos reales: solo la muestra en un temporal.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from conftest import copiar_muestra, requiere_biber, requiere_lualatex

from latex_app import compilador as svc  # noqa: E402
from latex_app import diagnostico, estructura, visor  # noqa: E402
from latex_app import proyectos as pr  # noqa: E402

requiere_poppler = pytest.mark.skipif(not (shutil.which("pdftoppm") and shutil.which("pdfinfo")), reason="falta poppler")
requiere_synctex = pytest.mark.skipif(not shutil.which("synctex"), reason="falta synctex")
requiere_latexmk = pytest.mark.skipif(not shutil.which("latexmk"), reason="falta latexmk")


@pytest.fixture
def muestra(tmp_path) -> Path:
    return copiar_muestra(tmp_path / "muestra")


def _por_nombre(proyectos) -> dict:
    return {p.nombre: p for p in proyectos}


def _compilar(proyecto, que="compilar", registro=None) -> int:
    codigo = 0
    for paso in svc.receta(proyecto, que, registro):
        env = {**os.environ, **paso.entorno, "NO_COLOR": "1"}
        r = subprocess.run(paso.argv, cwd=paso.cwd, env=env, capture_output=True, text=True, timeout=240)
        codigo = r.returncode
        if codigo:
            break
    return codigo


# ---------------------------------------------------------------------------------------------------- detección

def test_un_proyecto_por_principal_y_los_incluidos_no_son_proyectos(muestra):
    ps = _por_nombre(pr.detectar([muestra]))
    assert set(ps) == {"principal.tex", "articulo.tex", "roto.tex", "nota.tex", "informe.tex", "caso.tex"}
    tesis = ps["principal.tex"]
    assert [Path(a).name for a in tesis.archivos] == ["introduccion.tex", "metodo.tex"]
    assert [Path(b).name for b in tesis.bibs] == ["referencias.bib"]
    assert tesis.no_encontrados == [] and tesis.clase == "report"
    assert tesis.titulo == "Una tesis de muestra"
    assert str(muestra / "tesis-multiarchivo" / "proyecto.yaml") in tesis.configuracion


def test_motor_bibliografia_y_compilador_segun_el_proyecto(muestra):
    ps = _por_nombre(pr.detectar([muestra]))
    t, a, n, i = ps["principal.tex"], ps["articulo.tex"], ps["nota.tex"], ps["informe.tex"]
    assert (t.motor, t.motor_origen, t.bibliografia, t.compilador) == ("lualatex", "por omisión", "biber", "main.sh")
    assert (a.motor, a.motor_origen, a.bibliografia, a.compilador) == ("lualatex", "comentario mágico", "bibtex", "main.sh")
    assert (n.motor, n.motor_origen, n.compilador) == ("lualatex", "latexmkrc", "latexmk")
    assert (i.compilador, i.motor, i.motor_origen, i.carpeta_aux) == ("marco", "lualatex", "marco", ".build")
    assert i.marco == str((muestra / "marco").resolve())
    assert t.texto_motor() == "LuaLaTeX + Biber" and a.texto_motor() == "LuaLaTeX + BibTeX"


def test_motor_declarado_por_comentario_magico_se_respeta(tmp_path):
    (tmp_path / "viejo.tex").write_text("% !TEX program = pdflatex\n\\documentclass{article}\n\\begin{document}x\\end{document}\n")
    (tmp_path / "arara.tex").write_text("% arara: xelatex\n\\documentclass{article}\n\\begin{document}x\\end{document}\n")
    ps = _por_nombre(pr.detectar([tmp_path]))
    assert (ps["viejo.tex"].motor, ps["viejo.tex"].motor_origen) == ("pdflatex", "comentario mágico")
    assert (ps["arara.tex"].motor, ps["arara.tex"].motor_origen) == ("xelatex", "arara")
    assert ps["viejo.tex"].bibliografia == "ninguna"


def test_tex_root_subfiles_y_comentados_no_son_proyectos(tmp_path):
    (tmp_path / "main.tex").write_text("\\documentclass{article}\n\\begin{document}\\subfile{parte}\\end{document}\n")
    (tmp_path / "parte.tex").write_text("\\documentclass[main.tex]{subfiles}\n\\begin{document}parte\\end{document}\n")
    (tmp_path / "cap.tex").write_text("% !TEX root = main.tex\n\\section{Cap}\n")
    (tmp_path / "suelto.tex").write_text("% \\documentclass{article}\n\\section{nada}\n")
    ps = pr.detectar([tmp_path])
    assert [p.nombre for p in ps] == ["main.tex"]
    assert pr.proyecto_de(tmp_path / "cap.tex").nombre == "main.tex"        # Ctrl+O sobre un capítulo abre su raíz


def test_categorias_solo_con_informacion(muestra):
    ps = _por_nombre(pr.detectar([muestra]))
    assert ps["principal.tex"].categoria == "Tesis y trabajos de investigación"
    assert ps["principal.tex"].categoria_motivo.startswith("proyecto.yaml")
    assert ps["caso.tex"].categoria == "Pruebas y plantillas"
    for nombre in ("articulo.tex", "roto.tex", "nota.tex"):
        assert ps[nombre].categoria == "Otros proyectos", nombre        # article sin más: sin información → no se inventa
    assert (ps["informe.tex"].categoria, ps["informe.tex"].categoria_motivo) == ("Escritura académica", "carpeta «informes»")
    assert pr.categorizar(Path("/x/theses/t/plan.tex"), Path("/x"), "")[0] == "Tesis y trabajos de investigación"
    assert pr.categorizar(Path("/x/a/oficio.tex"), Path("/x"), "oficio")[0] == "Documentos institucionales"
    assert pr.categorizar(Path("/x/a/d.tex"), Path("/x"), "dictamen")[0] == "Documentos legislativos"
    assert pr.categorizar(Path("/x/a/i.tex"), Path("/x"), "informe", en_despacho=True)[0] == "Documentos institucionales"


def test_profundidad_y_carpetas_saltadas(tmp_path):
    hondo = tmp_path / "a" / "b" / "c"
    hondo.mkdir(parents=True)
    (hondo / "h.tex").write_text("\\documentclass{article}\n\\begin{document}x\\end{document}\n")
    (tmp_path / "_site").mkdir()
    (tmp_path / "_site" / "s.tex").write_text("\\documentclass{article}\n")
    (tmp_path / ".oculta").mkdir()
    (tmp_path / ".oculta" / "o.tex").write_text("\\documentclass{article}\n")
    assert [p.nombre for p in pr.detectar([tmp_path], profundidad=3)] == ["h.tex"]
    assert pr.detectar([tmp_path], profundidad=2) == []


def test_la_cache_no_vuelve_a_leer_lo_que_no_cambio(muestra, tmp_path):
    ruta = tmp_path / "cache" / "proyectos.json"
    c1 = pr.Cache(ruta)
    pr.detectar([muestra], cache=c1)
    assert c1.leidos == 8 and ruta.is_file()              # los ocho .tex de la muestra
    c2 = pr.Cache(ruta)
    pr.detectar([muestra], cache=c2)
    assert c2.leidos == 0
    cap = muestra / "tesis-multiarchivo" / "capitulos" / "metodo.tex"
    time.sleep(0.01)
    cap.write_text(cap.read_text() + "\n% cambio\n")
    c3 = pr.Cache(ruta)
    pr.detectar([muestra], cache=c3)
    assert c3.leidos == 1


def test_detectar_informa_progreso_y_se_cancela(muestra):
    avances = []
    pr.detectar([muestra], progreso=lambda p, t: avances.append(p))
    assert avances and avances[-1] == 100
    assert pr.detectar([muestra], cancelado=lambda: True) == []


def test_estado_del_disco_sin_compilar_y_desactualizado(muestra):
    ps = _por_nombre(pr.detectar([muestra]))
    assert ps["principal.tex"].estado == "sin_compilar"
    tesis = ps["principal.tex"]
    pdf = muestra / "tesis-multiarchivo" / "principal.pdf"
    pdf.write_bytes(b"%PDF-1.5\n")
    # Anterior a la fuente más vieja del proyecto: la muestra se copia con sus fechas, así que «hace una hora» deja de
    # ser anterior a los capítulos unas horas después de escribirlos (la prueba fallaba según la hora del día).
    fuentes = [p for p in (muestra / "tesis-multiarchivo").rglob("*") if p.is_file() and p != pdf]
    viejo = min(p.stat().st_mtime for p in fuentes) - 3600
    os.utime(pdf, (viejo, viejo))
    pr.leer_estado(tesis, pr.Cache())
    assert tesis.estado == "desactualizado"          # un capítulo es más nuevo que el PDF


# ---------------------------------------------------------------------------------------------------- estructura

def test_esquema_sigue_los_input_en_orden(muestra):
    e = estructura.esquema(muestra / "tesis-multiarchivo" / "principal.tex")
    secciones = [(x["orden"], x["titulo"]) for x in e if x["tipo"] == "seccion"]
    assert secciones == [("chapter", "Introducción"), ("section", "Planteamiento"), ("chapter", "Método"),
                         ("section", "Datos"), ("section", "Estimación")]
    flotantes = [(x["tipo"], x["titulo"], x["etiqueta"]) for x in e if x["tipo"] in ("figura", "tabla")]
    assert flotantes == [("tabla", "Variables del modelo", "tab:variables"), ("figura", "Esquema de la estimación", "fig:esquema")]
    metodo = next(x for x in e if x["titulo"] == "Método")
    assert Path(metodo["archivo"]).name == "metodo.tex" and metodo["linea"] == 2


def test_etiquetas_claves_y_autocompletado(muestra):
    p = pr.detectar([muestra / "tesis-multiarchivo"])[0]
    etiquetas = estructura.etiquetas(p.fuentes())
    assert {e["nombre"] for e in etiquetas} >= {"cap:intro", "eq:modelo", "tab:variables", "fig:esquema"}
    claves = estructura.claves_bib(p.bibs)
    assert [c["nombre"] for c in claves] == ["knuth1984", "lamport1994"] and claves[0]["anio"] == "1984"
    r = estructura.completar("ver la tabla~\\ref{tab", etiquetas, claves)
    assert r["tipo"] == "etiqueta" and [x["texto"] for x in r["elementos"]] == ["tab:variables"]
    r = estructura.completar("como dice \\parencite{knuth1984, lam", etiquetas, claves)
    assert r["tipo"] == "cita" and r["prefijo"] == "lam" and r["elementos"][0]["texto"] == "lamport1994"
    r = estructura.completar("\\begin{ali", etiquetas, claves)
    assert r["tipo"] == "entorno" and "align" in [x["texto"] for x in r["elementos"]]
    r = estructura.completar("texto \\textb", etiquetas, claves)
    # una orden con argumentos lleva su firma y se inserta con sus llaves y el cursor en la primera
    assert r["tipo"] == "orden" and r["elementos"][0]["texto"] == "\\textbf{texto}"
    assert (r["elementos"][0]["insertar"], r["elementos"][0]["retroceso"]) == ("textbf{}", 1)
    frac = next(x for x in estructura.completar("\\fra", etiquetas, claves)["elementos"] if x["insertar"].startswith("frac"))
    assert (frac["insertar"], frac["retroceso"]) == ("frac{}{}", 3)
    assert next(x for x in estructura.completar("\\cent", etiquetas, claves)["elementos"])["retroceso"] == 0
    assert estructura.completar("texto normal", etiquetas, claves)["tipo"] == ""


def test_autocompletado_de_argumentos(muestra):
    """Los argumentos que se conocen: paquetes (los usados en el proyecto también), clases, estilos de BibTeX y los
    archivos del proyecto (\\input con extensión, \\include sin ella; imágenes; .bib)."""
    carpeta = muestra / "tesis-multiarchivo"
    (carpeta / "figuras").mkdir()
    (carpeta / "figuras" / "esquema.png").write_bytes(b"")
    (carpeta / ".build").mkdir()
    (carpeta / ".build" / "oculto.tex").write_text("")
    archivos = estructura.archivos_de(carpeta)
    assert "capitulos/metodo.tex" in archivos and "figuras/esquema.png" in archivos and "referencias.bib" in archivos
    assert not any(a.startswith(".build") for a in archivos)
    def textos(antes, **k):
        r = estructura.completar(antes, [], [], archivos=archivos, **k)
        return r["tipo"], [x["texto"] for x in r["elementos"]], [x["insertar"] for x in r["elementos"]]
    assert textos("\\usepackage[utf8]{amsm")[1] == ["amsmath"]
    assert textos("\\usepackage{mipaq", paquetes_extra=["mipaquete"])[1] == ["mipaquete"]
    assert textos("\\documentclass[12pt]{art")[1] == ["article"]
    assert textos("\\bibliographystyle{apa")[1] == ["apalike"]
    assert textos("\\includegraphics[width=\\linewidth]{esq")[1] == ["figuras/esquema.png"]
    assert textos("\\input{capitulos/met")[2] == ["capitulos/metodo.tex"]
    assert textos("\\include{capitulos/met")[2] == ["capitulos/metodo"]
    assert textos("\\addbibresource{")[1] == ["referencias.bib"]
    assert textos("\\bibliography{ref")[2] == ["referencias"]
    assert textos("\\usepackage{amsmath,amss")[1] == ["amssymb"]


def test_definiciones_del_proyecto_entran_al_autocompletado(tmp_path):
    (tmp_path / "m.tex").write_text("\\newcommand{\\miorden}{x}\n\\newtheorem{teorema}{Teorema}\n\\documentclass{article}\n")
    ordenes, entornos = estructura.definiciones([str(tmp_path / "m.tex")])
    assert ordenes == ["miorden"] and entornos == ["teorema"]
    assert estructura.completar("\\mio", [], [], ordenes)["elementos"][0]["texto"] == "\\miorden"


# ---------------------------------------------------------------------------------------------------- diagnóstico

@pytest.mark.parametrize("mensaje,titulo", [
    ("LaTeX Error: File `inexistente.sty' not found.", "Falta el paquete «inexistente.sty»"),
    ("LaTeX Error: File `oficio.cls' not found.", "Falta la clase «oficio.cls»"),
    ("Undefined control sequence.", "Orden no definida"),
    ("Reference `fig:x' on page 1 undefined", "Referencia indefinida «fig:x»"),
    ("Citation `knuth' on page 1 undefined", "Cita indefinida «knuth»"),
    ("Biber: Cannot find control file 'doc.bcf'! - Did latex run on this file?", "Biber sin .bcf"),
    ("Missing $ inserted.", "Falta un $ (modo matemático)"),
])
def test_errores_presentables(mensaje, titulo):
    e = diagnostico.explicar("error", mensaje)
    assert e["titulo"] == titulo and e["causa"] and e["accion"]


def test_un_mensaje_desconocido_no_inventa_causa():
    e = diagnostico.explicar("error", "Algo rarísimo que ninguna regla conoce. Más texto")
    assert e["titulo"] == "Algo rarísimo que ninguna regla conoce" and e["causa"] == ""


def test_revision_de_dependencias(tmp_path):
    (tmp_path / "d.tex").write_text("\\documentclass{article}\n\\usepackage{paquetequenoexiste}\n\\usepackage{amsmath}\n"
                                    "\\addbibresource{nohay.bib}\n\\begin{document}\\input{falta}\\end{document}\n")
    p = pr.detectar([tmp_path])[0]
    problemas = diagnostico.revisar(p)
    mensajes = [x["mensaje"] for x in problemas]
    assert "No existe «falta»" in mensajes
    assert "No se encuentra la bibliografía «nohay.bib»" in mensajes
    if shutil.which("kpsewhich"):
        assert "Falta el paquete «paquetequenoexiste.sty»" in mensajes
        assert not any("amsmath" in m for m in mensajes)


def test_la_clase_de_un_marco_se_busca_en_el_marco(muestra):
    informe = _por_nombre(pr.detectar([muestra]))["informe.tex"]
    assert not any("memoria" in x["mensaje"] for x in diagnostico.revisar(informe))


# ---------------------------------------------------------------------------------------------------- recetas

def test_indice_y_glosarios_se_detectan_del_proyecto(tmp_path):
    (tmp_path / "i.tex").write_text("\\documentclass{book}\n\\usepackage{makeidx}\n\\makeindex\n\\begin{document}x\\printindex\\end{document}\n")
    p = pr.detectar([tmp_path])[0]
    assert p.indice and not p.glosarios
    argv = svc.receta(p)[0].argv
    assert "-i" in argv and "-g" not in argv
    assert svc.receta(p, "borrador")[0].argv[-2] == "--draft"


def test_recetas_por_compilador(muestra, tmp_path):
    ps = _por_nombre(pr.detectar([muestra]))
    t = svc.receta(ps["principal.tex"], "compilar", tmp_path / "r.log")
    assert t[0].argv[:6] == ["bash", str(svc.CLI), "-k", "-e", "lualatex", "--biber"] and "--log" in t[0].argv
    assert svc.receta(ps["articulo.tex"])[0].argv[5] == "-b"
    assert [p.argv[2] for p in svc.receta(ps["principal.tex"], "reconstruir")][:1] == ["-c"]
    assert svc.receta(ps["nota.tex"])[0].argv[0] == "latexmk" and "-synctex=1" in svc.receta(ps["nota.tex"])[0].argv
    assert "-g" in svc.receta(ps["nota.tex"], "reconstruir")[0].argv
    marco = svc.receta(ps["informe.tex"], "reconstruir")
    assert [p.argv[2] for p in marco] == ["--clean", str(ps["informe.tex"].principal)]
    assert "main.sh -k -e lualatex --biber" in svc.orden_legible(t)
    entorno = svc.receta(ps["principal.tex"], rutas_tex=[str(muestra / "marco" / "classes")])[0].entorno
    assert entorno["TEXINPUTS"].startswith(".:" + str(muestra / "marco" / "classes") + "//")


# ---------------------------------------------------------------------------------------------------- compilación real

@requiere_biber
def test_compila_la_tesis_multiarchivo_con_biber_y_conserva_synctex(muestra, tmp_path):
    p = _por_nombre(pr.detectar([muestra]))["principal.tex"]
    registro = tmp_path / "registro.log"
    assert _compilar(p, registro=registro) == 0
    carpeta = muestra / "tesis-multiarchivo"
    assert (carpeta / "principal.pdf").is_file() and (carpeta / "principal.synctex.gz").is_file()
    pr.leer_estado(p, pr.Cache(), registro)
    assert p.estado in ("compilado", "avisos") and p.errores == 0 and p.synctex
    for fuente in p.fuentes():
        assert Path(fuente).read_text()                     # las fuentes siguen ahí, intactas


@requiere_lualatex
def test_el_proyecto_con_error_queda_con_errores_y_explicado(muestra, tmp_path):
    p = _por_nombre(pr.detectar([muestra]))["roto.tex"]
    registro = tmp_path / "roto.log"
    assert _compilar(p, registro=registro) != 0
    pr.leer_estado(p, pr.Cache(), registro)
    assert p.estado == "errores" and p.errores >= 1
    problema = svc.problemas_de_registro(svc.leer_registro(registro))[0]
    assert problema.linea == 5
    assert diagnostico.explicar(problema.nivel, problema.mensaje)["titulo"] == "Orden no definida"


@requiere_lualatex
def test_compila_con_el_compilador_del_marco(muestra):
    p = _por_nombre(pr.detectar([muestra]))["informe.tex"]
    assert _compilar(p) == 0
    carpeta = muestra / "marco" / "informes" / "informe-anual"
    assert (carpeta / "informe.pdf").is_file() and (carpeta / ".build" / "informe.log").is_file()
    pr.leer_estado(p, pr.Cache())
    assert p.estado == "compilado" and p.log.endswith(".build/informe.log") and p.auxiliares > 0
    assert _compilar(p, "limpiar") == 0 and not (carpeta / ".build").exists() and (carpeta / "informe.tex").is_file()


@requiere_lualatex
@requiere_latexmk
def test_compila_con_latexmk_si_hay_latexmkrc(muestra):
    p = _por_nombre(pr.detectar([muestra]))["nota.tex"]
    assert _compilar(p) == 0
    assert (muestra / "con-latexmkrc" / "nota.pdf").is_file() and (muestra / "con-latexmkrc" / "nota.synctex.gz").is_file()


@requiere_lualatex
def test_compila_con_bibtex_y_comentario_magico(muestra, tmp_path):
    p = _por_nombre(pr.detectar([muestra]))["articulo.tex"]
    registro = tmp_path / "a.log"
    assert _compilar(p, registro=registro) == 0
    assert (muestra / "articulo-bibtex" / "articulo.bbl").is_file()          # BibTeX corrió (y -k conservó el .bbl)
    assert "This is BibTeX" in registro.read_text(errors="replace")


# ---------------------------------------------------------------------------------------------------- visor y SyncTeX

@requiere_lualatex
@requiere_poppler
def test_visor_renderiza_por_demanda_y_poda_la_cache(muestra, tmp_path):
    p = _por_nombre(pr.detectar([muestra]))["roto.tex"]
    nota = _por_nombre(pr.detectar([muestra]))["nota.tex"]
    assert _compilar(nota) == 0
    pdf = Path(nota.carpeta) / "nota.pdf"
    tamanos = visor.paginas(pdf)
    assert len(tamanos) == 1 and tamanos[0][0] == pytest.approx(614.0, abs=30)
    cache = tmp_path / "cache"
    png = visor.renderizar(pdf, 1, 50, cache)
    assert png is not None and png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert visor.renderizar(pdf, 1, 50, cache) == png                     # de la caché
    assert visor.tamano_cache(cache) > 0
    assert visor.podar(cache, limite=0, conservar=visor.clave(pdf)) == 0   # el abierto no se borra
    assert visor.podar(cache, limite=0) > 0 and visor.tamano_cache(cache) == 0
    assert visor.paginas(Path(p.carpeta) / "no-hay.pdf") == []


@requiere_biber
@requiere_synctex
def test_synctex_real_ida_y_vuelta(muestra, tmp_path):
    p = _por_nombre(pr.detectar([muestra]))["principal.tex"]
    assert _compilar(p, registro=tmp_path / "r.log") == 0
    pdf = Path(p.carpeta) / "principal.pdf"
    metodo = Path(p.carpeta) / "capitulos" / "metodo.tex"
    destino = visor.hacia_pdf(pdf, metodo, 4)            # «Seguimos a \parencite{lamport1994}.»
    assert destino is not None and destino["pagina"] >= 3
    origen = visor.hacia_codigo(pdf, destino["pagina"], destino["x"] + 2, destino["y"] + destino["alto"] / 2)
    assert origen is not None and Path(origen["archivo"]).name == "metodo.tex" and abs(origen["linea"] - 4) <= 1
