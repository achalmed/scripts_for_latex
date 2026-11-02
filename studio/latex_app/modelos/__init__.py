"""studio/latex_app/modelos/__init__.py — las filas de la tabla del historial de compilaciones, sin Qt (se prueban solas);
los modelos de Qt son los genéricos de gui_comun (`ModeloTabla`, `ModeloFiltrado`, `ModeloLista`). Las filas de los
proyectos están en `controladores/proyectos.py` (`fila_proyecto`)."""

from __future__ import annotations

from pathlib import Path

COLUMNAS_HISTORIAL = [("Cuándo", "cuando"), ("Documento", "nombre"), ("Resultado", "resultado"), ("Duración", "duracion"),
                      ("Detalle", "detalle"), ("Carpeta", "carpeta")]
ICONO_TEX = "text-x-tex"


def fila_historial(h: dict) -> dict:
    """Una fila del historial desde una entrada guardada (las claves de 1.x: tex, ok, segundos, detalle, cuando)."""
    tex = Path(h.get("tex", ""))
    ok = bool(h.get("ok"))
    return {"cuando": h.get("cuando", ""), "nombre": tex.name, "resultado": "Compiló" if ok else "Falló",
            "duracion": f"{h.get('segundos', 0)} s", "detalle": h.get("detalle", ""), "carpeta": str(tex.parent),
            "ruta": str(tex), "ok": ok, "nivel": "positivo" if ok else "negativo", "habilitado": True,
            "icono": {"nombre": ICONO_TEX, "resultado": "dialog-ok-apply" if ok else "dialog-cancel"},
            "crudo": {"duracion": float(h.get("segundos", 0) or 0), "resultado": 0 if ok else 1}}
