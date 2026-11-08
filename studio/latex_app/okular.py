"""latex_app/okular.py — Okular como visor del PDF (por omisión desde el 2026-11-08): las órdenes para abrirlo y para el
SyncTeX hacia el PDF, y su «editor externo» para el SyncTeX de vuelta (Mayús+clic en Okular → esta ventana).

Okular recarga solo el PDF cuando el compilador lo reescribe (su opción «Recargar el documento al cambiar», activa por
omisión): la ventana lo abre una vez (`okular --unique`) y lo deja. Del código al PDF: `okular --unique
"<pdf>#src:<línea><tex>"`. Del PDF al código: Okular corre su orden de editor con `%f` (archivo) y `%l` (línea); aquí es
`main.py --ir %f %l`, que pasa el salto a la ventana abierta (`instancia.py`).

Esa orden vive en la configuración de Okular (`~/.config/okularpartrc`, grupo `[Core General]`: `ExternalEditor=Custom`
y `ExternalEditorCommand`). Como `texstudio.py`: se edita como texto (KConfig reescribiría el archivo y rompería el enlace
de un paquete stow), solo esas dos claves, con Okular cerrado, respaldo junto al archivo y deshacer.

    python3 studio/latex_app/okular.py             # muestra lo que cambiaría
    python3 studio/latex_app/okular.py --aplicar   # lo escribe (con respaldo)
    python3 studio/latex_app/okular.py --deshacer  # vuelve al último respaldo
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

MAIN = Path(__file__).resolve().parents[1] / "main.py"
GRUPO = "Core General"


def orden_abrir(pdf: str, tex: str = "", linea: int = 0) -> list[str]:
    """`okular --unique` con el PDF; con `tex` y `linea`, en el punto que les corresponde (SyncTeX)."""
    if tex and linea:
        return ["okular", "--unique", f"{pdf}#src:{int(linea)}{os.path.abspath(tex)}"]
    return ["okular", "--unique", pdf]


def ruta_config() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "okularpartrc"


def deseado() -> dict[str, str]:
    return {"ExternalEditor": "Custom", "ExternalEditorCommand": f"/usr/bin/python3 {MAIN} --ir %f %l"}


def _leer(ruta: Path) -> list[str]:
    return ruta.read_text(encoding="utf-8", errors="surrogateescape").split("\n") if ruta.is_file() else []


def _seccion(lineas: list[str]) -> tuple[int, int]:
    inicio = next((i for i, l in enumerate(lineas) if l.strip() == f"[{GRUPO}]"), -1)
    if inicio < 0:
        return -1, -1
    fin = next((i for i in range(inicio + 1, len(lineas)) if lineas[i].startswith("[")), len(lineas))
    return inicio, fin


def _actuales(lineas: list[str]) -> dict[str, str]:
    inicio, fin = _seccion(lineas)
    return dict(l.split("=", 1) for l in lineas[inicio + 1:fin] if "=" in l) if inicio >= 0 else {}


def cambios(ruta: Path | None = None) -> list[tuple[str, str, str]]:
    """(clave, valor actual, valor nuevo) de lo que cambiaría; vacía si ya está."""
    actuales = _actuales(_leer(ruta or ruta_config()))
    return [(k, actuales.get(k, ""), v) for k, v in deseado().items() if actuales.get(k, "") != v]


def configurado(ruta: Path | None = None) -> bool:
    return not cambios(ruta)


def okular_abierto() -> bool:
    try:
        return subprocess.run(["pgrep", "-x", "okular"], capture_output=True).returncode == 0
    except OSError:
        return False


def aplicar(ruta: Path | None = None) -> str:
    """Escribe las dos claves con respaldo; devuelve "" o el motivo por el que no se hizo."""
    ruta = ruta or ruta_config()
    if okular_abierto():
        return "Cierra Okular antes: guarda su configuración al salir y se perdería el cambio."
    lista = cambios(ruta)
    if not lista:
        return ""
    lineas = _leer(ruta)
    if ruta.is_file():
        shutil.copy2(ruta, ruta.with_name(f"okularpartrc.antes-latex-studio-{time.strftime('%Y%m%d-%H%M%S')}"))
    inicio, fin = _seccion(lineas)
    if inicio < 0:                                   # sin el grupo: al final
        if lineas and lineas[-1].strip():
            lineas.append("")
        lineas += [f"[{GRUPO}]"]
        inicio = fin = len(lineas)
        fin = len(lineas)
    nuevos = {k: v for k, _a, v in lista}
    for i in range(inicio + 1, fin):
        clave = lineas[i].split("=", 1)[0]
        if clave in nuevos:
            lineas[i] = f"{clave}={nuevos.pop(clave)}"
    for clave, valor in nuevos.items():
        lineas.insert(fin, f"{clave}={valor}")
        fin += 1
    texto = "\n".join(lineas)
    ruta.write_text(texto if texto.endswith("\n") else texto + "\n", encoding="utf-8", errors="surrogateescape")
    return ""


def deshacer(ruta: Path | None = None) -> str:
    ruta = ruta or ruta_config()
    if okular_abierto():
        return "Cierra Okular antes de deshacer."
    respaldos = sorted(ruta.parent.glob("okularpartrc.antes-latex-studio-*"))
    if not respaldos:
        return "No hay respaldo que restaurar."
    shutil.copy2(respaldos[-1], ruta)
    return ""


if __name__ == "__main__":
    if "--deshacer" in sys.argv:
        e = deshacer()
        print(e or "Restaurado el último respaldo de Okular.")
        sys.exit(1 if e else 0)
    lista = cambios()
    if not lista:
        print("Okular ya vuelve al código en LaTeX Studio (Mayús+clic).")
        sys.exit(0)
    for clave, actual, nuevo in lista:
        print(f"[{GRUPO}] {clave}: «{actual}» → «{nuevo}»")
    if "--aplicar" in sys.argv:
        e = aplicar()
        print(e or f"Hecho (respaldo junto a {ruta_config()}).")
        sys.exit(1 if e else 0)
    print("SIMULACIÓN (usa --aplicar)")
