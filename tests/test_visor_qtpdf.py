"""test_visor_qtpdf.py — lo que el visor hace con el texto del PDF cuando QtQuick.Pdf está instalado (decisiones §1.11):
seleccionar arrastrando con el ratón y copiar, seguir los enlaces del PDF (internos: la página y el punto; externos:
`Visor.abrirEnlace`, que solo abre http, https y mailto) y buscar con los resultados resaltados.

La interacción es de verdad: un PDF con `hyperref` compilado con LuaLaTeX en una carpeta temporal, `CapaQtPdf` y
`BusquedaQtPdf` en una ventana sin pantalla del Python del sistema y el ratón movido con eventos de `QMouseEvent` (arrastre, clic sobre
cada enlace). También comprueba que la capa no se queda con el doble clic (SyncTeX al código sigue en `VisorPdf`).
"""

from __future__ import annotations

import json
import subprocess

import pytest

from conftest import STUDIO, correr_python, entorno_gui, requiere_lualatex, requiere_sistema

TEX = r"""\documentclass{article}
\usepackage{hyperref}
\begin{document}
\section{Inicio}\label{sec:inicio}
Texto de prueba con la palabra cometa. Véase la sección~\ref{sec:fin} y la página \url{https://example.org}.
\newpage
\section{Fin}\label{sec:fin}
Otra vez la palabra cometa y otra cometa más. Volver a~\ref{sec:inicio}.
\end{document}
"""

GUION = r"""
import sys, json, os
from gui_comun.qt import QGuiApplication, QTimer, QUrl, Qt
from PySide6.QtCore import QEvent, QPointF
from PySide6.QtGui import QMouseEvent
from PySide6.QtQuick import QQuickView
app = QGuiApplication(sys.argv)
sys.excepthook = lambda *e: (sys.__excepthook__(*e), app.exit(1))     # un fallo en un paso termina, no cuelga
import gui_comun                                # las piezas del visor son de gui-comun 3.2 (antes, copias de este studio)
componentes, pdf, ruta = os.path.join(os.path.dirname(gui_comun.__file__), "qml", "GuiComun"), sys.argv[2], sys.argv[3]
open(ruta, "w").write('''import QtQuick
import "file://%s"
Item {
    id: raiz
    width: 612; height: 792
    property var enlaces: []
    property int dobles: 0
    property var capa: null
    property alias busqueda: busqueda
    DocumentoQtPdf { id: doc; source: "%s" }
    BusquedaQtPdf { id: busqueda; document: doc }
    TapHandler { onDoubleTapped: raiz.dobles++ }
    // como en VisorPdf: la página dentro de una lista que se desplaza (el arrastre tiene que seleccionar, no mover)
    ListView {
        id: lista
        anchors.fill: parent
        model: 2
        delegate: Item { width: 612; height: 792 }
        header: CapaQtPdf {
        id: capa
        width: 612; height: 792
        Component.onCompleted: raiz.capa = capa
        document: doc
        pagina: 1
        zoom: 1
        busqueda: busqueda
        onIrA: (p, y) => raiz.enlaces = raiz.enlaces.concat(["pagina " + p + " y " + Math.round(y)])
        onEnlaceExterno: (url) => raiz.enlaces = raiz.enlaces.concat([url])
    }
    }
    function buscar(texto) { busqueda.searchString = texto }
    function ir(n) { busqueda.currentResult = n }
    function cuenta() { return JSON.stringify({paginasDoc: doc.pageCount, texto: capa.texto, desplazada: lista.contentY + 792, enlaces: enlaces, dobles: dobles, total: busqueda.count,
        resultados: busqueda.boundingPolygonsOnPage(0).length, actual: busqueda.currentResult,
        pagina: busqueda.currentResultLink.page, y: Math.round(busqueda.currentResultLink.location.y)}) }
}
''' % (componentes, QUrl.fromLocalFile(pdf).toString()))
vista = QQuickView()
# el ratón, a mano: el PySide6 del sistema no trae QtTest
reloj = [1000]
def raton(tipo, x, y, apretado=True, paso=40):
    p = QPointF(x, y)
    boton = Qt.LeftButton if tipo != QEvent.MouseMove else Qt.NoButton
    botones = Qt.LeftButton if apretado else Qt.NoButton
    evento = QMouseEvent(tipo, p, vista.mapToGlobal(p), boton, botones, Qt.NoModifier)
    reloj[0] += paso
    evento.setTimestamp(reloj[0])           # el doble clic y el toque se miden con la marca de tiempo del evento
    QGuiApplication.sendEvent(vista, evento)
def clic(x, y, paso=1000):
    raton(QEvent.MouseButtonPress, x, y, paso=paso); raton(QEvent.MouseButtonRelease, x, y, False)
def doble(x, y):
    clic(x, y); raton(QEvent.MouseButtonPress, x, y); raton(QEvent.MouseButtonDblClick, x, y, paso=0); raton(QEvent.MouseButtonRelease, x, y, False)
errores = []
vista.engine().warnings.connect(lambda avisos: errores.extend(a.toString() for a in avisos))
vista.setSource(QUrl.fromLocalFile(ruta))
if vista.status() != QQuickView.Status.Ready:
    print(json.dumps({"ok": False, "errores": [e.toString() for e in vista.errors()]})); sys.exit(0)
vista.show()
raiz = vista.rootObject()
pasos = {}
from PySide6.QtCore import QMetaObject, Q_ARG, Q_RETURN_ARG
def leer():
    return json.loads(QMetaObject.invokeMethod(raiz, "cuenta", Q_RETURN_ARG("QVariant")))
# cada paso espera a que se cumpla lo que el anterior debía producir (no un tiempo fijo: bajo carga, cargar el PDF o
# contar los resultados de la búsqueda tarda más); con un tope amplio, tras el cual el paso sigue y las aserciones dicen
# qué faltó
import time
temporizadores = []
def cuando(condicion, accion, tope=20.0):
    inicio = time.monotonic()
    t = QTimer(); t.setInterval(40)
    def tic():
        if condicion() or time.monotonic() - inicio > tope:
            t.stop(); accion()
    t.timeout.connect(tic); temporizadores.append(t); t.start()
# las posiciones (en puntos) salen del propio PDF: el texto empieza en x≈134 y la línea en y≈150; los enlaces, en la
# misma línea (el 2 de la sección en x≈385, la URL en x≈445) y la URL partida en la línea siguiente
def arrastrar():
    raton(QEvent.MouseButtonPress, 136, 152)
    for x in range(140, 300, 20):
        raton(QEvent.MouseMove, x, 155)
    raton(QEvent.MouseButtonRelease, 300, 155, False)
    cuando(lambda: leer()["texto"] != "", despues_del_arrastre)
def despues_del_arrastre():
    pasos["arrastre"] = leer()
    clic(388, 154)                           # el \ref interno (las marcas de tiempo, a 1 s: nunca un doble clic)
    clic(460, 154)                           # la URL
    cuando(lambda: len(leer()["enlaces"]) >= 2, clic_suelto)
def clic_suelto():
    pasos["enlaces"] = leer()
    clic(300, 500)                           # un clic fuera: borra la selección
    cuando(lambda: leer()["texto"] == "", doble_clic)
def doble_clic():
    pasos["clic"] = leer()
    doble(300, 600)
    cuando(lambda: leer()["dobles"] >= 1, buscar)
def buscar():
    pasos["doble"] = leer()
    QMetaObject.invokeMethod(raiz, "buscar", Q_ARG("QVariant", "cometa"))
    cuando(lambda: leer()["total"] >= 3, siguiente)        # PdfSearchModel cuenta sin bloquear
def siguiente():
    QMetaObject.invokeMethod(raiz, "ir", Q_ARG("QVariant", 2))
    cuando(lambda: leer()["actual"] == 2 and leer()["pagina"] == 1, fin)
def fin():
    pasos["busqueda"] = leer()
    app.quit()
cuando(lambda: leer()["paginasDoc"] > 0, lambda: QTimer.singleShot(150, arrastrar))   # el PDF abierto (y pintada la capa)
app.exec()
print(json.dumps({"ok": True, "errores": errores, **pasos}))
"""


@pytest.fixture(scope="module")
def pdf_con_enlaces(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("enlaces")
    (carpeta / "enlaces.tex").write_text(TEX, encoding="utf-8")
    for _ in range(2):                       # dos pasadas: la referencia cruzada resuelta
        subprocess.run(["lualatex", "-interaction=batchmode", "enlaces.tex"], cwd=carpeta, capture_output=True, timeout=180)
    pdf = carpeta / "enlaces.pdf"
    assert pdf.is_file()
    return pdf


def _hay_qtpdf_en_el_sistema() -> bool:
    from conftest import PYTHON_SISTEMA
    if not PYTHON_SISTEMA:
        return False
    r = subprocess.run([PYTHON_SISTEMA, "-c", "import sys; sys.path.insert(0, sys.argv[1]); from latex_app.controladores.visor import hay_qtpdf; print(hay_qtpdf())",
                        str(STUDIO)], capture_output=True, text=True, timeout=60)
    return r.stdout.strip() == "True"


@requiere_sistema
@requiere_lualatex
def test_seleccion_enlaces_y_busqueda_con_el_raton(pdf_con_enlaces, tmp_path):
    if not _hay_qtpdf_en_el_sistema():
        pytest.skip("QtQuick.Pdf no está instalado (qml6-module-qtquick-pdf)")
    r = correr_python(GUION, entorno_gui(tmp_path), str(pdf_con_enlaces), str(tmp_path / "Prueba.qml"))
    assert r.returncode == 0, r.stderr[-3000:]
    datos = json.loads(r.stdout.strip().splitlines()[-1])
    assert datos["ok"], datos
    graves = [e for e in datos["errores"] if "TypeError" in e or "ReferenceError" in e or "is not a type" in e]
    assert not graves, "\n".join(graves)
    # arrastrar con el ratón selecciona el texto de la línea
    assert datos["arrastre"]["texto"].startswith("Texto de prueba con la palabra"), datos["arrastre"]
    assert datos["arrastre"]["desplazada"] == 0                     # la lista no se movió con el arrastre
    # el enlace interno lleva a la página 2 (la sección «Fin»); el externo pasa su URL al controlador
    assert datos["enlaces"]["enlaces"][0].startswith("pagina 2 y "), datos["enlaces"]
    assert datos["enlaces"]["enlaces"][1] == "https://example.org"
    # un clic suelto borra la selección; el doble clic llega a quien está debajo (VisorPdf: SyncTeX al código)
    assert datos["clic"]["texto"] == ""
    assert datos["doble"]["dobles"] == 1 and datos["doble"]["texto"] == ""
    # la búsqueda: tres resultados (uno en la página 1, resaltado en la capa) y el tercero en la página 2
    b = datos["busqueda"]
    assert b["total"] == 3 and b["resultados"] == 1
    assert b["actual"] == 2 and b["pagina"] == 1 and b["y"] > 0


def test_abrir_enlace_solo_web_y_correo(app, tmp_path, monkeypatch):
    """Un enlace del PDF a `file:` o a una orden no se sigue; http, https y mailto van a la aplicación del escritorio."""
    from gui_comun import visor_pdf as base
    from latex_app.controladores import visor as cv
    abiertos = []
    monkeypatch.setattr(base.QDesktopServices, "openUrl", staticmethod(lambda url: abiertos.append(url.toString()) or True))
    v = cv.Visor(cache=tmp_path)
    avisos = []
    v.aviso.connect(lambda texto, nivel: avisos.append(nivel))
    assert v.abrirEnlace("https://example.org/a") and v.abrirEnlace("mailto:alguien@example.org")
    assert not v.abrirEnlace("file:///etc/hosts") and not v.abrirEnlace("javascript:alert(1)") and not v.abrirEnlace("relativo.pdf")
    assert abiertos == ["https://example.org/a", "mailto:alguien@example.org"]
    assert avisos == ["aviso", "aviso", "aviso"]
    v.apagar()
