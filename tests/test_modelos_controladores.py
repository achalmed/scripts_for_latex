"""tests/test_modelos_controladores.py — los modelos sin Qt y los controladores de la ventana en proceso (sin QML):
espacio, opciones, documentos (tablas, documento actual, problemas, salidas), corrida (simular, compilar de verdad con
lualatex si está, limpiar) e historial. Todo sobre el ejemplo copiado a una carpeta temporal.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from conftest import requiere_binding, requiere_lualatex

from latex_app import compilador as svc  # noqa: E402
from latex_app import modelos as mod  # noqa: E402


# --- modelos sin Qt ----------------------------------------------------------------------------------------------------

def test_fila_documento_y_contadores(tmp_path):
    tex = tmp_path / "a.tex"
    tex.write_text("% !TEX program = xelatex\n\\documentclass{article}\n", encoding="utf-8")
    f = mod.fila_documento(tex, svc.Estado("sin_compilar"))
    assert f["nombre"] == "a.tex" and f["estado"] == "Sin compilar" and f["nivel"] == "inactivo" and f["motor"] == "XeLaTeX (declarado)"
    assert f["pdf"] == "—" and f["icono"]["estado"] == "dialog-cancel" and f["crudo"]["estado"] == mod.ORDEN_ESTADO["sin_compilar"]
    assert mod.texto_motor(tex, "lualatex") == "LuaLaTeX"
    filas = [f, mod.fila_documento(tex, svc.Estado("errores", 2)), mod.fila_documento(tex, svc.Estado("avisos", 0, 1))]
    c = mod.contar(filas)
    assert c["total"] == 3 and c["sin_compilar"] == 1 and c["errores"] == 1
    assert mod.resumen_contadores(c) == "3 documentos · 1 con avisos · 1 con errores · 1 sin compilar"
    assert mod.resumen_contadores({"total": 1}) == "1 documento"


def test_filas_historial_y_problemas():
    h = mod.fila_historial({"tex": "/x/doc.tex", "ok": False, "segundos": 2.5, "detalle": "1 error(es)", "cuando": "2026-11-02 10:00"})
    assert h["nombre"] == "doc.tex" and h["resultado"] == "Falló" and h["nivel"] == "negativo" and h["duracion"] == "2.5 s" and h["carpeta"] == "/x"
    ps = mod.filas_problemas([svc.Problema("error", "Undefined", 4, "./a.tex"), svc.Problema("aviso", "Ref", None, "")])
    assert ps == [{"nivel": "error", "mensaje": "Undefined", "archivo": "./a.tex", "linea": 4, "detalle": ""},
                  {"nivel": "aviso", "mensaje": "Ref", "archivo": "", "linea": 0, "detalle": ""}]


# --- controladores -----------------------------------------------------------------------------------------------------

def _esperar(app, tareas, segundos=300):
    inicio = time.monotonic()
    while tareas.activa and time.monotonic() - inicio < segundos:
        app.processEvents()
        time.sleep(0.05)
    app.processEvents()


@pytest.fixture
def piezas(app, documentos, tmp_path):
    from gui_comun.consola import Consola
    from gui_comun.tareas import Tareas
    from latex_app.controladores.ajustes import Ajustes
    from latex_app.controladores.corrida import Corrida
    from latex_app.controladores.documentos import Documentos
    from latex_app.controladores.espacio import Espacio
    from latex_app.controladores.historial import Historial
    from latex_app.controladores.opciones import Opciones
    consola = Consola()
    tareas = Tareas(consola)
    ajustes = Ajustes()
    opciones = Opciones()
    espacio = Espacio(consola, ajustes)
    historial = Historial(consola)
    docs = Documentos(espacio, opciones, historial, consola, cache=tmp_path / "cache")
    p = dict(consola=consola, tareas=tareas, ajustes=ajustes, opciones=opciones, espacio=espacio, historial=historial, documentos=docs,
             corrida=Corrida(espacio, opciones, docs, historial, consola, tareas), carpeta=documentos)
    yield p
    tareas.esperar()


@requiere_binding
def test_espacio_vista_carpeta_y_rutas(app, piezas, tmp_path):
    e, carpeta = piezas["espacio"], piezas["carpeta"]
    assert e.vista == "carpeta" and e.indiceVista == 0
    e.fijarVista("historial")
    assert e.vista == "historial" and e.indiceVista == 2 and e.textoVista == "Compilaciones"
    e.fijarVistaPorIndice(0)
    assert e.fijarCarpeta(str(carpeta)) == "" and e.carpeta == str(carpeta) and e.nombreCarpeta == "doc"
    assert e.fijarCarpeta(str(carpeta / "articulo.tex")).startswith("No es una carpeta")
    assert e.filasCarpetas[0]["nombre"] == f"dir:{carpeta}" and e.filasCarpetas[0]["texto"] == "doc"
    e.subir()
    assert e.carpeta == str(tmp_path) and e.carpetas_recientes()[0] == str(tmp_path)
    nombres = [x["nombre"] for x in e.entradas_paleta("")]
    assert nombres[:3] == ["ir.carpeta", "ir.recientes", "ir.historial"] and f"dir.{carpeta}" in nombres
    e.fijarContexto("x")
    assert e.contexto == "x"
    orden = e.orden_editor(str(carpeta / "articulo.tex"), 17)
    assert orden and orden[-1].endswith("articulo.tex") and ("17" in " ".join(orden) or orden[0] == "xdg-open")
    assert e.orden_editor(str(carpeta / "no.tex"), 1) == []


@requiere_binding
def test_opciones_de_la_sesion(app, piezas):
    o = piezas["opciones"]
    assert o.motor == "auto" and o.bibliografia == "biber" and o.pasadas == 2 and o.pasadasEfectivas == 3
    assert [m["valor"] for m in o.motores] == ["auto", "lualatex"]          # ni pdflatex ni xelatex
    assert o.descripcion == "LuaLaTeX (auto) + Biber · 3 pasadas"
    o.fijarMotor("pdflatex")                                                  # no se admite: queda auto
    assert o.motor == "auto"
    o.fijarMotor("lualatex"); o.fijarBibliografia("ninguna"); o.pasadas = 9; o.indice = True
    assert o.motor == "lualatex" and o.bibliografia == "ninguna" and o.pasadas == 5 and o.pasadasEfectivas == 5
    assert o.descripcion == "LuaLaTeX · 5 pasadas · índice"
    tex = Path("/x/doc.tex")
    co = o.para(tex, Path("/c/r.log"), biber=True)
    assert co.bibliografia == "biber" and co.motor == "lualatex" and co.indice and co.log == Path("/c/r.log")
    assert o.ordenTexto("/x/doc.tex").startswith("main.sh -e lualatex -p 5 -i") and o.ordenTexto("") == ""
    o.vigilar = True; o.abrirAlTerminar = True
    assert o.vigilar and o.abrirAlTerminar
    o.fijarMotor("auto"); o.fijarBibliografia("biber"); o.pasadas = 2; o.indice = False; o.vigilar = False; o.abrirAlTerminar = False


@requiere_binding
def test_documentos_tabla_actual_y_abrir(app, piezas, tmp_path):
    d, e, h = piezas["documentos"], piezas["espacio"], piezas["historial"]
    carpeta = piezas["carpeta"]
    assert e.fijarCarpeta(str(carpeta)) == ""
    assert d.total == 2 and d.modelo.filas == 2 and d.nombres() == ["articulo.tex", "con-error.tex"]
    assert d.contadores["sin_compilar"] == 2 and d.filasNavegacion[0]["contador"] == 2
    assert not d.hayActual and d.nombre == "" and d.estadoTexto == ""
    d.fijarFila(0)
    assert d.hayActual and d.nombre == "articulo.tex" and d.estadoClave == "sin_compilar" and d.motorTexto == "LuaLaTeX" and not d.hayPdf
    assert e.contexto.startswith("articulo.tex · LuaLaTeX") and d.filaDe(d.actual) == 0 and d.nProblemas == 0 and d.registro == ""
    assert d.ultimaCompilacion == "" and d.salidas.filas == 0
    # abrir otro .tex: su carpeta pasa a ser la de trabajo, queda actual y entra a recientes
    otra = tmp_path / "otra"
    otra.mkdir()
    (otra / "nota.tex").write_text("% !TEX program = pdflatex\n\\documentclass{article}\\begin{document}x\\end{document}\n", encoding="utf-8")
    assert d.abrir(str(otra / "nota")) == ""                                   # sin extensión también
    assert e.carpeta == str(otra) and d.nombre == "nota.tex" and d.total == 1 and d.motorTexto == "pdfLaTeX (declarado)" and d.motorDeclarado == "pdflatex"
    assert h.recientes() == [str(otra / "nota.tex")] and d.modeloRecientes.filas == 1
    assert d.abrir(str(otra / "no-existe.tex")).startswith("No existe")
    d.modelo.filtrar("zzz")
    assert d.modelo.filas == 0
    d.modelo.filtrar("")
    # volver a la carpeta del ejemplo: el actual (de otra carpeta) sigue siendo válido
    e.fijarCarpeta(str(carpeta))
    assert d.total == 2 and d.nombre == "nota.tex"
    d.fijarFilaReciente(0)
    assert d.nombre == "nota.tex"
    d.fijarActual("")
    assert not d.hayActual and e.contexto == ""
    avisos = []
    d.aviso.connect(lambda t, k: avisos.append(k))
    d.abrirPdf()
    assert avisos == ["aviso"]


@requiere_binding
def test_corrida_simula_sin_escribir(app, piezas):
    c, d, e, t, consola = piezas["corrida"], piezas["documentos"], piezas["espacio"], piezas["tareas"], piezas["consola"]
    e.fijarCarpeta(str(piezas["carpeta"]))
    assert not c.puede and "Abre un .tex" in c.motivo
    assert not c.simular() and not c.compilar()
    d.fijarFila(0)
    antes = sorted(p.name for p in piezas["carpeta"].iterdir())
    assert c.puede and c.simular() and t.activa and c.enCurso and c.que == "simular"
    _esperar(app, t)
    assert "Simulación (--dry-run)" in consola.salida.texto and "lualatex" in consola.salida.texto
    assert sorted(p.name for p in piezas["carpeta"].iterdir()) == antes          # simular no escribe
    assert piezas["historial"].total == 0 and d.estadoClave == "sin_compilar"
    assert c.auxiliaresParaLimpiar() == []


@requiere_binding
@requiere_lualatex
def test_corrida_compila_de_verdad_limpia_y_anota_el_historial(app, piezas, tmp_path):
    import shutil
    c, d, e, t, h, o = piezas["corrida"], piezas["documentos"], piezas["espacio"], piezas["tareas"], piezas["historial"], piezas["opciones"]
    carpeta = piezas["carpeta"]
    e.fijarCarpeta(str(carpeta))
    o.fijarBibliografia("biber" if shutil.which("biber") else "ninguna")
    tex = carpeta / "articulo.tex"
    antes = tex.read_bytes()
    d.fijarActual(str(tex))
    terminadas, progresos = [], []
    c.terminada.connect(lambda r, ok: terminadas.append((Path(r).name, ok)))
    t.cambiada.connect(lambda: progresos.append(t.elemento) if t.activa and t.elemento else None)
    assert c.compilar()
    assert d.estadoClave == "compilando"
    _esperar(app, t)
    assert terminadas == [("articulo.tex", True)]
    assert tex.read_bytes() == antes and (carpeta / "articulo.pdf").is_file()
    assert d.estadoClave == "avisos" and d.nErrores == 0 and d.nAvisos >= 1 and d.hayPdf and d.pdfPaginas >= 1
    assert "pasada 1 de" in progresos[0]
    assert any("fig:modelo" in f["mensaje"] and f["linea"] == 17 for f in d._problemas.todas())
    assert d.registro and "LuaHBTeX" in d.registro and d.origenProblemas.endswith("-articulo.log")
    assert h.total == 1 and h.ultima_de(str(tex))["ok"] and d.ultimaCompilacion.startswith("20") and "compiló" in d.ultimaCompilacion
    assert h.recientes() == [str(tex)] and d.modeloRecientes.filas == 1
    assert [s["tipo"] for s in d._salidas.todas()] == ["PDF"]                   # la CLI borró los auxiliares al terminar bien
    assert [f["estado"] for f in d._tabla_carpeta.todas()] == ["Con avisos", "Sin compilar"]
    # los filtros de la lista de problemas
    n = d.problemas.filas
    d.mostrarAvisos = False
    assert d.problemas.filas < n
    d.mostrarAvisos = True
    assert d.problemas.filas == n
    # el documento con un error: falla, deja el .log, la fila cambia y el historial lo anota
    d.fijarActual(str(carpeta / "con-error.tex"))
    assert c.compilar()
    _esperar(app, t)
    assert terminadas[-1] == ("con-error.tex", False) and d.estadoClave == "errores" and d.nErrores >= 1
    assert any(f["mensaje"] == "Undefined control sequence." and f["linea"] == 5 for f in d._problemas.todas())
    assert h.total == 2 and not h.entradas()[0]["ok"]
    assert (carpeta / "con-error.log").is_file() and "con-error.log" in c.auxiliaresParaLimpiar()
    # limpiar borra solo los auxiliares del documento actual
    (carpeta / "ajeno.aux").write_text("x", encoding="utf-8")
    assert c.limpiar()
    _esperar(app, t)
    assert c.auxiliaresParaLimpiar() == [] and not (carpeta / "con-error.aux").exists() and (carpeta / "ajeno.aux").exists()
    assert (carpeta / "con-error.tex").is_file() and (carpeta / "articulo.pdf").is_file()
    # el historial: quitar y vaciar
    h.fijarFila(0)
    assert h.haySeleccion
    h.quitar(0)
    assert h.total == 1
    h.vaciar()
    assert h.total == 0 and d.ultimaCompilacion == ""
    o.fijarBibliografia("biber")


@requiere_binding
def test_recompilar_al_guardar_vigila_el_documento_actual(app, piezas):
    """Con «Recompilar al guardar», cambiar el .tex en disco pide recompilar (tras la espera); sin la opción, nada."""
    d, e, o = piezas["documentos"], piezas["espacio"], piezas["opciones"]
    e.fijarCarpeta(str(piezas["carpeta"]))
    tex = piezas["carpeta"] / "con-error.tex"
    d.fijarActual(str(tex))
    assert not d.vigilando
    o.vigilar = True
    assert d.vigilando
    pedidos = []
    d.recompilar.connect(lambda: pedidos.append(1))
    tex.write_text(tex.read_text(encoding="utf-8") + "% cambio\n", encoding="utf-8")
    inicio = time.monotonic()
    while not pedidos and time.monotonic() - inicio < 5:
        app.processEvents()
        time.sleep(0.05)
    assert pedidos == [1]
    o.vigilar = False
    assert not d.vigilando
    for _ in range(5):
        app.processEvents()
