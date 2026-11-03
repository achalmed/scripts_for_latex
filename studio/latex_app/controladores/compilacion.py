"""latex_app/controladores/compilacion.py — compilar, reconstruir, limpiar y simular un proyecto con su compilador (R5,
R8), la cola de varios proyectos (R15), los problemas con causa probable y acción (R9) y la revisión de dependencias
(R16). Cada paso es un proceso de `gui_comun.tareas` con su salida íntegra en el panel inferior; nunca se escribe una
fuente; «Limpiar» lo confirma QML con la lista exacta de lo que se borraría.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from gui_comun.modelos import ModeloFiltrado, ModeloLista
from gui_comun.qt import QObject, Property, Signal, Slot

from latex_app import compilador as svc
from latex_app import diagnostico as dg

ROLES_PROBLEMAS = ("nivel", "mensaje", "archivo", "linea", "titulo", "causa", "accion", "detalle", "relativa")
ROLES_COLA = ("ruta", "nombre", "estado", "detalle", "icono")
_PASO = re.compile(r"(?:Pasada|\(|^\S+\s+\()\s*(\d+)\s*/\s*(\d+)")


def progreso_de_linea(texto: str):
    """«Pasada n/N» (main.sh) o «lualatex (n/N)» (un compilador de marco) → (porcentaje, «pasada n de N»)."""
    m = _PASO.search(texto)
    if not m:
        return None
    n, total = int(m.group(1)), int(m.group(2))
    if total <= 0 or n > total:
        return None
    return (int((n - 1) * 100 / total), f"pasada {n} de {total}")


def contexto(texto: str, mensaje: str, lineas: int = 8) -> str:
    """Las líneas del registro alrededor de un mensaje (el detalle técnico desplegable del problema)."""
    clave = mensaje[:40]
    filas = texto.splitlines()
    for i, l in enumerate(filas):
        if clave and clave in l:
            return "\n".join(filas[max(0, i - 1):i + lineas])
    return ""


class Compilacion(QObject):
    cambiado = Signal()
    problemasCambiados = Signal()
    terminada = Signal(str, bool)            # principal, si compiló
    irA = Signal(str, int)                   # archivo, línea (F8, o elegir un problema)
    aviso = Signal(str, str)

    def __init__(self, proyectos, historial, ajustes, consola, tareas, parent=None):
        super().__init__(parent)
        self.proyectos, self.historial, self.ajustes, self.consola, self.tareas = proyectos, historial, ajustes, consola, tareas
        self._problemas = ModeloLista(ROLES_PROBLEMAS, parent=self)
        self._problemas_filtrados = ModeloFiltrado(self._problemas, parent=self)
        self._mostrar = {"error": True, "aviso": True, "tipografia": False}
        self._problemas_filtrados.aceptar_con(self._acepta)
        self._cola = ModeloLista(ROLES_COLA, parent=self)
        self._pendientes: list[tuple[str, str]] = []       # (principal, qué)
        self._lote = {"total": 0, "ok": 0, "fallos": []}    # la cola en curso: un solo aviso al terminar
        self._pasos: list = []
        self._ruta = ""
        self._que = ""
        self._inicio = 0.0
        self._worker = None
        self._origen = ""                                  # compilacion · dependencias
        self._registro = ""
        self._registro_texto = ""
        self._ruta_problemas = ""
        self._siguiente = -1
        tareas.cambiada.connect(self.cambiado)

    problemas = Property(QObject, lambda self: self._problemas_filtrados, constant=True)
    cola = Property(QObject, lambda self: self._cola, constant=True)

    # ---------------------------------------------------------------------------------------------------- estado
    @Property(bool, notify=cambiado)
    def enCurso(self) -> bool:
        return self._worker is not None

    @Property(str, notify=cambiado)
    def rutaEnCurso(self) -> str:
        return self._ruta if self._worker is not None else ""

    @Property(str, notify=cambiado)
    def que(self) -> str:
        return self._que if self._worker is not None else ""

    @Property(int, notify=cambiado)
    def enCola(self) -> int:
        return len(self._pendientes)

    def _objetivo(self, ruta: str) -> str:
        return ruta or self.proyectos.principal

    # ---------------------------------------------------------------------------------------------------- lanzar
    @Slot(result=bool)
    def compilar(self) -> bool:
        """F5 / Ctrl+B: el proyecto abierto con su compilador."""
        return self.lanzar(self.proyectos.principal, "compilar")

    @Slot(result=bool)
    def reconstruir(self) -> bool:
        """F6: limpia los auxiliares y compila de nuevo (Biber incluido)."""
        return self.lanzar(self.proyectos.principal, "reconstruir")

    @Slot(result=bool)
    def borrador(self) -> bool:
        """Comprueba que compila sin producir PDF (`main.sh --draft`; solo con script_compilar_latex)."""
        return self.lanzar(self.proyectos.principal, "borrador")

    @Slot(result=bool)
    def simular(self) -> bool:
        return self.lanzar(self.proyectos.principal, "simular")

    @Slot(str, str, result=bool)
    def lanzar(self, ruta: str, que: str) -> bool:
        ruta = self._objetivo(ruta)
        if not ruta:
            self.aviso.emit("Abre un proyecto (Ctrl+O o doble clic en la página de proyectos).", "aviso")
            return False
        if self._worker is not None or self.tareas.activa:
            self._pendientes.append((ruta, que))
            self._pintar_cola()
            self.aviso.emit(f"En cola: {Path(ruta).name} (hay una compilación en curso).", "informacion")
            return True
        return self._empezar(ruta, que)

    @Slot("QVariantList", result=int)
    def encolar(self, rutas: list) -> int:
        """Compila varios proyectos uno tras otro, cada uno con su compilador (la cola se ve en el panel inferior)."""
        rutas = [str(r) for r in rutas if r]
        if not rutas:
            return 0
        if len(rutas) > 1:
            self._lote = {"total": self._lote["total"] + len(rutas), "ok": self._lote["ok"], "fallos": self._lote["fallos"]}
        self._pendientes.extend((r, "compilar") for r in rutas)
        self._pintar_cola()
        if self._worker is None and not self.tareas.activa:
            r, q = self._pendientes.pop(0)
            self._empezar(r, q)
        return len(rutas)

    def _pintar_cola(self) -> None:
        filas = [f for f in self._cola.todas() if f["estado"] in ("compiló", "falló")][-20:]
        if self._worker is not None and self._ruta:
            filas.append({"ruta": self._ruta, "nombre": Path(self._ruta).name, "estado": "compilando", "detalle": self._que, "icono": "system-run"})
        filas += [{"ruta": r, "nombre": Path(r).name, "estado": "pendiente", "detalle": q, "icono": "view-pim-tasks-pending"}
                  for r, q in self._pendientes]
        self._cola.poner(filas)
        self.cambiado.emit()

    def _empezar(self, ruta: str, que: str) -> bool:
        p = self.proyectos.proyecto(ruta)
        if p is None:
            self.aviso.emit(f"No es un proyecto detectado: {ruta}", "error")
            return False
        registro = self.proyectos.registro_de(Path(p.principal)) if p.compilador == "main.sh" else None
        if registro is not None and que != "simular":
            registro.parent.mkdir(parents=True, exist_ok=True)
            registro.unlink(missing_ok=True)
        self._pasos = svc.receta(p, que, registro, self.ajustes.rutasTex)
        self._ruta, self._que, self._inicio = p.principal, que, time.monotonic()
        self._registro = str(registro) if registro else ""
        if que == "borrador" and p.compilador != "main.sh":
            que = self._que = "compilar"
        if que in ("compilar", "reconstruir", "borrador"):
            self.proyectos.refrescar(p.principal, en_curso=True)
        self._siguiente_paso()
        return True

    def _siguiente_paso(self) -> None:
        paso = self._pasos.pop(0)
        nombre = f"{paso.descripcion}: {Path(self._ruta).name}"
        self._worker = self.tareas.proceso(nombre, paso.argv, cwd=paso.cwd, entorno=paso.entorno or None,
                                           progreso_de=progreso_de_linea,
                                           al_terminar=lambda codigo: self._fin_paso(codigo))
        # un error de compilación lo presenta Problemas (con su causa y su acción), no el diálogo genérico de gui-comun 3.0
        self._worker.error_presentable = False
        self._pintar_cola()

    def _fin_paso(self, codigo: int) -> None:
        if codigo == 0 and self._pasos:
            self._siguiente_paso()
            return
        self._worker = None
        ruta, que = self._ruta, self._que
        segundos = time.monotonic() - self._inicio
        if que == "simular":
            self.aviso.emit(f"Simulación de {Path(ruta).name}: la orden está en la salida (F4).", "informacion")
        elif que == "limpiar":
            self.proyectos.refrescar(ruta, en_curso=False)
            self.aviso.emit(f"Auxiliares de {Path(ruta).name} eliminados." if codigo == 0 else
                            f"La limpieza de {Path(ruta).name} terminó con código {codigo}.", "positivo" if codigo == 0 else "error")
        else:
            p = self.proyectos.refrescar(ruta, en_curso=False)
            ok = codigo == 0 and (que == "borrador" or (p is not None and bool(p.pdf) and p.pdf_mtime >= time.time() - segundos - 5))
            n_err, n_av = (p.errores, p.avisos) if p is not None else (0, 0)
            detalle = svc.resumen([svc.Problema("error", "")] * n_err + [svc.Problema("aviso", "")] * n_av)
            if ruta == self.proyectos.principal or not self.proyectos.hayAbierto:
                self._leer_problemas(ruta)          # Problemas es del proyecto abierto; la cola guarda el resto
            self.historial.anotar(Path(ruta), ok, segundos, detalle, n_err, n_av)
            en_lote = self._lote["total"] > 0
            if en_lote:
                self._lote["ok"] += 1 if ok else 0
                if not ok:
                    self._lote["fallos"].append(Path(ruta).name)
            elif ok and que == "borrador":
                self.aviso.emit(f"{Path(ruta).name} compila (borrador, sin PDF) en {segundos:.1f} s · {detalle}.", "positivo")
            elif ok:
                self.aviso.emit(f"{Path(ruta).stem}.pdf en {segundos:.1f} s · {detalle}.", "positivo" if not n_err and not n_av else "informacion")
            else:
                self.aviso.emit(f"{Path(ruta).name} no compiló ({segundos:.1f} s) · {detalle}: revisa Problemas (F8 va al siguiente).", "error")
            filas = self._cola.todas()
            for i, f in enumerate(filas):
                if f["ruta"] == ruta and f["estado"] == "compilando":
                    self._cola.actualizar(i, estado="compiló" if ok else "falló", detalle=detalle,
                                          icono="dialog-ok-apply" if ok else "data-error")
            self.terminada.emit(ruta, ok)
        self.cambiado.emit()
        if self._pendientes:
            r, q = self._pendientes.pop(0)
            self._empezar(r, q)
        else:
            self._pintar_cola()
            self._cerrar_lote()

    def _cerrar_lote(self) -> None:
        lote, self._lote = self._lote, {"total": 0, "ok": 0, "fallos": []}
        if lote["total"] <= 0:
            return
        if lote["fallos"]:
            self.aviso.emit(f"Cola terminada: {lote['ok']} de {lote['total']} compilaron; fallaron {', '.join(lote['fallos'])} (panel inferior › Cola).", "error")
        else:
            self.aviso.emit(f"Cola terminada: los {lote['total']} proyectos compilaron.", "positivo")

    @Slot()
    def cancelar(self) -> None:
        """Esc: detiene la compilación en curso y vacía la cola."""
        self._pendientes.clear()
        self._lote = {"total": 0, "ok": 0, "fallos": []}
        if self._worker is not None:
            self._pasos = []
            self.tareas.cancelar()
        self._pintar_cola()

    # ---------------------------------------------------------------------------------------------------- limpiar
    @Slot(str, result="QVariantList")
    def auxiliaresParaLimpiar(self, ruta: str = "") -> list:
        """Lo que la limpieza borraría (la lista del diálogo, antes de borrar): nunca un .tex, un .bib ni el PDF."""
        p = self.proyectos.proyecto(self._objetivo(ruta))
        if p is None:
            return []
        tex = Path(p.principal)
        if p.compilador == "marco":
            carpeta = tex.parent / (p.carpeta_aux or ".build")
            return [str(f.relative_to(tex.parent)) for f in sorted(carpeta.rglob("*")) if f.is_file()] if carpeta.is_dir() else []
        carpeta = tex.parent / p.carpeta_aux if p.carpeta_aux else tex.parent
        salida = [f for f in (carpeta / f"{tex.stem}.{e}" for e in svc.extensiones_auxiliares()) if f.is_file()]
        if p.compilador == "main.sh":
            salida = svc.auxiliares_de(tex)
        return [str(f.relative_to(tex.parent)) for f in salida]

    @Slot(str, result=bool)
    def limpiar(self, ruta: str = "") -> bool:
        """Borra los auxiliares (QML ya confirmó con la lista). El .tex, los .bib y el PDF no se tocan."""
        return self.lanzar(self._objetivo(ruta), "limpiar")

    # ---------------------------------------------------------------------------------------------------- problemas
    def _acepta(self, fila: int) -> bool:
        return self._mostrar.get(self._problemas.fila(fila).get("nivel", ""), True)

    def _fijar_mostrar(self, nivel: str, v: bool) -> None:
        if self._mostrar[nivel] != bool(v):
            self._mostrar[nivel] = bool(v)
            self._problemas_filtrados.aceptar_con(self._acepta)
            self.problemasCambiados.emit()

    mostrarErrores = Property(bool, lambda self: self._mostrar["error"], lambda self, v: self._fijar_mostrar("error", v), notify=problemasCambiados)
    mostrarAvisos = Property(bool, lambda self: self._mostrar["aviso"], lambda self, v: self._fijar_mostrar("aviso", v), notify=problemasCambiados)
    mostrarTipografia = Property(bool, lambda self: self._mostrar["tipografia"], lambda self, v: self._fijar_mostrar("tipografia", v), notify=problemasCambiados)

    def _texto_registro(self, p) -> tuple[str, str, bool]:
        """(texto, ruta, es_registro_de_la_ventana) del registro más reciente del proyecto."""
        candidatos = []
        if p.compilador == "main.sh":
            r = self.proyectos.registro_de(Path(p.principal))
            if r.is_file():
                candidatos.append((r, True))
        motor = svc.registro_motor(p)
        if motor.is_file():
            candidatos.append((motor, False))
        if not candidatos:
            return "", "", False
        ruta, propio = max(candidatos, key=lambda c: c[0].stat().st_mtime)
        return svc.leer_registro(ruta), str(ruta), propio

    @Slot(str)
    def leerProblemas(self, ruta: str = "") -> None:
        self._leer_problemas(self._objetivo(ruta))

    def _leer_problemas(self, ruta: str) -> None:
        p = self.proyectos.proyecto(ruta)
        if p is None:
            self._problemas.poner([])
            self._origen, self._registro_texto, self._ruta_problemas = "", "", ""
            self.problemasCambiados.emit()
            return
        texto, origen, propio = self._texto_registro(p)
        problemas = svc.problemas_de_registro(texto) if propio else svc.leer_log(texto)
        if p.bibliografia == "biber" and origen:
            problemas = svc.con_blg(problemas, svc.registro_motor(p).with_suffix(".blg"), texto, Path(origen).stat().st_mtime, propio)
        carpeta = Path(p.carpeta)
        filas = []
        for x in problemas:
            archivo = x.archivo
            if archivo:
                ruta_abs = Path(archivo) if os.path.isabs(archivo) else carpeta / archivo
                if not ruta_abs.is_file() and archivo.endswith(".bib"):          # Biber da solo el nombre del .bib
                    ruta_abs = next((Path(b) for b in p.bibs if Path(b).name == Path(archivo).name), ruta_abs)
                archivo = os.path.normpath(ruta_abs) if ruta_abs.is_file() else p.principal
            else:
                archivo = p.principal
            e = dg.explicar(x.nivel, x.mensaje)
            try:
                relativa = str(Path(archivo).relative_to(carpeta))
            except ValueError:
                relativa = Path(archivo).name
            filas.append({"nivel": x.nivel, "mensaje": x.mensaje, "archivo": archivo, "linea": x.linea or 0, "titulo": e["titulo"],
                          "causa": e["causa"], "accion": e["accion"], "detalle": contexto(texto, x.mensaje), "relativa": relativa})
        self._problemas.poner(filas)
        self._origen, self._registro_texto, self._ruta_problemas = origen, texto, ruta
        self._siguiente = -1
        self.problemasCambiados.emit()

    @Property(str, notify=problemasCambiados)
    def registro(self) -> str:
        return self._registro_texto

    @Property(str, notify=problemasCambiados)
    def origenRegistro(self) -> str:
        return self._origen

    @Property(int, notify=problemasCambiados)
    def nErrores(self) -> int:
        return sum(1 for f in self._problemas.todas() if f["nivel"] == "error")

    @Property(int, notify=problemasCambiados)
    def nAvisos(self) -> int:
        return sum(1 for f in self._problemas.todas() if f["nivel"] == "aviso")

    @Property(int, notify=problemasCambiados)
    def nTipografia(self) -> int:
        return sum(1 for f in self._problemas.todas() if f["nivel"] == "tipografia")

    @Property(int, notify=problemasCambiados)
    def nProblemas(self) -> int:
        return self._problemas.filas

    @Slot(int, result="QVariantMap")
    def problema(self, fila_visible: int) -> dict:
        if fila_visible < 0:
            return {}
        return self._problemas.fila(self._problemas_filtrados.filaOrigen(fila_visible))

    @Slot(int)
    def elegir(self, fila_visible: int) -> None:
        """Elegir un problema: el editor salta a su archivo y su línea."""
        p = self.problema(fila_visible)
        if p:
            self._siguiente = fila_visible
            self.irA.emit(p["archivo"], int(p["linea"] or 0))

    @Slot()
    def siguiente(self) -> None:
        """F8: el siguiente problema visible (vuelve al primero al final)."""
        n = self._problemas_filtrados.filas
        if n == 0:
            self.aviso.emit("Sin problemas que recorrer.", "informacion")
            return
        self.elegir((self._siguiente + 1) % n)

    @Property(int, notify=problemasCambiados)
    def problemaActual(self) -> int:
        return self._siguiente

    # ---------------------------------------------------------------------------------------------------- dependencias
    @Slot(str)
    def revisarDependencias(self, ruta: str = "") -> None:
        """Ctrl+Mayús+D: clases, paquetes, archivos y programas que faltan (solo lee); el resultado va a Problemas."""
        p = self.proyectos.proyecto(self._objetivo(ruta))
        if p is None:
            self.aviso.emit("Abre un proyecto para revisar sus dependencias.", "aviso")
            return

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return dg.revisar(p)

        def fin(filas):
            carpeta = Path(p.carpeta)
            for f in filas:
                try:
                    f["relativa"] = str(Path(f["archivo"]).relative_to(carpeta))
                except ValueError:
                    f["relativa"] = Path(f["archivo"]).name
            self._problemas.poner(filas)
            self._origen, self._registro_texto, self._ruta_problemas = "revisión de dependencias", "", p.principal
            self.problemasCambiados.emit()
            if filas:
                self.aviso.emit(f"Dependencias de {p.nombre}: {len(filas)} problema(s); están en Problemas.", "aviso")
            else:
                self.aviso.emit(f"Dependencias de {p.nombre}: todo está (clase, paquetes, archivos, {p.texto_motor()}).", "positivo")

        self.tareas.funcion(f"Revisando las dependencias de {p.nombre}", trabajo, al_terminar=fin)
