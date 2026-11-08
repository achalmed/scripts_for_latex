"""latex_app/texstudio.py — que TeXstudio compile con LaTeX Studio: su orden «Compilar» pasa a ser `studio/compilar.py`.

TeXstudio compila cada documento con su orden `compile` (por omisión LuaLaTeX o pdfLaTeX a secas), que no encuentra las
clases de un marco (docencia, escritura, marco_documental…), no corre Biber y no usa el `scripts/build.sh` del marco.
Este módulo cambia en `~/.config/texstudio/texstudio.ini` solo tres cosas: `compile` → `compilar.py %.tex` (la misma
receta que la ventana), `bibliography` → Biber, y las rutas de registro y de PDF → `.build` además de la carpeta del
documento (escritura deja ahí los auxiliares). Simula por omisión; al aplicar exige TeXstudio cerrado (al salir reescribe
su configuración), guarda un respaldo junto al .ini y se deshace con `deshacer()`.

    python3 studio/latex_app/texstudio.py            # muestra lo que cambiaría
    python3 studio/latex_app/texstudio.py --aplicar  # lo escribe (con respaldo)
    python3 studio/latex_app/texstudio.py --deshacer # vuelve al último respaldo
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

COMPILAR = Path(__file__).resolve().parents[1] / "compilar.py"
GRUPO = "texmaker"


def ruta_ini() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "texstudio" / "texstudio.ini"


def deseado() -> dict[str, str]:
    """Clave del .ini (como la escribe Qt: «\\» entre niveles, espacios como %20) → valor."""
    return {
        "Tools\\Commands\\compile": f"/usr/bin/python3 {COMPILAR} %.tex",
        "Tools\\Commands\\bibliography": "txs:///biber",
        "Tools\\Log%20Paths": ".build",
        "Tools\\PDF%20Paths": ".build",
    }


# El .ini se edita como texto, línea por línea: reescribirlo con QSettings perdería los valores de tipos propios de
# TeXstudio que Qt no sabe leer («unknown user type StringStringMap»).
def _leer(ini: Path) -> list[str]:
    return ini.read_text(encoding="utf-8", errors="surrogateescape").split("\n")


def _seccion(lineas: list[str]) -> tuple[int, int]:
    """(inicio, fin) de las líneas de la sección [texmaker] (fin exclusivo)."""
    inicio = next((i for i, l in enumerate(lineas) if l.strip() == f"[{GRUPO}]"), -1)
    if inicio < 0:
        return -1, -1
    fin = next((i for i in range(inicio + 1, len(lineas)) if lineas[i].startswith("[")), len(lineas))
    return inicio, fin


def _valor(crudo: str) -> str:
    crudo = crudo.strip()
    if len(crudo) >= 2 and crudo[0] == crudo[-1] == '"':
        return crudo[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return crudo


def _actuales(lineas: list[str]) -> dict[str, str]:
    inicio, fin = _seccion(lineas)
    salida = {}
    for l in lineas[inicio + 1:fin] if inicio >= 0 else []:
        if "=" in l:
            k, v = l.split("=", 1)
            salida[k] = _valor(v)
    return salida


def cambios(ini: Path | None = None) -> list[tuple[str, str, str]]:
    """(clave, valor actual, valor nuevo) de lo que cambiaría; vacía si TeXstudio ya compila con LaTeX Studio."""
    ini = ini or ruta_ini()
    actuales = _actuales(_leer(ini)) if ini.is_file() else {}
    return [(k, actuales.get(k, ""), v) for k, v in deseado().items() if actuales.get(k, "") != v]


def configurado(ini: Path | None = None) -> bool:
    return (ini or ruta_ini()).is_file() and not cambios(ini)


def texstudio_abierto() -> bool:
    try:
        return subprocess.run(["pgrep", "-x", "texstudio"], capture_output=True).returncode == 0
    except OSError:
        return False


def aplicar(ini: Path | None = None) -> str:
    """Escribe los cambios con respaldo; devuelve "" o el motivo por el que no se hizo."""
    ini = ini or ruta_ini()
    if texstudio_abierto():
        return "Cierra TeXstudio antes: al salir reescribe su configuración y se perdería el cambio."
    if not ini.is_file():
        return f"No encuentro la configuración de TeXstudio ({ini}): ábrelo y ciérralo una vez para que la cree."
    lista = cambios(ini)
    if not lista:
        return ""
    respaldo = ini.with_name(f"texstudio.ini.antes-latex-studio-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(ini, respaldo)
    lineas = _leer(ini)
    inicio, fin = _seccion(lineas)
    if inicio < 0:
        return f"La configuración de TeXstudio no tiene la sección [{GRUPO}]; no se tocó nada."
    nuevos = dict((k, v) for k, _a, v in lista)
    for i in range(inicio + 1, fin):
        clave = lineas[i].split("=", 1)[0]
        if clave in nuevos:
            lineas[i] = f"{clave}={nuevos.pop(clave)}"
    for clave, valor in nuevos.items():           # las que no estaban: al final de la sección
        lineas.insert(fin, f"{clave}={valor}")
        fin += 1
    ini.write_text("\n".join(lineas), encoding="utf-8", errors="surrogateescape")
    return ""


def deshacer(ini: Path | None = None) -> str:
    ini = ini or ruta_ini()
    if texstudio_abierto():
        return "Cierra TeXstudio antes de deshacer."
    respaldos = sorted(ini.parent.glob("texstudio.ini.antes-latex-studio-*"))
    if not respaldos:
        return "No hay respaldo que restaurar."
    shutil.copy2(respaldos[-1], ini)
    return ""


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    if "--deshacer" in sys.argv:
        e = deshacer()
        print(e or "Restaurado el último respaldo de TeXstudio.")
        sys.exit(1 if e else 0)
    lista = cambios()
    if not lista:
        print("TeXstudio ya compila con LaTeX Studio.")
        sys.exit(0)
    for clave, actual, nuevo in lista:
        print(f"{clave}: «{actual}» → «{nuevo}»")
    if "--aplicar" in sys.argv:
        e = aplicar()
        print(e or f"Hecho (respaldo junto a {ruta_ini()}).")
        sys.exit(1 if e else 0)
    print("SIMULACIÓN (usa --aplicar)")
