"""test_studio.py — LaTeX Studio (reingeniería del 2026-11-02, QML + Kirigami sobre gui-comun 2.x) abre su ventana sin
pantalla con el Python del sistema sobre los proyectos de muestra copiados a una carpeta temporal (WRITING_DIR y
DESPACHO_DIR temporales: nunca las carpetas del autor): la ventana entera (acciones, menús, barra de compilación,
disponibilidad sin y con proyecto, las dos vistas, el editor y el visor con un proyecto abierto), cada componente QML,
`--smoke` con un .tex por argumento, y las reglas de la familia (sin colores propios, sin marca dentro, sin QtWidgets,
sin pdfLaTeX ni XeLaTeX ofrecidos).
"""

from __future__ import annotations

import json
import re
import subprocess

import pytest

from conftest import PYTHON_SISTEMA, REPO, STUDIO, copiar_muestra, correr_python, entorno_gui, requiere_sistema

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
piezas["proyectos"].detectar_ya()
ok = app.cargar(aplicacion.QML_DIR / "Main.qml")
raiz = app.motor.rootObjects()[0] if ok else None
a, p, i = piezas["acciones"], piezas["proyectos"], piezas["interfaz"]
hab = lambda *ns: [a.accion(n).habilitada for n in ns]
sin = hab("compilar.compilar", "compilar.limpiar", "archivo.guardar", "escritorio.pdf", "compilar.seleccion")
titulo_sin = raiz.property("title") if raiz else ""
resultado = {}
def abrir():
    i.pedir.emit("abrir_proyecto", {"ruta": sys.argv[2]})
    QTimer.singleShot(700, despues)
def despues():
    resultado.update(vista=i.vista, titulo=raiz.property("title"), abiertos=[f["nombre"] for f in piezas["editor"].abiertos.todas()], modificados=piezas["editor"].modificados,
                     con=hab("compilar.compilar", "compilar.limpiar", "archivo.guardar", "editar.buscar", "editar.ir_linea", "escritorio.dolphin"),
                     archivos=p.archivos.filas, esquema=p.esquema.filas)
    i.pedir.emit("buscar", {}); i.pedir.emit("ir_linea", {}); i.pedir.emit("atajos", {}); i.pedir.emit("alternar_pdf", {}); i.pedir.emit("alternar_pdf", {})
    i.fijarVista("proyectos"); i.fijarVista("escritura")
    QTimer.singleShot(500, app.app.quit)
QTimer.singleShot(400, abrir)
app.app.exec(); app.cerrar()
limpiar = a.accion("compilar.limpiar")
confirmaciones = {"limpiar": [limpiar.operacion, limpiar.requiereConfirmacion], "escritorio": type(app.escritorio).__module__}
print(json.dumps({"ok": ok, "confirmaciones": confirmaciones, "titulo_sin": titulo_sin, "errores": errores, "acciones": a.nombres(), "menus": [m["titulo"] for m in a.menus],
                  "barra": a.barra, "sin": sin, "total": p.total, **resultado}))
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


def _entorno(tmp_path):
    muestra = copiar_muestra(tmp_path / "escritura")
    (tmp_path / "despacho").mkdir(exist_ok=True)
    return muestra, entorno_gui(tmp_path, WRITING_DIR=str(muestra), DESPACHO_DIR=str(tmp_path / "despacho"))


@requiere_sistema
def test_abre_la_ventana_y_un_proyecto(tmp_path):
    muestra, env = _entorno(tmp_path)
    r = correr_python(ABRIR, env, str(muestra / "tesis-multiarchivo" / "capitulos" / "metodo.tex"))
    assert r.returncode == 0, f"código {r.returncode}\n{r.stderr[-3000:]}"
    datos = json.loads(r.stdout.strip().splitlines()[-1])
    assert datos["ok"], r.stderr[-3000:]
    assert not _graves(datos["errores"]), "\n".join(_graves(datos["errores"]))
    assert datos["total"] == 6 and datos["titulo_sin"] == "Proyectos — LaTeX Studio"
    for n in ("archivo.abrir", "archivo.carpetas", "archivo.anadir_carpeta", "proyectos.detectar", "archivo.guardar", "archivo.guardar_como", "archivo.guardar_todo",
              "archivo.cerrar", "proyecto.cerrar", "escritorio.pdf", "escritorio.dolphin", "escritorio.carpeta", "escritorio.terminal",
              "escritorio.copiar", "escritorio.editor", "archivo.salir", "editar.buscar", "editar.reemplazar", "editar.ir_linea",
              "editar.completar", "editar.comentar", "ver.proyectos", "ver.escritura", "ver.pdf", "compilar.compilar",
              "compilar.reconstruir", "compilar.simular", "compilar.cancelar", "compilar.seleccion", "compilar.limpiar",
              "compilar.dependencias", "compilar.siguiente", "compilar.al_guardar", "synctex.pdf", "ayuda.atajos", "ayuda.manual",
              "ventana.paleta", "app.ajustes", "app.acerca"):
        assert n in datos["acciones"], n
    assert datos["menus"] == ["&Archivo", "&Editar", "&Ver", "&Compilar", "&Herramientas", "A&justes", "Ay&uda"]
    assert datos["barra"][:3] == ["compilar.compilar", "compilar.cancelar", "compilar.reconstruir"]
    assert datos["sin"] == [False, False, False, False, True]          # sin proyecto: nada que compilar, guardar ni ver
    assert datos["vista"] == "escritura" and datos["titulo"] == "tesis-multiarchivo · principal.tex — LaTeX Studio"
    assert datos["abiertos"] == ["principal.tex"]                       # un capítulo abre el proyecto y su principal
    assert datos["modificados"] == []                                   # abrir no marca el archivo como modificado
    assert datos["con"] == [True, True, True, True, True, True]
    assert datos["archivos"] == 5 and datos["esquema"] >= 7
    assert datos["confirmaciones"]["limpiar"] == ["eliminacion", True]               # gui-comun 3.0 la confirma con su lista
    assert datos["confirmaciones"]["escritorio"] == "gui_comun.escritorio"          # las tres operaciones de escritorio, de la base


@requiere_sistema
def test_main_smoke_con_un_tex(tmp_path):
    muestra, env = _entorno(tmp_path)
    r = subprocess.run([PYTHON_SISTEMA, str(STUDIO / "main.py"), "--smoke", str(muestra / "con-error" / "roto.tex")], env=env,
                       capture_output=True, text=True, timeout=120, cwd=tmp_path)
    assert r.returncode == 0, f"código {r.returncode}\n{r.stderr[-3000:]}"
    ruido = [l for l in r.stderr.splitlines() if "TypeError" in l or "ReferenceError" in l or "polish() loop" in l]
    assert not ruido, "\n".join(ruido)


COMPONENTES = sorted((p.parent.name, p.stem) for p in QML.glob("*/*.qml"))


@requiere_sistema
@pytest.mark.parametrize("carpeta,nombre", COMPONENTES, ids=[f"{c}/{n}" for c, n in COMPONENTES])
def test_cada_componente_qml(carpeta, nombre, tmp_path):
    _muestra, env = _entorno(tmp_path)
    r = correr_python(COMPONENTE, env, nombre, carpeta)
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
