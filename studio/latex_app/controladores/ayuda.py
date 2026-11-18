"""latex_app/controladores/ayuda.py — la ayuda de la IA para la parte abierta: copiar el prompt que el marco arma para ella y leer de vuelta lo que respondió el chat, como cambio sugerido que el autor acepta en el editor.

Objetivo: lo que Yachay ofrece con «Ayuda de la IA» en su editor, también aquí: el prompt de la parte (el del ecosistema
  de prompts, con su entrada rellena con el escrito) al portapapeles, y la respuesta pegada, comprobada sin IA y mostrada
  como diferencia (decisiones §1.19).
Método: corre las dos órdenes de la sección `ayuda:` del `latex-studio.yml` del marco (contrato §10; latex_app/datos.py):
  `prompt` (devuelve {prompt, componente, titulo, fuente, aviso}) y `pegar` (lo pegado y el texto del editor van en dos
  archivos temporales de la caché; devuelve {ok, errores, avisos, antes, despues, diff}). La ventana no llama a ningún
  modelo ni escribe el archivo: aceptar reemplaza el tramo en el editor y el autor guarda con Ctrl+S.
  Antes de copiar, `revisar_prompt` (si el marco lo declara; C12.3, decisiones §1.22) dice si el prompt lleva datos de
  estudiantes o del despacho: la ventana lo muestra y el autor decide si copia igual.
Límite: la ventana no sabe qué prompt sirve a qué parte ni qué es un componente: lo dice el marco. Sin la sección, la
  acción queda deshabilitada.
"""
from __future__ import annotations

import os
from pathlib import Path

from gui_comun.qt import QObject, Property, Signal, Slot

from latex_app import datos


def _cache() -> Path:
    d = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "latex-studio" / "ayuda"
    d.mkdir(parents=True, exist_ok=True)
    return d


class AyudaParte(QObject):
    cambiado = Signal()
    promptListo = Signal("QVariantMap")              # {prompt, componente, titulo, fuente, aviso} o {error}
    pegadoListo = Signal("QVariantMap")              # {ok, errores, avisos, antes, despues, diff} o {error}
    promptRevisado = Signal("QVariantMap")           # {sensible, nivel, hallazgos, porque, fuente} (C12.3) o {sensible: false}

    def __init__(self, proyectos, tareas, consola, sistema=None, parent=None):
        super().__init__(parent)
        self.proyectos, self.tareas, self.consola, self.sistema = proyectos, tareas, consola, sistema
        self._decl: dict | None = None
        proyectos.abiertoCambiado.connect(self.recargar)

    def _get_disponible(self): return self._decl is not None
    disponible = Property(bool, _get_disponible, notify=cambiado)

    def _get_nombre(self): return self._decl["nombre"] if self._decl else "Ayuda de la IA"
    nombre = Property(str, _get_nombre, notify=cambiado)

    def _get_revisa(self): return bool(self._decl and self._decl.get("revisar_prompt"))
    revisaPrompt = Property(bool, _get_revisa, notify=cambiado)

    @Slot(str)
    def revisarPrompt(self, texto: str) -> None:
        """Antes de copiar: si el prompt lleva datos de estudiantes o del despacho (`revisar_prompt` del marco, C12.3).
        `promptRevisado` trae el resultado; sin la orden, trae {sensible: false} y la ventana copia sin preguntar."""
        if not self.revisaPrompt:
            self.promptRevisado.emit({"sensible": False, "hallazgos": []})
            return
        decl = dict(self._decl)
        archivo = _cache() / "prompt.txt"
        archivo.write_text(texto or "", encoding="utf-8")
        argv = datos.con(decl["revisar_prompt"], prompt=str(archivo))

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["proyecto"])

        def fin(r):
            dato, error = r
            if not isinstance(dato, dict) or dato.get("error"):
                # sin respuesta no se sabe: se avisa, para que el autor decida en vez de copiar a ciegas
                dato = {"sensible": True, "nivel": "desconocido", "hallazgos": [],
                        "error": (dato or {}).get("error") if isinstance(dato, dict) else (error or "la revisión no respondió")}
            self.promptRevisado.emit(dato)
        self.tareas.funcion("Revisar el prompt antes de copiarlo", trabajo, silenciosa=True, operacion="lectura", error=False, al_terminar=fin)

    @Slot()
    def recargar(self) -> None:
        self._decl = datos.declaracion_ayuda(self.proyectos.principal) if self.proyectos.hayAbierto else None
        self.cambiado.emit()

    def _relativa(self, ruta: str) -> str:
        try:
            return str(Path(ruta).resolve().relative_to(Path(self._decl["proyecto"]).resolve()))
        except (ValueError, OSError):
            return ruta

    @Slot(str, str)
    def pedirPrompt(self, ruta: str, componente: str) -> None:
        """El prompt de la parte `ruta` (el componente pedido o, vacío, el primero); `promptListo` lo trae."""
        if not self._decl or not ruta:
            return
        decl = dict(self._decl)
        argv = datos.con(decl["prompt"], archivo=self._relativa(ruta)) + (["--componente", componente] if componente else [])

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["proyecto"])

        def fin(r):
            dato, error = r
            dato = dato if isinstance(dato, dict) else {"error": error or "la orden no devolvió nada"}
            if dato.get("error"):
                self.consola.registrar("warn", f"Ayuda de la IA: {dato['error']}")
            self.promptListo.emit(dato)
        self.tareas.funcion("Preparar el prompt", trabajo, silenciosa=True, operacion="lectura", error=False, al_terminar=fin)

    @Slot(str, str, str, str)
    def comprobar(self, ruta: str, componente: str, pegado: str, texto_editor: str) -> None:
        """Lo pegado, comprobado contra la parte tal como está en el editor; `pegadoListo` trae el cambio sugerido."""
        if not self._decl or not ruta:
            return
        decl = dict(self._decl)
        cache = _cache()
        (cache / "pegado.txt").write_text(pegado or "", encoding="utf-8")
        (cache / "editor.tex").write_text(texto_editor or "", encoding="utf-8")
        argv = datos.con(decl["pegar"], archivo=self._relativa(ruta), pegado=str(cache / "pegado.txt"), tex=str(cache / "editor.tex"))
        argv += ["--componente", componente] if componente else []

        def trabajo(progress_cb=None, cancel_cb=None, message_cb=None):
            return datos._json(argv, decl["proyecto"])

        def fin(r):
            dato, error = r
            self.pegadoListo.emit(dato if isinstance(dato, dict) else {"error": error or "la orden no devolvió nada"})
        self.tareas.funcion("Comprobar lo pegado", trabajo, silenciosa=True, operacion="lectura", error=False, al_terminar=fin)
