"""latex_app/controladores/proyectos.py — los proyectos detectados (la página de proyectos) y el proyecto abierto (la
barra lateral del espacio de escritura): archivos, estructura, bibliografía y etiquetas.

La detección corre en una tarea de `gui_comun.tareas` con progreso y se puede cancelar (R3); la tabla se filtra por
categoría (solo las que tienen proyectos, R6) y por texto. Abrir un proyecto carga su estructura y su bibliografía
para la barra lateral y para el autocompletado del editor. Solo lee: compilar es de `Compilacion`.
"""

from __future__ import annotations

from pathlib import Path

from gui_comun.modelos import ModeloFiltrado, ModeloLista, ModeloTabla
from gui_comun.qt import QObject, QSettings, QStandardPaths, Property, Signal, Slot

from latex_app import compilador as svc
from latex_app import estructura as est
from latex_app import proyectos as pr

COLUMNAS = [("Proyecto", "nombre"), ("Estado", "estado"), ("Motor", "motor"), ("Última compilación", "ultima"),
            ("Problemas", "problemas"), ("Bibliografía", "bib"), ("Auxiliares", "aux"), ("Categoría", "categoria"),
            ("Carpeta", "carpeta")]
ROLES_ARCHIVOS = ("ruta", "nombre", "relativa", "tipo", "icono", "existe")
ROLES_ESQUEMA = ("tipo", "orden", "titulo", "nivel", "archivo", "linea", "icono", "etiqueta")
ROLES_BIB = ("nombre", "tipo", "autor", "anio", "titulo", "archivo", "linea")
ICONOS_ESTADO = {"compilado": "dialog-ok-apply", "avisos": "data-warning", "errores": "data-error",
                 "desactualizado": "view-refresh", "sin_compilar": "dialog-cancel", "compilando": "system-run"}
ORDEN_ESTADO = {"errores": 0, "avisos": 1, "desactualizado": 2, "sin_compilar": 3, "compilado": 4, "compilando": 5}
TODAS = "Todas"
RECIENTES = "Recientes"


def cache_del_studio() -> Path:
    return Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation) or (Path.home() / ".cache" / "latex-studio"))


def texto_problemas(p: pr.Proyecto) -> str:
    partes = [f"{p.errores} error" + ("" if p.errores == 1 else "es") if p.errores else "",
              f"{p.avisos} aviso" + ("" if p.avisos == 1 else "s") if p.avisos else ""]
    return " · ".join(x for x in partes if x) or ("—" if not p.log else "ninguno")


def fila_proyecto(p: pr.Proyecto, en_curso: str = "") -> dict:
    """Una fila de la tabla de proyectos (columnas y roles para `TablaDatos`)."""
    clave = "compilando" if p.principal == en_curso else p.estado
    texto, nivel = svc.ESTADOS[clave]
    try:
        relativa = str(Path(p.principal).relative_to(p.raiz))
    except ValueError:
        relativa = p.principal
    motor = p.texto_motor() + ("" if p.compilador == "main.sh" else " · " + ("marco" if p.compilador == "marco" else "latexmk"))
    return {"nombre": relativa, "estado": texto, "motor": motor,
            "ultima": svc.fecha_legible(p.pdf_mtime) if p.pdf_mtime else "nunca",
            "problemas": texto_problemas(p), "bib": str(len(p.bibs)) if p.bibs else "—",
            "aux": str(p.auxiliares) if p.auxiliares else "—", "categoria": p.categoria, "carpeta": p.carpeta,
            "ruta": p.principal, "titulo": p.titulo, "clave": clave, "nivel": nivel, "habilitado": True,
            "icono": {"nombre": "text-x-tex", "estado": ICONOS_ESTADO[clave]},
            "crudo": {"estado": ORDEN_ESTADO[clave], "ultima": p.pdf_mtime, "problemas": p.errores * 1000 + p.avisos,
                      "bib": len(p.bibs), "aux": p.auxiliares}}


class Proyectos(QObject):
    cambiado = Signal()                  # la tabla, las categorías, los recuentos
    abiertoCambiado = Signal()           # el proyecto abierto y sus modelos
    detectando = Signal(bool)
    aviso = Signal(str, str)

    def __init__(self, ajustes, historial, consola, tareas, cache: Path | None = None, parent=None):
        super().__init__(parent)
        self.ajustes, self.historial, self.consola, self.tareas = ajustes, historial, consola, tareas
        self._s = QSettings()
        self._cache_dir = cache or cache_del_studio()
        self._cache = pr.Cache(self._cache_dir / "proyectos.json")
        self._proyectos: list[pr.Proyecto] = []
        self._por_ruta: dict[str, pr.Proyecto] = {}
        self._tabla = ModeloTabla(COLUMNAS, parent=self)
        self._modelo = ModeloFiltrado(self._tabla, parent=self)
        self._categoria = TODAS
        self._modelo.aceptar_con(self._acepta)
        self._archivos = ModeloLista(ROLES_ARCHIVOS, parent=self)
        self._esquema = ModeloLista(ROLES_ESQUEMA, parent=self)
        self._esquema_filtrado = ModeloFiltrado(self._esquema, parent=self)
        self._bib = ModeloLista(ROLES_BIB, parent=self)
        self._bib_filtrada = ModeloFiltrado(self._bib, parent=self)
        self._abierto: pr.Proyecto | None = None
        self._etiquetas: list[dict] = []
        self._claves: list[dict] = []
        self._ordenes: list[str] = []
        self._archivos_proyecto: list[str] = []       # .tex, .bib e imágenes del abierto (para completar argumentos)
        self._entornos: list[str] = []
        self._en_curso = ""
        self._worker = None
        self._detectado = False
        ajustes.carpetasCambiadas.connect(self.detectar)
        historial.recientesCambiados.connect(self._recientes_cambiaron)

    modelo = Property(QObject, lambda self: self._modelo, constant=True)
    archivos = Property(QObject, lambda self: self._archivos, constant=True)
    esquema = Property(QObject, lambda self: self._esquema_filtrado, constant=True)
    bibliografia = Property(QObject, lambda self: self._bib_filtrada, constant=True)

    # ---------------------------------------------------------------------------------------------------- detección
    def registro_de(self, tex: Path) -> Path:
        """El registro de la ventana para un principal compilado con `main.sh` (`--log`, en la caché del studio)."""
        return svc.registro_de(tex, self._cache_dir)

    @Slot()
    def detectar(self) -> None:
        """Recorre las carpetas de trabajo en una tarea con progreso (Esc la cancela)."""
        if self._worker is not None:
            return
        raices = self.ajustes.raices()
        if not raices:
            self._poner([])
            self.aviso.emit("No hay carpetas de trabajo: añade una en Ajustes › Carpetas de trabajo (Ctrl+Mayús+O).", "aviso")
            return
        profundidad, despacho, cache = self.ajustes.profundidad, self.ajustes.despacho(), self._cache
        registro_de = self.registro_de

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return pr.detectar(raices, profundidad, cache, progreso=progress_cb, cancelado=cancel_cb,
                               registro_de=registro_de, despacho=despacho)

        self.detectando.emit(True)
        self._worker = self.tareas.funcion("Buscando proyectos LaTeX", trabajo, al_terminar=self._fin_detectar,
                                           al_fallar=self._fallo_detectar)
        self.cambiado.emit()

    def _fin_detectar(self, proyectos) -> None:
        self._worker = None
        self._detectado = True
        self._poner(proyectos or [])
        self.detectando.emit(False)
        self.consola.registrar("info", f"{len(self._proyectos)} proyectos en " + ", ".join(n for n, _r in self.ajustes.raices()))

    def _fallo_detectar(self, error) -> None:
        self._worker = None
        self.detectando.emit(False)
        self.aviso.emit(f"No se pudieron recorrer las carpetas de trabajo: {error}", "error")
        self.cambiado.emit()

    def detectar_ya(self) -> None:
        """La detección en el hilo actual (pruebas y capturas)."""
        self._poner(pr.detectar(self.ajustes.raices(), self.ajustes.profundidad, self._cache, registro_de=self.registro_de,
                                despacho=self.ajustes.despacho()))
        self._detectado = True

    def _poner(self, proyectos: list[pr.Proyecto]) -> None:
        self._proyectos = sorted(proyectos, key=lambda p: (pr.CATEGORIAS.index(p.categoria), p.principal))
        self._por_ruta = {p.principal: p for p in self._proyectos}
        self._tabla.poner([fila_proyecto(p, self._en_curso) for p in self._proyectos])
        if self._abierto is not None and self._abierto.principal in self._por_ruta:
            self._abierto = self._por_ruta[self._abierto.principal]
            self.abiertoCambiado.emit()
        self.cambiado.emit()

    @Property(bool, notify=cambiado)
    def enDeteccion(self) -> bool:
        return self._worker is not None

    @Property(bool, notify=cambiado)
    def detectado(self) -> bool:
        return self._detectado

    @Property(int, notify=cambiado)
    def total(self) -> int:
        return len(self._proyectos)

    def proyecto(self, ruta: str) -> pr.Proyecto | None:
        return self._por_ruta.get(ruta) or (self._abierto if self._abierto and self._abierto.principal == ruta else None)

    def todos(self) -> list[pr.Proyecto]:
        return list(self._proyectos)

    # ---------------------------------------------------------------------------------------------------- categorías
    def _acepta(self, fila: int) -> bool:
        if self._categoria == TODAS:
            return True
        f = self._tabla.fila(fila)
        if self._categoria == RECIENTES:
            return f.get("ruta") in set(self.historial.recientes())
        return f.get("categoria") == self._categoria

    @Property(str, notify=cambiado)
    def categoria(self) -> str:
        return self._categoria

    @Slot(str)
    def fijarCategoria(self, categoria: str) -> None:
        if categoria != self._categoria:
            self._categoria = categoria
            self._modelo.aceptar_con(self._acepta)
            self.cambiado.emit()

    @Property("QVariantList", notify=cambiado)
    def categorias(self) -> list:
        """Las filas de la navegación: Todas, Recientes y cada categoría con proyectos (ninguna vacía, R6)."""
        cuenta = {c: 0 for c in pr.CATEGORIAS}
        for p in self._proyectos:
            cuenta[p.categoria] += 1
        recientes = set(self.historial.recientes())
        filas = [{"nombre": TODAS, "texto": "Todos los proyectos", "icono": "view-list-details", "contador": len(self._proyectos)},
                 {"nombre": RECIENTES, "texto": "Recientes", "icono": "document-open-recent",
                  "contador": sum(1 for p in self._proyectos if p.principal in recientes)}]
        iconos = ["document-edit", "school", "document-new", "view-pim-journal", "view-pim-mail", "run-build-prune", "folder-documents"]
        filas += [{"nombre": c, "texto": c, "icono": iconos[i], "contador": cuenta[c]} for i, c in enumerate(pr.CATEGORIAS) if cuenta[c]]
        return filas

    @Property("QVariantMap", notify=cambiado)
    def recuento(self) -> dict:
        c = {k: 0 for k in svc.ESTADOS}
        for p in self._proyectos:
            c[p.estado] = c.get(p.estado, 0) + 1
        c["total"] = len(self._proyectos)
        return c

    def _recientes_cambiaron(self) -> None:
        if self._categoria == RECIENTES:
            self._modelo.aceptar_con(self._acepta)
        self.cambiado.emit()

    # ---------------------------------------------------------------------------------------------------- filas
    @Slot(int, result=str)
    def rutaDeFila(self, fila_visible: int) -> str:
        if fila_visible < 0:
            return ""
        return self._tabla.fila(self._modelo.filaOrigen(fila_visible)).get("ruta", "")

    @Slot("QVariantList", result="QVariantList")
    def rutasDeFilas(self, filas: list) -> list:
        return [r for r in (self.rutaDeFila(int(f)) for f in filas) if r]

    @Slot(str, result=int)
    def filaDe(self, ruta: str) -> int:
        for i, f in enumerate(self._tabla.todas()):
            if f.get("ruta") == ruta:
                return self._modelo.filaVisible(i)
        return -1

    @Slot(str, result="QVariantMap")
    def datos(self, ruta: str) -> dict:
        """Todo lo de un proyecto para la ficha de la página de proyectos."""
        p = self.proyecto(ruta)
        if p is None:
            return {}
        d = p.a_dict()
        d.update(fila_proyecto(p, self._en_curso))
        d["compilador_texto"] = pr.NOMBRES_COMPILADOR.get(p.compilador, p.compilador)
        d["orden"] = svc.orden_legible(svc.receta(p, "compilar", self.registro_de(Path(p.principal)), self.ajustes.rutasTex))
        d["n_archivos"] = len(p.archivos) + 1
        return d

    def refrescar(self, ruta: str, en_curso: bool | None = None) -> pr.Proyecto | None:
        """Vuelve a leer el estado de un proyecto (tras compilar o limpiar) y su fila; si es el abierto, sus modelos."""
        if en_curso is not None:
            self._en_curso = ruta if en_curso else ""
        p = self.proyecto(ruta)
        if p is None:
            return None
        nuevo = pr.construir(Path(p.principal), Path(p.raiz), self._cache, en_despacho=False)
        nuevo.categoria, nuevo.categoria_motivo = p.categoria, p.categoria_motivo
        pr.leer_estado(nuevo, self._cache, self.registro_de(Path(p.principal)))
        if ruta in self._por_ruta:
            i = self._proyectos.index(self._por_ruta[ruta])
            self._proyectos[i] = nuevo
            self._por_ruta[ruta] = nuevo
            for j, f in enumerate(self._tabla.todas()):
                if f.get("ruta") == ruta:
                    self._tabla.actualizar(j, **fila_proyecto(nuevo, self._en_curso))
        if self._abierto is not None and self._abierto.principal == ruta:
            self._abierto = nuevo
            self._cargar_abierto(estructura=False)
        self.cambiado.emit()
        return nuevo

    # ---------------------------------------------------------------------------------------------------- el abierto
    @Slot(str, result=str)
    def abrir(self, ruta: str) -> str:
        """Abre un proyecto por su principal, o por cualquier `.tex` (Ctrl+O): un capítulo con `% !TEX root` abre su
        raíz; un `.tex` sin clase que algún proyecto incluye abre ese proyecto. Devuelve el error, o vacío."""
        ruta = str(Path(ruta).expanduser().resolve()) if ruta else ""
        p = self._por_ruta.get(ruta)
        if p is None and ruta:
            p = next((q for q in self._proyectos if ruta in q.archivos), None)
        if p is None and ruta:
            p = pr.proyecto_de(Path(ruta), self._cache)
            if p is not None:
                p.categoria, p.categoria_motivo = "Otros proyectos", "abierto suelto"
        if p is None:
            return f"No es un documento LaTeX con \\documentclass ni pertenece a un proyecto conocido: {ruta}"
        self._abierto = p
        self._s.setValue("abierto", p.principal)
        self.historial.recordar(Path(p.principal))
        self._cargar_abierto()
        self.consola.registrar("info", f"Proyecto: {p.principal}")
        return ""

    @Slot()
    def cerrar(self) -> None:
        self._abierto = None
        for m in (self._archivos, self._esquema, self._bib):
            m.poner([])
        self.abiertoCambiado.emit()

    def ultimo_abierto(self) -> str:
        return str(self._s.value("abierto", "") or "")

    def _cargar_abierto(self, estructura: bool = True) -> None:
        p = self._abierto
        carpeta = Path(p.carpeta)

        def fila(ruta: str, tipo: str, icono: str) -> dict:
            try:
                relativa = str(Path(ruta).relative_to(carpeta))
            except ValueError:
                relativa = ruta
            return {"ruta": ruta, "nombre": Path(ruta).name, "relativa": relativa, "tipo": tipo, "icono": icono, "existe": Path(ruta).is_file()}

        filas = [fila(p.principal, "principal", "text-x-tex")]
        filas += [fila(a, "incluido", "text-x-tex") for a in p.archivos]
        filas += [fila(b, "bibliografía", "text-x-bibtex") for b in p.bibs]
        filas += [fila(c, "configuración", "configure") for c in p.configuracion]
        self._archivos.poner(filas)
        if estructura:
            self.releerEstructura()
        self.abiertoCambiado.emit()

    @Slot()
    def releerEstructura(self) -> None:
        """La estructura, las etiquetas, la bibliografía y las definiciones del abierto (al abrir y al guardar)."""
        p = self._abierto
        if p is None:
            return
        fuentes = p.fuentes()
        self._esquema.poner(est.esquema(p.principal))
        self._etiquetas = est.etiquetas([f for f in fuentes if f.endswith(".tex")])
        self._claves = est.claves_bib(p.bibs)
        self._bib.poner(self._claves)
        self._ordenes, self._entornos = est.definiciones([f for f in fuentes if f.endswith(".tex")])
        self._archivos_proyecto = est.archivos_de(p.carpeta)
        self.abiertoCambiado.emit()

    @Slot(str)
    def filtrarEstructura(self, texto: str) -> None:
        self._esquema_filtrado.filtrar(texto)

    @Slot(str)
    def filtrarBibliografia(self, texto: str) -> None:
        self._bib_filtrada.filtrar(texto)

    @Slot(str, result="QVariantMap")
    def completar(self, antes: str) -> dict:
        """El autocompletado en el cursor (órdenes, entornos, `\\ref`, `\\cite`) con lo del proyecto abierto."""
        p = self._abierto
        return est.completar(antes, self._etiquetas, self._claves, self._ordenes, self._entornos,
                             archivos=self._archivos_proyecto, paquetes_extra=list(p.paquetes) if p else [])

    def _abierto_dict(self) -> dict:
        return self.datos(self._abierto.principal) if self._abierto else {}

    @Property(bool, notify=abiertoCambiado)
    def hayAbierto(self) -> bool:
        return self._abierto is not None

    @Property(str, notify=abiertoCambiado)
    def principal(self) -> str:
        return self._abierto.principal if self._abierto else ""

    @Property(str, notify=abiertoCambiado)
    def nombreAbierto(self) -> str:
        if not self._abierto:
            return ""
        return Path(self._abierto.carpeta).name + " · " + self._abierto.nombre

    @Property("QVariantMap", notify=abiertoCambiado)
    def abierto(self) -> dict:
        return self._abierto_dict()

    @Property(int, notify=abiertoCambiado)
    def nEtiquetas(self) -> int:
        return len(self._etiquetas)

    @Property(int, notify=abiertoCambiado)
    def nClaves(self) -> int:
        return len(self._claves)

    def proyecto_abierto(self) -> pr.Proyecto | None:
        return self._abierto
