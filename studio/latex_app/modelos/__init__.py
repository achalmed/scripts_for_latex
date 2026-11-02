"""studio/latex_app/modelos/__init__.py — las filas de las tablas de LaTeX Studio (documentos, historial, salidas) y de la
lista de problemas, sin Qt (se prueban solas); los modelos de Qt son los genéricos de gui_comun (`ModeloTabla`,
`ModeloFiltrado`, `ModeloLista`)."""

from __future__ import annotations

from pathlib import Path

from latex_app import compilador as svc

COLUMNAS_DOCUMENTOS = [("Documento", "nombre"), ("Estado", "estado"), ("Motor", "motor"), ("PDF", "pdf"),
                       ("Modificado", "modificado"), ("Carpeta", "carpeta")]
COLUMNAS_HISTORIAL = [("Cuándo", "cuando"), ("Documento", "nombre"), ("Resultado", "resultado"), ("Duración", "duracion"),
                      ("Detalle", "detalle"), ("Carpeta", "carpeta")]
COLUMNAS_SALIDAS = [("Archivo", "nombre"), ("Tipo", "tipo"), ("Tamaño", "tamano"), ("Modificado", "modificado")]
ROLES_PROBLEMAS = ("nivel", "mensaje", "archivo", "linea", "detalle")
ICONO_TEX = "text-x-tex"
ICONOS_ESTADO = {"compilado": "dialog-ok-apply", "avisos": "data-warning", "errores": "data-error", "desactualizado": "view-refresh",
                 "sin_compilar": "dialog-cancel", "compilando": "system-run"}
ORDEN_ESTADO = {"errores": 0, "avisos": 1, "desactualizado": 2, "sin_compilar": 3, "compilado": 4, "compilando": 5}


def texto_motor(tex: Path, motor: str = "auto") -> str:
    """Lo que la columna Motor dice: el motor efectivo y, si lo declara el `.tex`, «(declarado)»."""
    declarado = svc.motor_declarado(tex)
    efectivo = svc.motor_efectivo(tex, motor)
    nombre = svc.NOMBRES_MOTOR.get(efectivo, efectivo)
    return f"{nombre} (declarado)" if declarado and motor == "auto" else nombre


def fila_documento(tex: Path, estado: svc.Estado, motor: str = "auto", salida: str = "") -> dict:
    """Una fila de la tabla de documentos: nombre, estado con color semántico, motor, fecha del PDF, modificado, carpeta."""
    pdf = svc.info_pdf(svc.pdf_de(tex, salida), con_paginas=False)
    try:
        mtime = tex.stat().st_mtime
    except OSError:
        mtime = 0.0
    return {"nombre": tex.name, "estado": estado.texto, "motor": texto_motor(tex, motor), "pdf": pdf["modificado"] or "—",
            "modificado": svc.fecha_legible(mtime) if mtime else "", "carpeta": str(tex.parent),
            "ruta": str(tex), "clave": estado.clave, "errores": estado.errores, "avisos": estado.avisos, "tipografia": estado.tipografia,
            "nivel": estado.nivel, "habilitado": True,
            "icono": {"nombre": ICONO_TEX, "estado": ICONOS_ESTADO[estado.clave]},
            "crudo": {"estado": ORDEN_ESTADO[estado.clave], "pdf": pdf["mtime"], "modificado": mtime}}


def fila_historial(h: dict) -> dict:
    """Una fila de la vista Historial desde una entrada guardada (las claves de 1.x: tex, ok, segundos, detalle, cuando)."""
    tex = Path(h.get("tex", ""))
    ok = bool(h.get("ok"))
    return {"cuando": h.get("cuando", ""), "nombre": tex.name, "resultado": "Compiló" if ok else "Falló",
            "duracion": f"{h.get('segundos', 0)} s", "detalle": h.get("detalle", ""), "carpeta": str(tex.parent),
            "ruta": str(tex), "ok": ok, "nivel": "positivo" if ok else "negativo", "habilitado": True,
            "icono": {"nombre": ICONO_TEX, "resultado": "dialog-ok-apply" if ok else "dialog-cancel"},
            "crudo": {"duracion": float(h.get("segundos", 0) or 0), "resultado": 0 if ok else 1}}


def fila_salida(s: dict) -> dict:
    return {**s, "nivel": "positivo" if s["tipo"] == "PDF" else "",
            "icono": "application-pdf" if s["tipo"] == "PDF" else "text-x-generic",
            "crudo": {"tamano": s["bytes"], "modificado": s["mtime"]}}


def filas_problemas(problemas: list[svc.Problema]) -> list[dict]:
    """Las filas de `ListaDiagnosticos` desde los problemas de `leer_log` (ya vienen ordenados: errores, avisos, tipografía)."""
    return [{"nivel": p.nivel, "mensaje": p.mensaje, "archivo": p.archivo, "linea": p.linea or 0, "detalle": " ".join(p.detalle)}
            for p in problemas]


def contar(filas: list[dict]) -> dict:
    """Cuántos documentos hay por estado (la barra de estado y los contadores de la navegación)."""
    c = {k: 0 for k in svc.ESTADOS}
    for f in filas:
        c[f["clave"]] = c.get(f["clave"], 0) + 1
    c["total"] = len(filas)
    return c


def resumen_contadores(c: dict) -> str:
    n = c.get("total", 0)
    partes = [f"{n} documento" + ("" if n == 1 else "s")]
    for clave, texto in (("compilado", "compilados"), ("avisos", "con avisos"), ("errores", "con errores"),
                         ("desactualizado", "con PDF anterior al .tex"), ("sin_compilar", "sin compilar")):
        if c.get(clave):
            partes.append(f"{c[clave]} {texto}")
    return " · ".join(partes)
