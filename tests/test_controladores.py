"""tests/test_controladores.py — los controladores de la reingeniería en proceso (sin QML) sobre el árbol de muestra
propio copiado a una carpeta temporal, con `WRITING_DIR` y `DESPACHO_DIR` apuntando a temporales (nunca a las
carpetas del autor): ajustes (carpetas de trabajo), proyectos (detección en tarea, categorías, el abierto, estructura,
autocompletado), editor (leer, guardar solo con orden, cambio externo, buscar y reemplazar), compilación (real, cola,
problemas explicados, limpiar sin tocar fuentes, dependencias), visor (páginas, SyncTeX) y las órdenes de escritorio.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from conftest import copiar_muestra, requiere_binding, requiere_biber, requiere_lualatex

from latex_app import modelos as mod  # noqa: E402
from latex_app.controladores import editor as ed  # noqa: E402


# ---------------------------------------------------------------------------------------------------- sin Qt

def test_fila_historial():
    h = mod.fila_historial({"tex": "/x/doc.tex", "ok": False, "segundos": 2.5, "detalle": "1 error(es)", "cuando": "2026-11-02 10:00"})
    assert h["nombre"] == "doc.tex" and h["resultado"] == "Falló" and h["nivel"] == "negativo" and h["duracion"] == "2.5 s"


def test_buscar_y_reemplazar_con_expresiones_regulares():
    texto = "\\section{Uno}\n\\section{Dos}\n\\subsection{Tres}\n"
    assert ed.buscar(texto, "section") == [[1, 8], [15, 22], [32, 39]]
    assert ed.buscar(texto, "section", palabra=True) == [[1, 8], [15, 22]]
    assert ed.buscar(texto, "SECTION", mayusculas=True) == []
    assert ed.buscar(texto, r"\\section\{(\w+)\}", regex=True) == [[0, 13], [14, 27]]
    cambios = ed.reemplazos(texto, r"\\section\{(\w+)\}", r"\\chapter{\1}", regex=True)
    assert cambios == [[14, 27, "\\chapter{Dos}"], [0, 13, "\\chapter{Uno}"]]          # del último al primero
    assert ed.reemplazos(texto, "Dos", "2", solo_desde=0) == [[23, 26, "2"]]


def test_posiciones_en_utf16_como_qml():
    texto = "𝔸 β x"                                   # 𝔸 ocupa dos unidades de UTF-16
    assert ed.buscar(texto, "x") == [[5, 6]]
    assert ed.reemplazos(texto, "β", "b") == [[3, 4, "b"]]


def test_definicion_de_resaltado():
    assert ed.definicion_de("/a/x.tex") == "LaTeX" and ed.definicion_de("/a/r.bib") == "BibTeX"
    assert ed.definicion_de("/a/latexmkrc") == "Perl" and ed.definicion_de("/a/proyecto.yaml") == "YAML"


# ---------------------------------------------------------------------------------------------------- con Qt

def _esperar(app, condicion, segundos=300):
    inicio = time.monotonic()
    while condicion() and time.monotonic() - inicio < segundos:
        app.processEvents()
        time.sleep(0.03)
    for _ in range(5):
        app.processEvents()


@pytest.fixture
def piezas(app, tmp_path, monkeypatch):
    """Los controladores como los arma `aplicacion.construir`, sin QML, sobre la muestra; QSettings y caché en temporal."""
    from gui_comun.consola import Consola
    from gui_comun.qt import QSettings
    from gui_comun.tareas import Tareas
    from latex_app.controladores.ajustes import Ajustes
    from latex_app.controladores.compilacion import Compilacion
    from latex_app.controladores.editor import Editor
    from latex_app.controladores.historial import Historial
    from latex_app.controladores.proyectos import Proyectos
    from latex_app.controladores.visor import Visor
    QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, str(tmp_path / "config"))
    QSettings().clear()
    muestra = copiar_muestra(tmp_path / "escritura")
    (tmp_path / "despacho").mkdir()
    monkeypatch.setenv("WRITING_DIR", str(muestra))
    monkeypatch.setenv("DESPACHO_DIR", str(tmp_path / "despacho"))
    consola = Consola()
    tareas = Tareas(consola)
    ajustes = Ajustes()
    historial = Historial(consola)
    proyectos = Proyectos(ajustes, historial, consola, tareas, cache=tmp_path / "cache")
    editor = Editor(consola)
    compilacion = Compilacion(proyectos, historial, ajustes, consola, tareas)
    visor = Visor(cache=tmp_path / "cache")
    p = dict(consola=consola, tareas=tareas, ajustes=ajustes, historial=historial, proyectos=proyectos, editor=editor,
             compilacion=compilacion, visor=visor, muestra=muestra, tmp=tmp_path)
    yield p
    tareas.esperar()
    visor.apagar()
    editor.soltar()
    app.processEvents()


@requiere_binding
def test_carpetas_de_trabajo_por_omision_y_del_usuario(app, piezas, tmp_path):
    a, muestra = piezas["ajustes"], piezas["muestra"]
    filas = a.carpetas
    assert [(f["nombre"], f["ruta"], f["activa"]) for f in filas] == [("Escritura", str(muestra), True), ("Despacho", str(tmp_path / "despacho"), True)]
    otra = tmp_path / "otra"
    otra.mkdir()
    assert a.anadirCarpeta(str(otra)) == "" and a.anadirCarpeta(str(tmp_path / "no-hay")).startswith("No es una carpeta")
    assert [r for _n, r in a.raices()] == [muestra, tmp_path / "despacho", otra]
    a.activarCarpeta(str(tmp_path / "despacho"), False)
    assert tmp_path / "despacho" not in [r for _n, r in a.raices()]
    a.quitarCarpeta(str(otra))
    assert [r for _n, r in a.raices()] == [muestra]
    a.profundidad = 99
    assert a.profundidad == 12


@requiere_binding
def test_deteccion_en_tarea_categorias_y_filtro(app, piezas):
    p = piezas["proyectos"]
    p.detectar()
    assert p.enDeteccion
    _esperar(app, lambda: p.enDeteccion)
    assert p.total == 6 and p.detectado
    categorias = {c["nombre"]: c["contador"] for c in p.categorias}
    assert categorias == {"Todas": 6, "Recientes": 0, "Escritura académica": 1, "Tesis y trabajos de investigación": 1,
                          "Pruebas y plantillas": 1, "Otros proyectos": 3}             # ninguna categoría vacía
    p.fijarCategoria("Otros proyectos")
    assert p.modelo.filas == 3
    p.fijarCategoria("Todas")
    p.modelo.filtrar("tesis")
    assert p.modelo.filas == 1
    ruta = p.rutaDeFila(0)
    d = p.datos(ruta)
    assert d["nombre"] == "tesis-multiarchivo/principal.tex" and d["compilador_texto"] == "script_compilar_latex" and "main.sh -k -e lualatex --biber" in d["orden"]
    assert p.recuento["sin_compilar"] == 6


@requiere_binding
def test_abrir_un_capitulo_abre_su_proyecto_con_estructura_y_autocompletado(app, piezas):
    p, muestra = piezas["proyectos"], piezas["muestra"]
    p.detectar_ya()
    assert p.abrir(str(muestra / "tesis-multiarchivo" / "capitulos" / "metodo.tex")) == ""
    assert p.hayAbierto and p.principal.endswith("tesis-multiarchivo/principal.tex")
    tipos = [f["tipo"] for f in p.archivos.todas()]
    assert tipos == ["principal", "incluido", "incluido", "bibliografía", "configuración"]
    assert p.esquema.filas >= 7 and p.nEtiquetas >= 6 and p.nClaves == 2
    r = p.completar("véase la tabla~\\ref{tab")
    assert r["tipo"] == "etiqueta" and r["elementos"][0]["texto"] == "tab:variables"
    assert [x["texto"] for x in p.completar("\\cite{kn")["elementos"]] == ["knuth1984"]
    assert str(muestra / "tesis-multiarchivo" / "principal.tex") in piezas["historial"].recientes()
    assert p.abrir(str(muestra / "no-es-tex.txt")).startswith("No es un documento LaTeX")


@requiere_binding
def test_editor_guarda_solo_con_orden_y_respeta_cambios_externos(app, piezas):
    e, muestra = piezas["editor"], piezas["muestra"]
    ruta = str(muestra / "con-error" / "roto.tex")
    original = Path(ruta).read_text()
    assert e.abrir(ruta) == 0 and e.actual == ruta
    texto = e.leer(ruta)
    assert texto == original and Path(ruta).read_text() == original        # abrir y leer no escriben
    e.marcarModificado(ruta, True)
    assert e.hayModificados and e.modificados == [ruta]
    assert e.guardar(ruta, texto.replace("está bien", "sigue bien"), False) == ""
    assert "sigue bien" in Path(ruta).read_text() and not e.hayModificados
    time.sleep(0.02)
    Path(ruta).write_text(original + "% de fuera\n")                         # otro programa lo cambia
    assert e.cambioEnDisco(ruta)
    assert e.guardar(ruta, "lo mío", False) == "externo" and "de fuera" in Path(ruta).read_text()
    assert e.guardar(ruta, "lo mío", True) == "" and Path(ruta).read_text() == "lo mío"
    e.cerrar(ruta)
    assert e.abiertos.filas == 0 and e.actual == ""


@requiere_binding
def test_guardar_como_no_toca_el_original(app, piezas, tmp_path):
    e = piezas["editor"]
    original = tmp_path / "a.tex"
    original.write_text("hola\n")
    e.abrir(str(original))
    e.leer(str(original))
    nueva = tmp_path / "b.tex"
    assert e.guardarComo(str(original), str(nueva), "hola, otra\n") == ""
    assert original.read_text() == "hola\n" and nueva.read_text() == "hola, otra\n"
    assert [f["ruta"] for f in e.abiertos.todas()] == [str(nueva)] and e.actual == str(nueva)
    assert e.guardar(str(nueva), "tres\n", False) == "" and nueva.read_text() == "tres\n"


@requiere_binding
def test_editor_conserva_los_finales_de_linea_de_windows(app, piezas, tmp_path):
    e = piezas["editor"]
    f = tmp_path / "w.tex"
    f.write_bytes(b"a\r\nb\r\n")
    e.abrir(str(f))
    assert e.leer(str(f)) == "a\nb\n"
    assert e.guardar(str(f), "a\nc\n", False) == "" and f.read_bytes() == b"a\r\nc\r\n"


@requiere_binding
@requiere_biber
def test_compila_el_proyecto_abierto_y_lo_muestra(app, piezas):
    p, c, v, muestra = piezas["proyectos"], piezas["compilacion"], piezas["visor"], piezas["muestra"]
    p.detectar_ya()
    p.abrir(str(muestra / "tesis-multiarchivo" / "principal.tex"))
    fuentes = {f: Path(f).read_bytes() for f in p.proyecto_abierto().fuentes()}
    terminadas = []
    c.terminada.connect(lambda r, ok: terminadas.append((r, ok)))
    assert c.compilar()
    _esperar(app, lambda: c.enCurso)
    assert terminadas == [(p.principal, True)]
    assert {f: Path(f).read_bytes() for f in fuentes} == fuentes                # la compilación no toca las fuentes
    assert p.abierto["estado"] in ("Compilado", "Con avisos") and p.abierto["synctex"]
    assert c.nErrores == 0 and c.origenRegistro.endswith(".log")
    assert piezas["historial"].ultima_de(p.principal)["ok"] is True
    pdf = p.proyecto_abierto().pdf
    v.abrir(pdf, "")
    assert v.total == 5 and v.haySynctex
    assert v.renderizar_ya(1, 30).endswith(".png") and v.paginas.fila(0)["imagen"].startswith("file://")
    marcas = []
    v.marcar.connect(lambda *a: marcas.append(a))
    assert v.desdeCodigo(str(muestra / "tesis-multiarchivo" / "capitulos" / "metodo.tex"), 4, 0)
    assert marcas and marcas[0][0] >= 3
    vueltas = []
    v.irACodigo.connect(lambda archivo, linea: vueltas.append((Path(archivo).name, linea)))
    _pag, x, y, ancho, alto = marcas[0]
    assert v.haciaCodigo(marcas[0][0], x + 2, y + alto / 2) and vueltas[0][0] == "metodo.tex"
    # limpiar: la lista no lleva fuentes ni el PDF, y después las fuentes siguen intactas
    lista = c.auxiliaresParaLimpiar("")
    assert lista and not any(x.endswith((".tex", ".bib", ".pdf")) for x in lista)
    assert c.limpiar("")
    _esperar(app, lambda: c.enCurso)
    assert {f: Path(f).read_bytes() for f in fuentes} == fuentes and Path(pdf).is_file()
    assert not (muestra / "tesis-multiarchivo" / "principal.synctex.gz").exists()


@requiere_binding
@requiere_lualatex
def test_el_error_se_explica_y_f8_va_a_la_linea(app, piezas):
    p, c, muestra = piezas["proyectos"], piezas["compilacion"], piezas["muestra"]
    p.detectar_ya()
    p.abrir(str(muestra / "con-error" / "roto.tex"))
    c.compilar()
    _esperar(app, lambda: c.enCurso)
    assert c.nErrores == 1
    problema = c.problema(0)
    assert problema["titulo"] == "Orden no definida" and problema["linea"] == 5 and problema["causa"] and problema["accion"]
    assert problema["archivo"].endswith("roto.tex") and "comandoquenoexiste" in problema["detalle"]
    saltos = []
    c.irA.connect(lambda archivo, linea: saltos.append((Path(archivo).name, linea)))
    c.siguiente()
    assert saltos == [("roto.tex", 5)]
    assert p.abierto["estado"] == "Con errores"


@requiere_binding
@requiere_lualatex
def test_cola_de_varios_proyectos_cada_uno_con_su_compilador(app, piezas):
    p, c, muestra = piezas["proyectos"], piezas["compilacion"], piezas["muestra"]
    p.detectar_ya()
    rutas = [str((muestra / r).resolve()) for r in ("marco/informes/informe-anual/informe.tex", "con-error/roto.tex", "con-latexmkrc/nota.tex")]
    avisos = []
    c.aviso.connect(lambda t, n: avisos.append((t, n)))
    assert c.encolar(rutas) == 3 and c.enCurso and c.enCola == 2
    _esperar(app, lambda: c.enCurso or c.enCola)
    estados = {Path(f["ruta"]).name: f["estado"] for f in c.cola.todas()}
    assert estados == {"informe.tex": "compiló", "roto.tex": "falló", "nota.tex": "compiló"}
    assert len([a for a in avisos if a[0].startswith("Cola terminada")]) == 1             # un solo aviso al final
    assert (muestra / "marco" / "informes" / "informe-anual" / ".build" / "informe.log").is_file()
    assert p.datos(rutas[0])["estado"] == "Compilado"


@requiere_binding
def test_revision_de_dependencias_va_a_problemas(app, piezas, tmp_path):
    p, c = piezas["proyectos"], piezas["compilacion"]
    raro = piezas["muestra"] / "raro"
    raro.mkdir()
    (raro / "d.tex").write_text("\\documentclass{article}\n\\usepackage{paquetequenoexiste}\n\\begin{document}\\input{falta}\\end{document}\n")
    p.detectar_ya()
    p.abrir(str(raro / "d.tex"))
    c.revisarDependencias("")
    _esperar(app, lambda: piezas["tareas"].activa)
    mensajes = [c.problema(i)["mensaje"] for i in range(c.problemas.filas)]
    assert "No existe «falta»" in mensajes and c.origenRegistro == "revisión de dependencias"
