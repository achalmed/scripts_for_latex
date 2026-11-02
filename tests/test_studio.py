"""test_studio.py — LaTeX Studio (QML + Kirigami sobre gui-comun 2.x) abre su ventana sin pantalla con el Python del
sistema sobre el ejemplo copiado a una carpeta temporal: la ventana entera (acciones, menús, barra, resumen), cada
componente QML, `--smoke` con un .tex por argumento, y las reglas de la familia (sin colores propios, sin marca dentro,
sin QtWidgets, sin pdfLaTeX ni XeLaTeX en la ventana).
"""

from __future__ import annotations

import json
import re
import subprocess

import pytest

from conftest import PYTHON_SISTEMA, REPO, STUDIO, copiar_ejemplo, correr_python, entorno_gui, requiere_sistema

QML = STUDIO / "latex_app" / "qml"

ABRIR = """
import sys, json; sys.path.insert(0, sys.argv[1])
from latex_app import aplicacion
from gui_comun.nucleo import Aplicacion
from gui_comun.qt import QTimer
app = Aplicacion("latex-studio", "LaTeX Studio", version="prueba", nombre_ajustes="LatexStudio")
piezas = aplicacion.construir(app)
errores = []
app.motor.warnings.connect(lambda avisos: errores.extend(a.toString() for a in avisos))
piezas["espacio"].fijarCarpeta(sys.argv[2])
ok = app.cargar(aplicacion.QML_DIR / "Main.qml")
raiz = app.motor.rootObjects()[0] if ok else None
titulo = raiz.property("title") if raiz else ""
a, d = piezas["acciones"], piezas["documentos"]
sin_doc = (a.accion("doc.compilar").habilitada, a.accion("doc.pdf").habilitada)
d.fijarFila(0)
con_doc = (a.accion("doc.compilar").habilitada, a.accion("doc.simular").habilitada, a.accion("doc.limpiar").habilitada, a.accion("doc.editor").habilitada, a.accion("doc.pdf").habilitada)
QTimer.singleShot(600, app.app.quit); app.app.exec(); app.cerrar()
print(json.dumps({"ok": ok, "titulo": titulo, "errores": errores, "acciones": a.nombres(), "menus": [m["titulo"] for m in a.menus],
                  "barra": a.barra, "sin_doc": sin_doc, "con_doc": con_doc, "resumen": piezas["espacio"].resumen, "contexto": piezas["espacio"].contexto,
                  "motores": [m["valor"] for m in piezas["opciones"].motores]}))
"""

COMPONENTE = """
import sys, json, os; sys.path.insert(0, sys.argv[1])
from latex_app import aplicacion
from gui_comun.nucleo import Aplicacion
from gui_comun.qt import QTimer
app = Aplicacion("latex-studio", "LaTeX Studio", version="prueba", nombre_ajustes="LatexStudio")
aplicacion.construir(app)
app.motor.addImportPath(str(aplicacion.QML_DIR))
errores = []
app.motor.warnings.connect(lambda avisos: errores.extend(a.toString() for a in avisos))
nombre, carpeta = sys.argv[2], sys.argv[3]
ruta = os.path.join(os.environ["XDG_CACHE_HOME"], "Prueba_" + nombre + ".qml")
os.makedirs(os.path.dirname(ruta), exist_ok=True)
open(ruta, "w").write('import QtQuick\\nimport GuiComun\\nimport "file://%s/%s"\\nVentanaStudio { id: ventana; acciones: studio.acciones; visible: false; %s { id: objeto } }\\n' % (str(aplicacion.QML_DIR), carpeta, nombre))
ok = app.cargar(ruta)
QTimer.singleShot(400, app.app.quit); app.app.exec(); app.cerrar()
print(json.dumps({"ok": ok, "errores": errores}))
"""


def _graves(errores):
    return [e for e in errores if "TypeError" in e or "ReferenceError" in e or "is not a type" in e or "Cannot assign" in e or "No se puede asignar" in e]


@requiere_sistema
def test_abre_y_cierra_su_ventana(tmp_path):
    carpeta = copiar_ejemplo(tmp_path / "doc")
    r = correr_python(ABRIR, entorno_gui(tmp_path), str(carpeta))
    assert r.returncode == 0, f"código {r.returncode}\n{r.stderr[-3000:]}"
    datos = json.loads(r.stdout.strip().splitlines()[-1])
    assert datos["ok"], r.stderr[-3000:]
    assert datos["titulo"] == "doc — LaTeX Studio"
    assert not _graves(datos["errores"]), "\n".join(_graves(datos["errores"]))
    for n in ("archivo.abrir", "archivo.carpeta", "archivo.subir", "archivo.dolphin", "archivo.terminal", "archivo.copiar",
              "editar.filtrar", "editar.todo", "historial.quitar", "historial.vaciar",
              "ver.vista.carpeta", "ver.vista.recientes", "ver.vista.historial", "ver.recargar",
              "doc.compilar", "doc.compilar_biber", "doc.simular", "doc.cancelar", "doc.limpiar", "doc.pdf", "doc.editor", "doc.vigilar", "doc.abrir_al_terminar",
              "prob.ir", "ayuda.manual", "ventana.navegacion", "ventana.detalles", "ventana.inferior", "ventana.paleta", "app.ajustes", "app.acerca", "app.salir"):
        assert n in datos["acciones"], n
    assert datos["menus"] == ["&Archivo", "&Editar", "&Ver", "&Documento", "&Herramientas", "A&justes", "Ay&uda"]
    assert datos["barra"] == ["doc.compilar", "doc.simular", "|", "doc.pdf", "doc.editor", "|", "doc.limpiar"]
    assert datos["sin_doc"] == [False, False]
    assert datos["con_doc"] == [True, True, True, True, False]          # sin PDF todavía: Abrir el PDF deshabilitada
    assert datos["resumen"] == "2 documentos · 2 sin compilar"
    assert datos["contexto"].startswith("articulo.tex · LuaLaTeX")
    assert datos["motores"] == ["auto", "lualatex"]


@requiere_sistema
def test_main_smoke_con_un_tex(tmp_path):
    carpeta = copiar_ejemplo(tmp_path / "doc")
    r = subprocess.run([PYTHON_SISTEMA, str(STUDIO / "main.py"), "--smoke", str(carpeta / "con-error.tex")], env=entorno_gui(tmp_path),
                       capture_output=True, text=True, timeout=120, cwd=tmp_path)
    assert r.returncode == 0, f"código {r.returncode}\n{r.stderr[-3000:]}"
    ruido = [l for l in r.stderr.splitlines() if "TypeError" in l or "ReferenceError" in l or "polish() loop" in l]
    assert not ruido, "\n".join(ruido)


COMPONENTES = sorted((p.parent.name, p.stem) for p in QML.glob("*/*.qml"))


@requiere_sistema
@pytest.mark.parametrize("carpeta,nombre", COMPONENTES, ids=[f"{c}/{n}" for c, n in COMPONENTES])
def test_cada_componente_qml(carpeta, nombre, tmp_path):
    r = correr_python(COMPONENTE, entorno_gui(tmp_path), nombre, carpeta)
    assert r.returncode == 0, r.stderr[-3000:]
    datos = json.loads(r.stdout.strip().splitlines()[-1])
    assert datos["ok"], r.stderr[-3000:]
    assert not _graves(datos["errores"]), "\n".join(_graves(datos["errores"]))


def test_sin_colores_propios_en_qml():
    malos = []
    for qml in QML.rglob("*.qml"):
        for n, linea in enumerate(qml.read_text(encoding="utf-8").splitlines(), 1):
            sin_comentario = linea.split("//")[0]
            if re.search(r'"#[0-9a-fA-F]{3,8}"', sin_comentario) or re.search(r'\bfont\.(pointSize|pixelSize|family)\s*:\s*["\d]', sin_comentario):
                malos.append(f"{qml.relative_to(STUDIO)}:{n}: {linea.strip()}")
    assert not malos, "\n".join(malos)


def test_sin_marca_dentro_de_la_ventana():
    """Ningún nombre ni logotipo del studio dentro de la ventana (rediseno.md): el título lo pone KWin."""
    codigo = "\n".join(l.split("//")[0] for l in (QML / "Main.qml").read_text(encoding="utf-8").splitlines())
    assert "logotipo" not in codigo.lower() and "logo_svg" not in codigo and "marca.svg" not in codigo
    assert 'text: "LaTeX Studio"' not in codigo and "Kirigami.Heading" not in codigo.split("centro:")[0]


def test_sin_qtwidgets_ni_motores_heredados_en_la_ventana():
    """El studio no importa QtWidgets (corre con el Qt del sistema, en QML) y no ofrece pdfLaTeX ni XeLaTeX (regla 6)."""
    for py in (STUDIO / "latex_app").rglob("*.py"):
        texto = py.read_text(encoding="utf-8")
        assert "QtWidgets" not in texto and "gui_comun.widgets" not in texto, py
    for qml in QML.rglob("*.qml"):
        texto = "\n".join(l.split("//")[0] for l in qml.read_text(encoding="utf-8").splitlines())
        assert "pdflatex" not in texto.lower().replace("pdflatex y xelatex no se ofrecen", "") or "no se ofrecen" in texto, qml
    assert (STUDIO / "main.py").read_text(encoding="utf-8").startswith("#!/usr/bin/python3")
    assert "/usr/bin/python3" in (REPO / "install.sh").read_text(encoding="utf-8")
