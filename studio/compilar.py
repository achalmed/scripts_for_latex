#!/usr/bin/python3
"""studio/compilar.py — compila un .tex como lo compila LaTeX Studio, desde cualquier editor (TeXstudio, Kate, la terminal).

La misma receta que la ventana (`latex_app.compilador.receta`): el `scripts/build.sh` de su marco si la clase es de un
marco (docencia, escritura, marco_documental…), latexmk si el proyecto tiene `latexmkrc`, o `script_compilar_latex/main.sh`
con el motor que declare o LuaLaTeX + Biber. Si el archivo es un capítulo, compila su documento principal (el que lo
incluye o el que declara `% !TEX root`). La salida va a la consola del editor que la llamó; el código de salida es el del
último paso (0 si todo fue bien). LaTeX Studio, si tiene el proyecto abierto, ve el PDF nuevo y sus problemas.

    compilar.py ARCHIVO.tex                 # compilar
    compilar.py ARCHIVO.tex --reconstruir   # limpiar auxiliares y compilar
    compilar.py ARCHIVO.tex --limpiar       # solo limpiar
    compilar.py ARCHIVO.tex --simular       # mostrar las órdenes sin ejecutarlas
    compilar.py ARCHIVO.tex --version soluciones   # otra versión de las que declara el marco (sin --version: la que
                                            # declara el documento, «% !MODO = …», o la de omisión)
    compilar.py ARCHIVO.tex --versiones     # las versiones que declara el marco del documento

En TeXstudio: Opciones › Configurar TeXstudio › Compilación › «Compilar» = /usr/bin/python3 «ruta»/compilar.py %.tex
(o, desde LaTeX Studio, Herramientas › «Compilar desde TeXstudio con LaTeX Studio», que lo deja hecho).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from latex_app import compilador as svc          # noqa: E402  (sin Qt)
from latex_app import proyectos as pr            # noqa: E402  (sin Qt)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compila un .tex con la receta de LaTeX Studio (su marco, latexmk o main.sh)")
    ap.add_argument("tex", type=Path)
    grupo = ap.add_mutually_exclusive_group()
    grupo.add_argument("--reconstruir", action="store_true", help="limpiar los auxiliares y compilar")
    grupo.add_argument("--limpiar", action="store_true", help="solo limpiar los auxiliares")
    grupo.add_argument("--simular", action="store_true", help="mostrar las órdenes sin ejecutarlas")
    grupo.add_argument("--versiones", action="store_true", help="las versiones que declara el marco del documento")
    ap.add_argument("--version", default="", help="la versión que se compila (una de --versiones)")
    args = ap.parse_args(argv)
    tex = args.tex.expanduser().resolve()
    if not tex.is_file():
        print(f"compilar.py: no existe {tex}", file=sys.stderr)
        return 2
    proyecto = pr.proyecto_de(tex)
    if proyecto is None:
        print(f"compilar.py: {tex.name} no tiene \\documentclass ni declara % !TEX root", file=sys.stderr)
        return 2
    if args.versiones:
        if not proyecto.versiones:
            print(f"{tex.name}: su marco no declara versiones")
            return 0
        for v in proyecto.versiones:
            marca = "  ← la que declara el documento" if v["clave"] == proyecto.version_declarada else ""
            print(f"{v['clave']:<12} {v['nombre']} → {proyecto.job_de(v['clave'])}.pdf{marca}")
        return 0
    if args.version and not proyecto.elegir_version(args.version.strip().lower()):
        disponibles = ", ".join(v["clave"] for v in proyecto.versiones) or "ninguna (el marco no declara versiones)"
        print(f"compilar.py: versión desconocida «{args.version}»; disponibles: {disponibles}", file=sys.stderr)
        return 2
    que = "reconstruir" if args.reconstruir else "limpiar" if args.limpiar else "compilar"
    pasos = svc.receta(proyecto, que)
    version = next((v["nombre"] for v in proyecto.versiones if v["clave"] == proyecto.version), "")
    print(f"LaTeX Studio · {Path(proyecto.principal).name} · {proyecto.texto_motor()} · "
          f"{pr.NOMBRES_COMPILADOR.get(proyecto.compilador, proyecto.compilador)}" + (f" · versión: {version}" if version else ""),
          flush=True)
    codigo = 0
    for paso in pasos:
        print(f"→ {paso.descripcion}: {' '.join(paso.argv)}", flush=True)
        if args.simular:
            continue
        entorno = dict(os.environ, **(paso.entorno or {}))
        codigo = subprocess.call(paso.argv, cwd=paso.cwd, env=entorno)
        if codigo != 0:
            print(f"✗ {paso.descripcion}: terminó con el código {codigo}", flush=True)
            return codigo
    if not args.simular:
        print(f"✓ listo: {Path(proyecto.principal).parent / (proyecto.job + '.pdf')}", flush=True)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
