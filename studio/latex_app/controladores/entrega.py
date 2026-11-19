"""latex_app/controladores/entrega.py — «Antes de entregar» (Ctrl+Alt+E): los controles que el marco revisa antes de entregar el documento abierto, los puntos manuales que el autor marca y el registro de cada uso de la IA que acepta.

Objetivo: cerrar la cadena de evidencia sin salir de la ventana (decisiones §1.21): ver cada control con su estado, su
  porqué con la fuente y sus hallazgos (un clic lleva al archivo y la línea), marcar o justificar lo manual, y saber si
  está «Listo para entregar».
Método: corre las tres órdenes de la sección `entrega:` del `latex-studio.yml` del marco (contrato §12;
  latex_app/datos.py) en hilos: `revisar` (devuelve los controles; `datos.resultado_entrega` les pone la ruta absoluta y
  el veredicto), `marcar` con `--aplicar` al tocar la casilla o guardar la nota (el clic es la confirmación; luego se
  revisa de nuevo) y `registrar_ia` con `--aplicar` cuando el autor pone en el editor un cambio de la ayuda de la IA
  (contrato §10, «Poner en el editor»).
  La autoevaluación con la rúbrica (C11.2; decisiones §1.22): `rubrica` trae la rúbrica en el formato común y lo
  puntuado (`datos.resultado_rubrica`), y `autoevaluar` guarda un criterio con `--aplicar` al pulsar «Guardar»; un
  control que trae `accion: autoevaluar` muestra el botón que abre el diálogo.
  La medición (C14.1; decisiones §1.21): «Revisar de nuevo» corre `medir --aplicar` (revisa y anota la corrida en el
  registro del marco; la revisión llega en `revision`), y `falso --aplicar` declara con su motivo que lo que marcó un
  control no era un defecto. El tiempo por etapa: `tiempo` trae la etapa en curso y los minutos (`tiempos`), y
  `tiempo <etapa> empezar|terminar --aplicar` marca. El candado de entrega (§1.21): `entregar` con `--destino` copia el
  PDF y lo anota; con «Faltan N» y sin `--motivo` el marco se detiene (`bloqueado`) y la ventana pide el motivo.
Límite: la ventana no sabe qué es una cifra viva ni qué lista corresponde a un tipo: lo dice el marco. El veredicto lo
  calcula la ventana con lo revisado (`datos.veredicto`): listo si no hay fallas y todo lo manual está marcado o
  justificado. Sin la sección, la acción queda deshabilitada y nada se registra.
"""
from __future__ import annotations

import json

from gui_comun.qt import QObject, Property, Signal, Slot

from latex_app import datos


class AntesDeEntregar(QObject):
    cambiado = Signal()
    resultadoCambiado = Signal()
    marcado = Signal("QVariantMap")                  # lo que respondió `marcar` ({id, estado, escrito} o {error})
    rubricaCambiada = Signal()
    autoevaluado = Signal("QVariantMap")             # lo que respondió `autoevaluar` ({puntajes, nota, escrito} o {error})
    lectorFrioListo = Signal("QVariantMap")          # lo que respondió `lector_frio` ({pdf, quitado, pendientes, escrito} o {error})
    registrado = Signal("QVariantMap")               # lo que respondió `registrar_ia`
    falsoDeclarado = Signal("QVariantMap")           # lo que respondió `falso` ({falso, escrito} o {error})
    tiemposCambiados = Signal()
    etapaMarcada = Signal("QVariantMap")             # lo que respondió `tiempo <etapa> <accion>` ({tramo, cerrado…} o {error})
    entregado = Signal("QVariantMap")                # lo que respondió `entregar` ({entrega, escrito}, {bloqueado, mensaje} o {error})

    def __init__(self, proyectos, tareas, consola, parent=None):
        super().__init__(parent)
        self.proyectos, self.tareas, self.consola = proyectos, tareas, consola
        self._decl: dict | None = None
        self._resultado: dict = datos.resultado_entrega({"controles": []}, "")
        self._revisando = False
        self._pedido = 0
        self._rubrica: dict = {}
        self._tiempos: dict = datos.resultado_tiempos({})
        proyectos.abiertoCambiado.connect(self.recargar)

    # ------------------------------------------------------------------ propiedades
    def _get_disponible(self): return self._decl is not None
    disponible = Property(bool, _get_disponible, notify=cambiado)

    def _get_nombre(self): return self._decl["nombre"] if self._decl else "Antes de entregar"
    nombre = Property(str, _get_nombre, notify=cambiado)

    def _get_resultado(self): return self._resultado
    resultado = Property("QVariantMap", _get_resultado, notify=resultadoCambiado)

    def _get_revisando(self): return self._revisando
    revisando = Property(bool, _get_revisando, notify=resultadoCambiado)

    def _get_puede_marcar(self): return bool(self._decl and self._decl.get("marcar"))
    puedeMarcar = Property(bool, _get_puede_marcar, notify=cambiado)

    def _get_puede_autoevaluar(self): return bool(self._decl and self._decl.get("rubrica") and self._decl.get("autoevaluar"))
    puedeAutoevaluar = Property(bool, _get_puede_autoevaluar, notify=cambiado)

    def _get_puede_lector_frio(self): return bool(self._decl and self._decl.get("lector_frio"))
    puedeLectorFrio = Property(bool, _get_puede_lector_frio, notify=cambiado)

    def _get_rubrica(self): return self._rubrica
    rubrica = Property("QVariantMap", _get_rubrica, notify=rubricaCambiada)

    def _get_puede_medir(self): return bool(self._decl and self._decl.get("medir"))
    puedeMedir = Property(bool, _get_puede_medir, notify=cambiado)

    def _get_puede_falso(self): return bool(self._decl and self._decl.get("falso"))
    puedeFalso = Property(bool, _get_puede_falso, notify=cambiado)

    def _get_puede_tiempo(self): return bool(self._decl and self._decl.get("tiempo"))
    puedeTiempo = Property(bool, _get_puede_tiempo, notify=cambiado)

    def _get_puede_entregar(self): return bool(self._decl and self._decl.get("entregar"))
    puedeEntregar = Property(bool, _get_puede_entregar, notify=cambiado)

    def _get_tiempos(self): return self._tiempos
    tiempos = Property("QVariantMap", _get_tiempos, notify=tiemposCambiados)

    @Slot(int, result=str)
    def duracion(self, minutos: int) -> str:
        return datos.duracion(minutos)

    # ------------------------------------------------------------------ revisar
    @Slot()
    def recargar(self) -> None:
        """Lee la declaración del marco para el proyecto abierto; lo revisado de otro proyecto se olvida."""
        decl = datos.declaracion_entrega(self.proyectos.principal) if self.proyectos.hayAbierto else None
        if (decl or {}).get("proyecto") != (self._decl or {}).get("proyecto"):
            self._resultado = datos.resultado_entrega({"controles": []}, "")
            self._tiempos = datos.resultado_tiempos({})
            self.resultadoCambiado.emit()
            self.tiemposCambiados.emit()
        self._decl = decl
        self.cambiado.emit()

    @Slot()
    def revisar(self) -> None:
        """Corre `revisar` del marco en un hilo (el último pedido manda); `resultado` trae los controles y el veredicto."""
        self._revisar(False)

    @Slot()
    def revisarMidiendo(self) -> None:
        """«Revisar de nuevo»: la misma revisión, anotada como una corrida en el registro del marco (`medir --aplicar`,
        C14.1); sin `medir` en la declaración, revisa sin medir. Abrir el diálogo o marcar un punto no miden."""
        self._revisar(self.puedeMedir)

    def _revisar(self, medir: bool) -> None:
        if not self._decl:
            return
        decl = dict(self._decl)
        self._pedido += 1
        pedido = self._pedido
        self._revisando = True
        self.resultadoCambiado.emit()

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            if medir:
                return datos._json(decl["medir"] + ["--aplicar"], decl["proyecto"], tope=120)
            return datos._json(decl["revisar"], decl["proyecto"], tope=120)

        def fin(r):
            if pedido != self._pedido or not self._decl or self._decl["proyecto"] != decl["proyecto"]:
                return
            dato, error = r
            if medir and isinstance(dato, dict) and not dato.get("error"):
                if dato.get("escrito"):
                    self.consola.registrar("info", f"Antes de entregar: corrida anotada en {dato.get('ruta', 'el registro')}")
                dato = dato.get("revision") if isinstance(dato.get("revision"), dict) else {"error": "medir no devolvió la revisión"}
            self._resultado = datos.resultado_entrega(dato if dato is not None else {"error": error}, decl["proyecto"])
            self._revisando = False
            if self._resultado["error"]:
                self.consola.registrar("warn", f"Antes de entregar: {self._resultado['error']}")
            self.resultadoCambiado.emit()
        self.tareas.funcion("Revisar antes de entregar", trabajo, silenciosa=True, operacion="lectura", error=False, al_terminar=fin)

    # ------------------------------------------------------------------ marcar un punto manual
    @Slot(str, bool, str)
    def marcar(self, id: str, hecho: bool, nota: str) -> None:
        """La casilla y la nota de un punto manual: hecho, justificado (sin casilla y con nota) o pendiente."""
        if not self.puedeMarcar:
            return
        nota = (nota or "").strip()
        estado = "hecho" if hecho else "justificado" if nota else "pendiente"
        decl = dict(self._decl)
        argv = datos.con(decl["marcar"], id=id, estado=estado, nota=nota) + ["--aplicar"]

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["proyecto"])

        def fin(r):
            dato, error = r
            dato = dato if isinstance(dato, dict) else {"error": error or "la orden no devolvió nada"}
            if dato.get("error"):
                self.consola.registrar("warn", f"Marcar: {dato['error']}")
            self.marcado.emit(dato)
            self.revisar()
        self.tareas.funcion("Marcar un punto", trabajo, silenciosa=True, operacion="escritura", error=False, al_terminar=fin)

    # ------------------------------------------------------------------ registrar un uso de la IA
    @Slot("QVariantMap")
    def registrarIa(self, uso: dict) -> None:
        """Al poner en el editor un cambio de la ayuda de la IA: {ruta, parte, prompt: {titulo, ruta, version, texto},
        antes, despues}. El marco lo agrega a su registro y regenera la declaración (sin la sección, no hace nada)."""
        if not self._decl or not self._decl.get("registrar_ia"):
            return
        uso = dict(uso)
        decl = dict(self._decl)
        carga = datos.uso_de_ia(decl["proyecto"], str(uso.get("ruta") or ""), str(uso.get("parte") or ""),
                                dict(uso.get("prompt") or {}), str(uso.get("antes") or ""), str(uso.get("despues") or ""))
        argv = datos.con(decl["registrar_ia"], datos=json.dumps(carga, ensure_ascii=False)) + ["--aplicar"]

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["proyecto"])

        def fin(r):
            dato, error = r
            dato = dato if isinstance(dato, dict) else {"error": error or "la orden no devolvió nada"}
            if dato.get("escrito"):
                self.consola.registrar("ok", f"Uso de la IA registrado: {dato.get('registro', '')} ({dato.get('total', '')} en total)")
            else:
                self.consola.registrar("warn", f"Registrar el uso de la IA: {dato.get('error', 'no se escribió')}")
            self.registrado.emit(dato)
        self.tareas.funcion("Registrar el uso de la IA", trabajo, silenciosa=True, operacion="escritura", error=False, al_terminar=fin)

    # ------------------------------------------------------------------ la autoevaluación con la rúbrica (C11.2)
    @Slot()
    def leerRubrica(self) -> None:
        """La rúbrica que le toca al proyecto y lo ya puntuado (`rubrica` del marco); `rubrica` lo trae."""
        if not self.puedeAutoevaluar:
            return
        decl = dict(self._decl)

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(decl["rubrica"], decl["proyecto"])

        def fin(r):
            dato, error = r
            self._rubrica = datos.resultado_rubrica(dato if dato is not None else {"error": error})
            self.rubricaCambiada.emit()
        self.tareas.funcion("Leer la rúbrica", trabajo, silenciosa=True, operacion="lectura", error=False, al_terminar=fin)

    @Slot(str, str, str)
    def autoevaluar(self, clave: str, puntaje: str, justificacion: str) -> None:
        """Guarda el puntaje y la justificación de un criterio (el clic en «Guardar» es la confirmación)."""
        if not self.puedeAutoevaluar:
            return
        decl = dict(self._decl)
        carga = json.dumps({"clave": clave, "puntaje": puntaje, "justificacion": justificacion}, ensure_ascii=False)
        argv = datos.con(decl["autoevaluar"], datos=carga) + ["--aplicar"]

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["proyecto"])

        def fin(r):
            dato, error = r
            dato = dato if isinstance(dato, dict) else {"error": error or "la orden no devolvió nada"}
            if dato.get("error"):
                self.consola.registrar("warn", f"Autoevaluación: {dato['error']}")
            self.autoevaluado.emit(dato)
            self.leerRubrica()
            self.revisar()
        self.tareas.funcion("Guardar la autoevaluación", trabajo, silenciosa=True, operacion="escritura", error=False, al_terminar=fin)

    # ------------------------------------------------------------------ el lector frío (C11.4)
    @Slot()
    def lectorFrio(self) -> None:
        """La versión sin nombres para un revisor externo (`lector_frio --aplicar`: el marco la copia, la anonimiza y la
        compila fuera del documento); `lectorFrioListo` trae el PDF y lo que se quitó."""
        if not self.puedeLectorFrio:
            return
        decl = dict(self._decl)

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(decl["lector_frio"] + ["--aplicar"], decl["proyecto"], tope=600)

        def fin(r):
            dato, error = r
            dato = dato if isinstance(dato, dict) else {"error": error or "la orden no devolvió nada"}
            if dato.get("error"):
                self.consola.registrar("warn", f"Lector frío: {dato['error']}")
            elif dato.get("pdf"):
                self.consola.registrar("ok", f"Versión sin nombres: {dato['pdf']}")
            self.lectorFrioListo.emit(dato)
        self.tareas.funcion("Preparar la versión para el lector frío", trabajo, operacion="escritura", error=False, al_terminar=fin)

    # ------------------------------------------------------------------ la medición: el falso positivo (C14.1)
    @Slot(str, str)
    def declararFalso(self, control: str, nota: str) -> None:
        """Lo que marcó `control` no era un defecto: el marco lo anota con su motivo (el clic en «Declarar» es la
        confirmación) y se revisa de nuevo, sin medir."""
        nota = (nota or "").strip()
        if not self.puedeFalso or not nota:
            return
        decl = dict(self._decl)
        argv = datos.con(decl["falso"], control=control, nota=nota) + ["--aplicar"]

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["proyecto"])

        def fin(r):
            dato, error = r
            dato = dato if isinstance(dato, dict) else {"error": error or "la orden no devolvió nada"}
            if dato.get("error"):
                self.consola.registrar("warn", f"Falso positivo: {dato['error']}")
            else:
                self.consola.registrar("ok", f"Falso positivo de «{control}» anotado en {dato.get('ruta', 'el registro')}")
            self.falsoDeclarado.emit(dato)
            self.revisar()
        self.tareas.funcion("Declarar un falso positivo", trabajo, silenciosa=True, operacion="escritura", error=False, al_terminar=fin)

    # ------------------------------------------------------------------ el tiempo por etapa (C14.1)
    @Slot()
    def leerTiempos(self) -> None:
        """La etapa en curso y los minutos por etapa (`tiempo` del marco, sin etapa); `tiempos` lo trae."""
        if not self.puedeTiempo:
            return
        decl = dict(self._decl)

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(decl["tiempo"], decl["proyecto"])

        def fin(r):
            if not self._decl or self._decl["proyecto"] != decl["proyecto"]:
                return
            dato, error = r
            self._tiempos = datos.resultado_tiempos(dato if dato is not None else {"error": error})
            self.tiemposCambiados.emit()
        self.tareas.funcion("Leer el tiempo por etapa", trabajo, silenciosa=True, operacion="lectura", error=False, al_terminar=fin)

    @Slot(str, str)
    def marcarEtapa(self, etapa: str, accion: str) -> None:
        """Empieza o termina una etapa (el clic es la confirmación); empezar otra cierra la que estaba en curso."""
        if not self.puedeTiempo or accion not in ("empezar", "terminar"):
            return
        decl = dict(self._decl)
        argv = decl["tiempo"] + [etapa, accion, "--aplicar"]

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["proyecto"])

        def fin(r):
            dato, error = r
            dato = dato if isinstance(dato, dict) else {"error": error or "la orden no devolvió nada"}
            if dato.get("error"):
                self.consola.registrar("warn", f"Tiempo por etapa: {dato['error']}")
            self.etapaMarcada.emit(dato)
            self.leerTiempos()
        self.tareas.funcion("Marcar una etapa", trabajo, silenciosa=True, operacion="escritura", error=False, al_terminar=fin)

    # ------------------------------------------------------------------ el candado de entrega (§1.21)
    @Slot(str, str)
    def entregar(self, destino: str, motivo: str) -> None:
        """Entrega el PDF: el marco revisa otra vez y, con «Faltan N» y sin motivo, se detiene (`bloqueado`); si no, copia
        el PDF a `destino` y anota la entrega (con el motivo). El clic en «Entregar» es la confirmación."""
        if not self.puedeEntregar:
            return
        decl = dict(self._decl)
        argv = list(decl["entregar"]) + (["--destino", destino] if destino else []) \
            + (["--motivo", motivo.strip()] if (motivo or "").strip() else []) + ["--aplicar"]

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["proyecto"], tope=180)

        def fin(r):
            dato, error = r
            dato = dato if isinstance(dato, dict) else {"error": error or "la orden no devolvió nada"}
            if dato.get("error"):
                self.consola.registrar("warn", f"Entregar: {dato['error']}")
            elif dato.get("escrito"):
                con_motivo = (dato.get("entrega") or {}).get("motivo")
                self.consola.registrar("ok", f"PDF entregado{' en ' + destino if destino else ''}"
                                             + (f" con «Faltan {dato.get('faltan')}» (motivo: {con_motivo})" if con_motivo else ""))
            self.entregado.emit(dato)
        self.tareas.funcion("Entregar el PDF", trabajo, operacion="escritura", error=False, al_terminar=fin)
