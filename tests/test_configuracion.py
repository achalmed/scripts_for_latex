"""tests/test_configuracion.py — la configuración de documentos por el latex-studio.yml de su marco
(docs/configuracion-de-documentos.md): búsqueda del esquema, lectura, diferencia, escritura confirmada y el controlador.
Todo sobre un marco de muestra en un temporal; ningún documento real."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import requiere_binding
from latex_app import configuracion as cf

ESQUEMA = r"""
version: 1
marco: muestra
documentos:
  - nombre: Examen
    clases: [examen]
    secciones:
      - titulo: Datos
        campos:
          - {clave: curso, etiqueta: Curso, tipo: texto, destino: {orden: '\curso'}}
          - {clave: docente, etiqueta: Docente, tipo: texto, destino: {orden: '\docente'}}
          - {clave: titulo, etiqueta: Título, tipo: texto, destino: {orden: '\setmeta', clave: titulo, archivo: metadata.tex}}
      - titulo: Presentación
        campos:
          - {clave: nivel, etiqueta: Nivel, tipo: interruptor, omision: true, destino: {lista: '\configuracion', clave: nivel}}
          - {clave: puntaje, etiqueta: Puntaje, tipo: interruptor, omision: true, destino: {lista: '\configuracion', clave: puntaje}}
          - {clave: bn, etiqueta: Blanco y negro, tipo: interruptor, omision: false, destino: {opcion_clase: bn}}
          - {clave: tema, etiqueta: Tema, tipo: opcion, opciones_desde: {carpeta: temas, extension: .yml}, destino: {opcion_clase: tema}}
  - nombre: Otro
    generica: false
    secciones: []
"""

DOC = r"""% cabecera
\documentclass[tema=claro]{examen}
% \curso{comentado}
\curso{Matemáticas III}
\begin{document}
\curso{en el cuerpo: no cuenta}
\end{document}
"""


@pytest.fixture
def marco(tmp_path):
    raiz = tmp_path / "marco"
    (raiz / "config").mkdir(parents=True)
    (raiz / "config" / "latex-studio.yml").write_text(ESQUEMA, encoding="utf-8")
    (raiz / "config" / "temas").mkdir()
    for t in ("claro", "oscuro", "_base"):
        (raiz / "config" / "temas" / f"{t}.yml").write_text("{}\n")
    doc = raiz / "cursos" / "c" / "evaluaciones" / "e" / "e.tex"
    doc.parent.mkdir(parents=True)
    doc.write_text(DOC, encoding="utf-8")
    return doc


def test_busca_el_esquema_subiendo_y_lee_los_valores(marco):
    assert cf.buscar_esquema(marco).name == "latex-studio.yml"
    conf = cf.configuracion_de(marco)
    assert (conf.marco, conf.nombre, conf.clase) == ("muestra", "Examen", "examen")
    assert [s.titulo for s in conf.secciones] == ["Datos", "Presentación", "Documento"]   # más la genérica
    c = conf.campos()
    assert c["curso"].valor == "Matemáticas III"           # ni la comentada ni la del cuerpo
    assert c["docente"].valor == "" and c["nivel"].valor is True and c["bn"].valor is False
    assert c["tema"].valor == "claro" and c["tema"].opciones == ["claro", "oscuro"]     # sin los que empiezan por _
    assert c["titulo"].archivo == str(marco)               # sin metadata.tex, el principal


def test_diferencia_y_escritura_solo_del_preambulo(marco):
    conf = cf.configuracion_de(marco)
    cambios = cf.cambios(conf, {"curso": "Econometría", "docente": "Mg. Prueba", "nivel": False, "bn": True, "tema": "oscuro"})
    assert len(cambios) == 1 and "+\\docente{Mg. Prueba}" in cambios[0].diferencia()
    assert marco.read_text(encoding="utf-8") == DOC          # calcular no escribe
    cf.aplicar(cambios)
    texto = marco.read_text(encoding="utf-8")
    assert "\\documentclass[bn, tema=oscuro]{examen}" in texto or "\\documentclass[tema=oscuro, bn]{examen}" in texto
    assert "\\curso{Econometría}" in texto and "% \\curso{comentado}" in texto
    assert "\\curso{en el cuerpo: no cuenta}" in texto     # el cuerpo no se toca
    assert "\\configuracion{nivel=false}" in texto
    assert texto.index("\\docente{Mg. Prueba}") < texto.index("\\begin{document}")
    c = cf.configuracion_de(marco).campos()
    assert (c["nivel"].valor, c["bn"].valor, c["docente"].valor) == (False, True, "Mg. Prueba")


def test_volver_a_la_omision_limpia_y_vaciar_quita_la_linea(marco):
    conf = cf.configuracion_de(marco)
    cf.aplicar(cf.cambios(conf, {"nivel": False, "puntaje": False}))
    conf = cf.configuracion_de(marco)
    cf.aplicar(cf.cambios(conf, {"nivel": True, "puntaje": True, "curso": ""}))
    pre = marco.read_text(encoding="utf-8").split("\\begin{document}")[0]
    assert "\\configuracion" not in pre and "\n\\curso{" not in pre


def test_metadatos_en_su_archivo(marco):
    meta = marco.parent / "metadata.tex"
    meta.write_text("\\setmeta{titulo}{Viejo}\n", encoding="utf-8")
    conf = cf.configuracion_de(marco)
    assert conf.campos()["titulo"].valor == "Viejo"
    cambios = cf.cambios(conf, {"titulo": "Nuevo"})
    assert [c.archivo for c in cambios] == [meta]
    cf.aplicar(cambios)
    assert meta.read_text(encoding="utf-8") == "\\setmeta{titulo}{Nuevo}\n"


def test_no_escribe_si_el_archivo_cambio_entre_tanto(marco):
    cambios = cf.cambios(cf.configuracion_de(marco), {"docente": "X"})
    marco.write_text(DOC + "% editado fuera\n", encoding="utf-8")
    with pytest.raises(cf.ErrorEsquema):
        cf.aplicar(cambios)


def test_sin_esquema_solo_la_seccion_generica(tmp_path):
    doc = tmp_path / "suelto.tex"
    doc.write_text("\\documentclass[11pt]{article}\n\\title{Hola}\n\\begin{document}x\\end{document}\n", encoding="utf-8")
    conf = cf.configuracion_de(doc)
    assert conf.esquema is None and [s.titulo for s in conf.secciones] == ["Documento"]
    assert conf.campos()["_title"].valor == "Hola" and conf.campos()["_opciones"].valor == "11pt"
    cf.aplicar(cf.cambios(conf, {"_opciones": "12pt, a4paper", "_author": "Autor"}))
    texto = doc.read_text(encoding="utf-8")
    assert texto.startswith("\\documentclass[12pt, a4paper]{article}") and "\\author{Autor}" in texto


def test_un_esquema_mal_formado_dice_donde(tmp_path):
    (tmp_path / "latex-studio.yml").write_text("version: 1\ndocumentos:\n  - secciones:\n      - campos:\n          - {clave: x}\n")
    doc = tmp_path / "d.tex"
    doc.write_text("\\documentclass{article}\n")
    with pytest.raises(cf.ErrorEsquema, match="destino"):
        cf.configuracion_de(doc)


@requiere_binding
def test_controlador_pendientes_diferencia_y_aplicar(marco):
    from gui_comun.consola import Consola
    from latex_app.controladores.configuracion import ConfiguracionDocumento

    class Editor:
        def __init__(self):
            self.sucios = []

        def modificados(self):
            return self.sucios

    editor = Editor()
    c = ConfiguracionDocumento(Consola(), editor)
    assert c.abrir(str(marco)) == "" and c.nombre == "Examen" and c.pendientes == 0
    c.fijar("docente", "Mg. Prueba")
    c.fijar("curso", "Matemáticas III")              # igual al actual: no queda pendiente
    assert c.pendientes == 1 and "+\\docente{Mg. Prueba}" in c.diferencia()
    editor.sucios = [str(marco)]
    assert "sin guardar" in c.aplicar()              # no pisa el editor
    editor.sucios = []
    aplicados = []
    c.aplicado.connect(aplicados.append)
    assert c.aplicar() == "" and aplicados == [str(marco)] and c.pendientes == 0
    assert "\\docente{Mg. Prueba}" in marco.read_text(encoding="utf-8")
    assert c.abrir(str(marco.parent / "no-existe.tex")).startswith("No hay un documento")


def test_verificar_esquema_senala_lo_que_las_clases_no_definen(tmp_path):
    (tmp_path / "classes").mkdir()
    (tmp_path / "classes" / "examen.cls").write_text("\\newcommand{\\curso}[1]{}\n\\DeclareOption{bn}{}\n")
    (tmp_path / "config").mkdir()
    esquema = tmp_path / "config" / "latex-studio.yml"
    esquema.write_text(r"""
version: 1
documentos:
  - secciones:
      - titulo: S
        campos:
          - {clave: curso, tipo: texto, destino: {orden: '\curso'}}
          - {clave: titulo, tipo: texto, destino: {orden: '\title'}}
          - {clave: bn, tipo: interruptor, destino: {opcion_clase: bn}}
          - {clave: falta, tipo: texto, destino: {orden: '\noexiste'}}
          - {clave: curso, tipo: texto, destino: {orden: '\curso'}}
""", encoding="utf-8")
    problemas = cf.verificar_esquema(esquema)
    assert len(problemas) == 2
    assert any("\\noexiste no está definida" in p for p in problemas) and any("repetida" in p for p in problemas)


def test_documento_fuera_del_arbol_del_marco_halla_el_esquema_junto_a_su_clase(marco, tmp_path):
    """Los documentos que viven lejos de su marco (p. ej. en una carpeta de documentos aparte) encuentran el esquema
    por la clase, en las rutas de TeX extra o en los marcos detectados."""
    raiz = marco.parents[4]                       # …/marco
    (raiz / "classes").mkdir()
    (raiz / "classes" / "examen.cls").write_text("\\newcommand{\\curso}[1]{}\n")
    lejos = tmp_path / "otra" / "carpeta" / "doc.tex"
    lejos.parent.mkdir(parents=True)
    lejos.write_text(DOC, encoding="utf-8")
    assert cf.configuracion_de(lejos).esquema is None
    conf = cf.configuracion_de(lejos, rutas=[raiz])
    assert conf.marco == "muestra" and conf.campos()["curso"].valor == "Matemáticas III"
