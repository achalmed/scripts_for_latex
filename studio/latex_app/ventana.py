"""La ventana de LaTeX Studio: el marco común de los studios (gui_comun) sobre `script_compilar_latex`.

Tres páginas: Inicio (recientes y abrir), Compilar (opciones, compilar, simular, limpiar; el resultado con cada error y
aviso del `.log`, que abre el editor en su línea) e Historial. «Recompilar al guardar» vigila el `.tex` desde la
ventana (la CLI necesita inotifywait para su `-w`, que esta máquina no trae).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QFileSystemWatcher, QSettings, QStandardPaths, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
                               QSpinBox, QStackedWidget, QVBoxLayout, QWidget)

from gui_comun.diseno import clase, icono_trazo, variante
from gui_comun.theming import aplicar_tema, disenador_de
from gui_comun.widgets.console_dock import ConsoleDock
from gui_comun.widgets.marco import montar_studio
from gui_comun.widgets.paleta import Comando
from gui_comun.widgets.tarjetas import (Cifra, ListaConVacio, Mosaico, Tarjeta, encabezado, pagina_desplazable,
                                        rejilla_pareja, seccion)
from gui_comun.workers.process_worker import ProcessWorker

from latex_app.compilador import BIBLIOGRAFIAS, MOTORES, Opciones, leer_log, resumen

APP_VERSION = "1.0.0"
ACENTO = "rosa"
LOGO = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#888888" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round"><path d="M4 7V5h16v2M12 5v14M9 19h6"/></svg>')
MAX_RECIENTES = 12


class Ajustes:
    def __init__(self) -> None:
        self.q = QSettings()

    def theme(self) -> str:
        return str(self.q.value("ui/tema", "sistema"))

    def set_theme(self, tema: str) -> None:
        self.q.setValue("ui/tema", tema)

    def lista(self, clave: str) -> list:
        try:
            return json.loads(self.q.value(clave, "[]") or "[]")
        except ValueError:
            return []

    def guardar_lista(self, clave: str, valor: list) -> None:
        self.q.setValue(clave, json.dumps(valor, ensure_ascii=False))


class Ventana:
    """Envoltorio de la QMainWindow con la forma que `gui_comun.widgets.marco.montar_studio` espera."""

    def __init__(self) -> None:
        app = QApplication.instance()
        self.settings = Ajustes()
        disenador = disenador_de(app) or aplicar_tema(app, self.settings.theme(), acento=ACENTO)
        self.ui = QMainWindow()
        self.ui.setWindowTitle(f"LaTeX Studio {APP_VERSION}")
        self.ui.setAcceptDrops(True)
        central = QWidget()
        fila = QHBoxLayout(central)
        self.ui.sidebar = QListWidget()
        self.ui.stack = QStackedWidget()
        fila.addWidget(self.ui.sidebar)
        fila.addWidget(self.ui.stack, 1)
        self.ui.setCentralWidget(central)
        self.ui.statusbar = self.ui.statusBar()
        self.console = ConsoleDock(self.ui)
        self.ui.addDockWidget(Qt.BottomDockWidgetArea, self.console)
        self._workers: list = []
        self._en_curso: ProcessWorker | None = None
        self._inicio_compilacion = 0.0
        self.vigia = QFileSystemWatcher()
        self.vigia.fileChanged.connect(self._cambio_en_disco)
        self.espera = QTimer(singleShot=True, interval=900, timeout=self.compilar)

        self.controllers: dict[str, SimpleNamespace] = {}
        self._page_order: list[str] = []
        self._pagina("dashboard", "Inicio", "inicio", self._crear_inicio())
        self._pagina("compilar", "Compilar", "jugar", self._crear_compilar())
        self._pagina("historial", "Historial", "receta", self._crear_historial())
        self.ui.sidebar.currentRowChanged.connect(self._al_cambiar_pagina)
        self.ui.sidebar.setCurrentRow(0)

        self.marco = montar_studio(self, nombre="LaTeX Studio", subtitulo="Compilar documentos", logo_svg=LOGO,
                                   disenador=disenador, primarios={}, peligro=())
        self.marco.comandos_extra += [
            Comando("Abrir un .tex", self.elegir_tex, grupo="Archivo", icono=icono_trazo("documento"), atajo="Ctrl+O"),
            Comando("Compilar", self.compilar, grupo="Compilar", icono=icono_trazo("jugar"), atajo="F5",
                    palabras="lualatex biber pdf construir"),
            Comando("Simular la compilación", lambda: self.compilar(simular=True), grupo="Compilar",
                    palabras="dry-run probar"),
            Comando("Limpiar auxiliares", self.limpiar, grupo="Compilar", palabras="aux borrar"),
            Comando("Abrir el PDF", self.abrir_pdf, grupo="Compilar", icono=icono_trazo("pdf")),
        ]
        from PySide6.QtGui import QKeySequence, QShortcut
        self._atajos = [QShortcut(QKeySequence(k), self.ui, activated=f)
                        for k, f in (("F5", self.compilar), ("Ctrl+O", self.elegir_tex))]
        self.ui.dragEnterEvent = lambda e: e.acceptProposedAction() if e.mimeData().hasUrls() else None
        self.ui.dragMoveEvent = self.ui.dragEnterEvent
        self.ui.dropEvent = self._soltar
        self._pintar_recientes()
        self._pintar_historial()

    # ------------------------------------------------------------------------------------------------- páginas
    def _crear_inicio(self) -> QWidget:
        contenido = QWidget()
        raiz = QVBoxLayout(contenido)
        raiz.setSpacing(14)
        raiz.addWidget(encabezado("Inicio", "El .tex suelto, desde cualquier carpeta: LuaLaTeX y Biber por omisión, "
                                            "pasadas fijas, el PDF y los auxiliares fuera."))
        cifras = rejilla_pareja(3)
        self.cifra_recientes = Cifra("Recientes", "0", "Los últimos que compilaste")
        self.cifra_ultimo = Cifra("Última compilación", "—", "")
        self.cifra_motor = Cifra("Motor por omisión", "LuaLaTeX", "con Biber; «% !TEX program» manda")
        for i, c in enumerate((self.cifra_recientes, self.cifra_ultimo, self.cifra_motor)):
            cifras.addWidget(c, 0, i)
        raiz.addLayout(cifras)
        raiz.addSpacing(4)
        raiz.addWidget(seccion("Empezar"))
        mosaicos = rejilla_pareja(3)
        mosaicos.addWidget(Mosaico(icono_trazo("documento"), "Abrir un .tex", "Elige el archivo o suéltalo en la "
                                   "ventana (Ctrl+O)", self.elegir_tex), 0, 0)
        mosaicos.addWidget(Mosaico(icono_trazo("jugar"), "Compilar", "Opciones, errores con su línea y el PDF (F5)",
                                   lambda: self.navigate("compilar")), 0, 1)
        mosaicos.addWidget(Mosaico(icono_trazo("receta"), "Historial", "Cada compilación con su resultado",
                                   lambda: self.navigate("historial")), 0, 2)
        raiz.addLayout(mosaicos)
        raiz.addSpacing(4)
        tarjeta = Tarjeta("Recientes · doble clic para abrir")
        self.recientes = ListaConVacio("Todavía no compilaste nada aquí.\nSuelta un .tex en la ventana.")
        self.recientes.lista.itemDoubleClicked.connect(lambda it: self.cargar(it.data(Qt.UserRole)))
        tarjeta.cuerpo.addWidget(self.recientes, 1)
        tarjeta.setMinimumHeight(240)
        raiz.addWidget(tarjeta, 1)
        return pagina_desplazable(contenido)

    def _crear_compilar(self) -> QWidget:
        contenido = QWidget()
        raiz = QVBoxLayout(contenido)
        raiz.setSpacing(14)
        raiz.addWidget(encabezado("Compilar", "Cualquier .tex que no pertenezca a un framework (escritura, docencia y "
                                              "los libros compilan con su propio build)."))
        fila_tex = QHBoxLayout()
        self.ruta = QLineEdit()
        self.ruta.setPlaceholderText("Ruta del .tex…")
        self.ruta.returnPressed.connect(lambda: self.cargar(self.ruta.text()))
        b_abrir = QPushButton(icono_trazo("carpeta"), " Abrir…")
        b_abrir.clicked.connect(self.elegir_tex)
        b_simular = QPushButton("Simular")
        b_simular.setToolTip("Dice qué ejecutaría, sin escribir nada (-n)")
        b_simular.clicked.connect(lambda: self.compilar(simular=True))
        self.b_compilar = variante(QPushButton("Compilar"), "primario")
        self.b_compilar.setToolTip("F5 · Ctrl+Intro")
        self.b_compilar.setShortcut("Ctrl+Return")
        self.b_compilar.setMinimumWidth(130)
        self.b_compilar.clicked.connect(lambda: self.compilar())
        fila_tex.addWidget(self.ruta, 1)
        fila_tex.addWidget(b_abrir)
        fila_tex.addWidget(b_simular)
        fila_tex.addWidget(self.b_compilar)
        raiz.addLayout(fila_tex)

        fila = QHBoxLayout()
        fila.setSpacing(14)
        opciones = Tarjeta("Opciones")
        forma = QFormLayout()
        forma.setHorizontalSpacing(14)
        forma.setVerticalSpacing(10)
        self.motor = QComboBox()
        for m in MOTORES:
            self.motor.addItem({"auto": "Automático (LuaLaTeX)", "lualatex": "LuaLaTeX", "pdflatex": "pdfLaTeX "
                                "(heredado)", "xelatex": "XeLaTeX (heredado)"}[m], m)
        self.pasadas = QSpinBox()
        self.pasadas.setRange(1, 5)
        self.pasadas.setValue(2)
        self.bib = QComboBox()
        for valor, nombre in BIBLIOGRAFIAS:
            self.bib.addItem(nombre, valor)
        self.indice = QCheckBox("Índice (makeindex)")
        self.glosarios = QCheckBox("Glosarios (makeglossaries)")
        self.borrador = QCheckBox("Borrador: solo comprobar, sin PDF")
        self.salida = QLineEdit()
        self.salida.setPlaceholderText("junto al .tex")
        self.abrir_al_terminar = QCheckBox("Abrir el PDF al terminar")
        self.recompilar = QCheckBox("Recompilar al guardar el .tex")
        self.recompilar.toggled.connect(self._vigilar)
        forma.addRow("Motor", self.motor)
        forma.addRow("Pasadas", self.pasadas)
        forma.addRow("Bibliografía", self.bib)
        forma.addRow("", self.indice)
        forma.addRow("", self.glosarios)
        forma.addRow("", self.borrador)
        forma.addRow("Mover el PDF a", self.salida)
        forma.addRow("", self.abrir_al_terminar)
        forma.addRow("", self.recompilar)
        opciones.cuerpo.addLayout(forma)
        opciones.cuerpo.addStretch(1)
        fila.addWidget(opciones, 2)

        resultado = Tarjeta("Resultado")
        self.estado = clase(QLabel("Elige un .tex y compílalo (F5)."), "suave")
        self.estado.setWordWrap(True)
        resultado.cuerpo.addWidget(self.estado)
        self.problemas = ListaConVacio("Sin errores ni avisos.")
        self.problemas.lista.itemDoubleClicked.connect(self._ir_a_linea)
        self.problemas.lista.setToolTip("Doble clic: abre el editor en esa línea")
        resultado.cuerpo.addWidget(self.problemas, 1)
        botones = QHBoxLayout()
        self.b_pdf = variante(QPushButton(icono_trazo("pdf"), " Abrir el PDF"), "fantasma")
        self.b_pdf.clicked.connect(self.abrir_pdf)
        self.b_carpeta = variante(QPushButton(icono_trazo("abrir"), " Carpeta"), "fantasma")
        self.b_carpeta.clicked.connect(lambda: self._tex() and QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(self._tex().parent))))
        b_limpiar = variante(QPushButton("Limpiar auxiliares"), "peligro")
        b_limpiar.clicked.connect(self.limpiar)
        botones.addWidget(self.b_pdf)
        botones.addWidget(self.b_carpeta)
        botones.addStretch(1)
        botones.addWidget(b_limpiar)
        resultado.cuerpo.addLayout(botones)
        resultado.setMinimumHeight(360)
        fila.addWidget(resultado, 3)
        raiz.addLayout(fila, 1)

        return pagina_desplazable(contenido)

    def _crear_historial(self) -> QWidget:
        contenido = QWidget()
        raiz = QVBoxLayout(contenido)
        raiz.addWidget(encabezado("Historial", "Cada compilación, con su resultado y su tiempo (doble clic: volver a "
                                               "ese .tex)."))
        tarjeta = Tarjeta()
        self.historial = ListaConVacio("Sin compilaciones todavía.")
        self.historial.lista.itemDoubleClicked.connect(lambda it: self.cargar(it.data(Qt.UserRole)))
        tarjeta.cuerpo.addWidget(self.historial, 1)
        b_borrar = variante(QPushButton("Vaciar el historial"), "fantasma")
        b_borrar.clicked.connect(lambda: (self.settings.guardar_lista("historial", []), self._pintar_historial()))
        tarjeta.cuerpo.addWidget(b_borrar, 0, Qt.AlignRight)
        raiz.addWidget(tarjeta, 1)
        return pagina_desplazable(contenido)

    # ----------------------------------------------------------------------------------------------------- API
    def show(self) -> None:
        self.ui.show()

    def navigate(self, page_id: str) -> None:
        if page_id in self._page_order:
            self.ui.sidebar.setCurrentRow(self._page_order.index(page_id))

    def elegir_tex(self) -> None:
        inicio = str(self._tex().parent) if self._tex() else str(Path.home() / "Documents")
        ruta, _ = QFileDialog.getOpenFileName(self.ui, "Abrir un .tex", inicio, "LaTeX (*.tex)")
        if ruta:
            self.cargar(ruta)

    def cargar(self, ruta: str) -> None:
        p = Path(ruta).expanduser()
        if p.suffix != ".tex":
            p = p.with_suffix(".tex")
        if not p.is_file():
            self.marco.avisar("No existe ese .tex", str(p), "aviso")
            return
        self.ruta.setText(str(p))
        self.navigate("compilar")
        self._vigilar(self.recompilar.isChecked())
        self.estado.setText(f"{p.name} · listo para compilar (F5).")

    def compilar(self, simular: bool = False) -> None:
        tex = self._tex()
        if not tex:
            self.marco.avisar("Falta el .tex", "Ábrelo con Ctrl+O o suéltalo en la ventana.", "aviso")
            return
        if self._en_curso is not None:
            return
        self._log = Path(QStandardPaths.writableLocation(QStandardPaths.CacheLocation)) / f"{tex.stem}.log"
        self._log.parent.mkdir(parents=True, exist_ok=True)
        self._log.unlink(missing_ok=True)
        self._opciones = Opciones(tex, self.motor.currentData(), self.pasadas.value(), self.bib.currentData(),
                                  self.indice.isChecked(), self.glosarios.isChecked(), self.borrador.isChecked(),
                                  self.salida.text().strip(), self._log)
        self._correr(self._opciones.orden(simular=simular), f"{'Simular' if simular else 'Compilar'} {tex.name}",
                     simular)

    def limpiar(self) -> None:
        tex = self._tex()
        if not tex:
            return
        if QMessageBox.question(self.ui, "Limpiar auxiliares", f"¿Borrar los auxiliares de {tex.name} (.aux, .log, "
                                ".bbl…)? El .tex y el PDF no se tocan.") != QMessageBox.Yes:
            return
        self._opciones = Opciones(tex)
        self._correr(self._opciones.orden(limpiar=True), f"Limpiar {tex.name}", True)

    def abrir_pdf(self) -> None:
        if self._tex():
            pdf = Opciones(self._tex(), salida=self.salida.text().strip()).pdf()
            if pdf.is_file():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf)))
            else:
                self.marco.avisar("Todavía no hay PDF", pdf.name, "aviso")

    def run_function_worker(self, worker, nombre: str) -> None:   # lo pide el marco; aquí todo es proceso
        self.console.attach_function_worker(worker, nombre)
        self._workers.append(worker)
        worker.start()

    # -------------------------------------------------------------------------------------------------- privado
    def _correr(self, argv: list[str], nombre: str, sin_pdf: bool) -> None:
        tex = self._tex()
        worker = ProcessWorker(argv, cwd=str(tex.parent), description=nombre)
        self.console.attach_process_worker(worker, nombre)
        worker.finished_with_code.connect(lambda codigo: self._terminado(codigo, sin_pdf))
        self._en_curso = worker
        self._workers.append(worker)
        self._inicio_compilacion = time.monotonic()
        self.b_compilar.setEnabled(False)
        self.estado.setText(f"{nombre}…")
        worker.start()

    def _terminado(self, codigo: int, sin_pdf: bool) -> None:
        self._en_curso = None
        self.b_compilar.setEnabled(True)
        segundos = time.monotonic() - self._inicio_compilacion
        tex = self._tex()
        problemas = []
        log = getattr(self, "_log", None)
        if log and log.is_file():
            problemas = leer_log(log.read_text(encoding="utf-8", errors="replace"))
        self.problemas.lista.clear()
        iconos = {"error": "quitar", "aviso": "info", "tipografia": "texto"}
        for p in problemas:
            donde = f"línea {p.linea}" if p.linea else "sin línea"
            item = QListWidgetItem(icono_trazo(iconos[p.nivel] if iconos[p.nivel] != "info" else "subtitulos"),
                                   f"{p.mensaje}\n{p.nivel} · {donde}" + (f" · {p.archivo}" if p.archivo else ""))
            item.setData(Qt.UserRole, (p.archivo, p.linea))
            self.problemas.lista.addItem(item)
        self.problemas.actualizar()
        ok = codigo == 0
        pdf = self._opciones.pdf() if hasattr(self, "_opciones") else None
        if sin_pdf:
            self.estado.setText(("Hecho" if ok else "Falló") + f" en {segundos:.1f} s. Detalle en la consola (Ctrl+J).")
        elif ok and pdf and pdf.is_file():
            self.estado.setText(f"✓ {pdf.name} en {segundos:.1f} s · {resumen(problemas)}")
            if self.abrir_al_terminar.isChecked():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(pdf)))
        else:
            self.estado.setText(f"✕ No compiló ({segundos:.1f} s) · {resumen(problemas)}")
        self.cifra_ultimo.poner("✓" if ok else "✕", f"{tex.name} · {segundos:.1f} s" if tex else "")
        if tex and not sin_pdf:
            self._recordar(tex, ok, segundos, resumen(problemas))

    def _recordar(self, tex: Path, ok: bool, segundos: float, detalle: str) -> None:
        recientes = [str(tex)] + [r for r in self.settings.lista("recientes") if r != str(tex)]
        self.settings.guardar_lista("recientes", recientes[:MAX_RECIENTES])
        historial = [{"tex": str(tex), "ok": ok, "segundos": round(segundos, 1), "detalle": detalle,
                      "cuando": time.strftime("%Y-%m-%d %H:%M")}] + self.settings.lista("historial")
        self.settings.guardar_lista("historial", historial[:60])
        self._pintar_recientes()
        self._pintar_historial()

    def _pintar_recientes(self) -> None:
        self.recientes.lista.clear()
        recientes = [r for r in self.settings.lista("recientes") if Path(r).is_file()]
        for r in recientes:
            item = QListWidgetItem(icono_trazo("documento"), f"{Path(r).name}\n{Path(r).parent}")
            item.setData(Qt.UserRole, r)
            self.recientes.lista.addItem(item)
        self.recientes.actualizar()
        self.cifra_recientes.poner(str(len(recientes)))

    def _pintar_historial(self) -> None:
        self.historial.lista.clear()
        for h in self.settings.lista("historial"):
            item = QListWidgetItem(icono_trazo("pdf" if h["ok"] else "quitar"),
                                   f"{Path(h['tex']).name} · {'compiló' if h['ok'] else 'falló'} en {h['segundos']} s"
                                   f"\n{h['cuando']} · {h['detalle']} · {Path(h['tex']).parent}")
            item.setData(Qt.UserRole, h["tex"])
            self.historial.lista.addItem(item)
        self.historial.actualizar()

    def _ir_a_linea(self, item: QListWidgetItem) -> None:
        archivo, linea = item.data(Qt.UserRole)
        tex = self._tex()
        ruta = (tex.parent / archivo).resolve() if archivo and tex else tex
        if not ruta:
            return
        if shutil.which("kate"):
            subprocess.Popen(["kate", "--line", str(linea or 1), str(ruta)])
        elif shutil.which("code"):
            subprocess.Popen(["code", "-g", f"{ruta}:{linea or 1}"])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta)))

    def _vigilar(self, activo: bool) -> None:
        for f in self.vigia.files():
            self.vigia.removePath(f)
        if activo and self._tex():
            self.vigia.addPath(str(self._tex()))

    def _cambio_en_disco(self, ruta: str) -> None:
        if Path(ruta).exists() and ruta not in self.vigia.files():
            self.vigia.addPath(ruta)            # los editores guardan reemplazando: se vuelve a vigilar
        if self.recompilar.isChecked():
            self.espera.start()

    def _tex(self) -> Path | None:
        texto = self.ruta.text().strip()
        return Path(texto).expanduser() if texto else None

    def _soltar(self, e) -> None:
        tex = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile() and u.toLocalFile().endswith(".tex")]
        if tex:
            self.cargar(tex[0])
            e.acceptProposedAction()
        else:
            self.marco.avisar("Eso no es un .tex", "LaTeX Studio compila archivos .tex.", "aviso")

    def _pagina(self, id_: str, nombre: str, icono: str, widget) -> None:
        self.controllers[id_] = SimpleNamespace(widget=widget)
        self._page_order.append(id_)
        self.ui.stack.addWidget(widget)
        self.ui.sidebar.addItem(QListWidgetItem(icono_trazo(icono), nombre))

    def _al_cambiar_pagina(self, fila: int) -> None:
        self.ui.stack.setCurrentIndex(fila)
        if self._page_order[fila] == "dashboard":
            self._pintar_recientes()

    def _open_preferences(self) -> None:
        self.navigate("compilar")

    def _about(self) -> None:
        QMessageBox.about(self.ui, "Acerca de LaTeX Studio",
                          f"<b>LaTeX Studio</b> {APP_VERSION}<br><br>El compilador del .tex suelto del espacio de "
                          "trabajo, con ventana: LuaLaTeX + Biber, errores con su línea, recompilar al guardar.<br><br>"
                          "La CLI sigue siendo <code>script_compilar_latex/main.sh</code> (alias "
                          "<code>compilar</code>).<br><br>Edison Achalma")
