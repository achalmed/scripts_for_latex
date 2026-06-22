# compilar_latex — Script Universal de Compilación LaTeX

> Compila documentos LaTeX con **pdflatex**, **xelatex** o **lualatex** desde
> cualquier directorio del sistema, indicando la ruta exacta del `.tex`.
> Detecta el motor automáticamente, gestiona bibliografía, índices, glosarios,
> modo watch y limpieza de auxiliares.

---

## 📋 Tabla de Contenidos

- [Descripción](#descripción)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Uso](#uso)
- [Arquitectura](#arquitectura)
- [Bugs Corregidos](#bugs-corregidos)
- [Nuevas Funcionalidades](#nuevas-funcionalidades)
- [Solución de Problemas](#solución-de-problemas)
- [Variables de Entorno](#variables-de-entorno)
- [Cómo Contribuir](#cómo-contribuir)
- [Notas y Advertencias](#notas-y-advertencias)

---

## 📖 Descripción

`compilar_latex` es un compilador universal de LaTeX para Bash. El script
vive siempre en una carpeta fija (`scripts_for_latex/script_compilar_latex/`)
mientras que los archivos `.tex` pueden estar en **cualquier ubicación** de
tu sistema: `pub_dialectica-y-mercado/`, `03 writing/`, `pub_axiomata/`, etc.

Se invoca pasando la ruta exacta al `.tex`—absoluta, relativa o con tilde—y
el script se encarga de compilar en el directorio correcto sin mover ningún
archivo y sin requerir `cd` previos.

---

## ⚙️ Requisitos

### Sistema Operativo

- Linux (Arch, Archcraft, Kubuntu, Ubuntu, Debian, Fedora) ✓
- macOS ✓ (requiere `fswatch` para modo watch)

### Dependencias obligatorias

| Herramienta | Paquete (Arch) | Paquete (Debian/Ubuntu) | Para qué |
|-------------|----------------|--------------------------|----------|
| `pdflatex` / `xelatex` / `lualatex` | `texlive-most` | `texlive-full` | Motor de compilación |

### Dependencias opcionales

| Herramienta | Paquete | Para qué |
|-------------|---------|----------|
| `bibtex` | incluido en texlive | Bibliografía clásica (`-b`) |
| `biber` | `biber` | Bibliografía con biblatex (`--biber`) |
| `makeindex` | incluido en texlive | Índices temáticos (`-i`) |
| `makeglossaries` | `texlive-glossaries` | Glosarios (`-g`) |
| `pdfinfo` | `poppler` / `poppler-utils` | Mostrar páginas y metadata del PDF |
| `inotifywait` | `inotify-tools` | Modo watch en Linux (`-w`) |
| `fswatch` | `fswatch` (Homebrew) | Modo watch en macOS (`-w`) |
| `evince` / `okular` / `zathura` | (varios) | Abrir PDF automáticamente (`-a`) |

```bash
# Arch Linux / Archcraft
sudo pacman -S texlive-most biber poppler inotify-tools

# Kubuntu / Debian / Ubuntu
sudo apt install texlive-full biber poppler-utils inotify-tools

# macOS
brew install --cask mactex && brew install poppler fswatch
```

---

## 🚀 Instalación

### Paso 1: Ubicar el script

El script vive siempre en su carpeta, nunca se mueve:

```
~/Documents/scripts_for_latex/script_compilar_latex/
├── main.sh          ← punto de entrada
├── config.sh
├── README.md
└── lib/
    ├── logger.sh
    ├── resolver.sh
    ├── detector.sh
    ├── validator.sh
    ├── cli.sh
    ├── compiler.sh
    ├── output.sh
    └── watch.sh
```

### Paso 2: Permisos de ejecución

```bash
cd ~/Documents/scripts_for_latex/script_compilar_latex
chmod +x main.sh lib/*.sh config.sh
```

### Paso 3: Crear alias para acceso global (recomendado)

Agrega esta línea a tu shell de configuración y ya no necesitas escribir
la ruta completa nunca más:

```bash
# ~/.zshrc  (zsh — tu shell actual en Kubuntu/Arch)
alias compilar='~/Documents/scripts_for_latex/script_compilar_latex/main.sh'

# ~/.config/fish/config.fish  (fish — tu otra shell)
alias compilar '~/Documents/scripts_for_latex/script_compilar_latex/main.sh'
```

Recarga la configuración:

```bash
source ~/.zshrc      # zsh
# o abre una nueva terminal
```

Desde este momento puedes usar `compilar` desde cualquier directorio.

---

## 💻 Uso

### Sintaxis

```bash
# Invocación directa (sin alias)
~/Documents/scripts_for_latex/script_compilar_latex/main.sh [OPCIONES] [RUTA]

# Con alias (recomendado)
compilar [OPCIONES] [RUTA]
```

### Formas de indicar el archivo .tex

```bash
# Solo nombre base → busca en el directorio actual
compilar tesis
compilar index

# Ruta relativa al directorio actual
compilar ../pub_dialectica-y-mercado/articulo
compilar 03\ writing/nota_metodologica

# Ruta con tilde
compilar ~/Documents/pub_axiomata/paper
compilar ~/Documents/03\ writing/informe_unsch

# Ruta absoluta completa
compilar /home/achalmaedison/Documents/pub_res-publica/capitulo1

# Con extensión .tex explícita (también funciona)
compilar ~/Documents/pub_numerus-scriptum/python_intro.tex
```

### Opciones completas

| Flag | Descripción | Default |
|------|-------------|---------|
| `-e, --engine ENGINE` | Motor: `auto`, `pdflatex`, `xelatex`, `lualatex` | `auto` |
| `-p, --pasadas N` | Número de compilaciones | `2` (o `3` con biblio) |
| `--draft` | Modo borrador: más rápido, sin imágenes | desactivado |
| `-b, --bibtex` | Ejecuta BibTeX entre compilaciones | — |
| `--biber` | Ejecuta Biber (para biblatex) | — |
| `-i, --makeindex` | Ejecuta makeindex | — |
| `-g, --makeglossaries` | Ejecuta makeglossaries | — |
| `-o, --output DIR` | Mueve el PDF al directorio indicado | (en el dir del .tex) |
| `-s, --silencioso` | Suprime salida del compilador | — |
| `-v, --verbose` | Muestra salida completa del compilador | — |
| `-a, --abrir` | Abre el PDF automáticamente al terminar | — |
| `--log FILE` | Guarda el log en FILE | `ARCHIVO.log` |
| `-c, --limpiar` | Solo elimina auxiliares y sale | — |
| `-w, --watch` | Recompila automáticamente al detectar cambios | — |
| `-h, --help` | Muestra la ayuda | — |
| `--version` | Muestra la versión | — |

### Ejemplos por caso de uso

```bash
# ── 1. Artículo simple ──────────────────────────────────────────────────────
# (motor detectado automáticamente según el contenido del .tex)
compilar ~/Documents/pub_dialectica-y-mercado/articulo_main

# ── 2. Tesis con Biber (biblatex) ──────────────────────────────────────────
compilar --biber -p 3 ~/Documents/03\ writing/tesis_economia

# ── 3. Presentación Beamer, abrir al terminar ───────────────────────────────
compilar -e xelatex -a ~/Documents/03\ writing/slides_microeconomia

# ── 4. Libro con índice, glosario y salida en build/ ───────────────────────
compilar -e lualatex -i -g -o build ~/Documents/pub_res-publica/libro_metodologia

# ── 5. Modo watch durante la escritura ──────────────────────────────────────
compilar -w ~/Documents/02\ analysis/informe_islm

# ── 6. Solo limpiar auxiliares de un documento ──────────────────────────────
compilar -c ~/Documents/pub_chaska/presentacion

# ── 7. Compilar silenciosamente (scripts CI o cron) ─────────────────────────
compilar -s ~/Documents/pub_axiomata/paper && echo "OK" || echo "ERROR"

# ── 8. Modo borrador para escritura rápida ──────────────────────────────────
compilar --draft ~/Documents/pub_numerus-scriptum/python_economists

# ── 9. Forzar motor específico ignorando la detección automática ─────────────
compilar -e lualatex ~/Documents/CampusTeX-Preuniversitario/modulo_algebra

# ── 10. Debug con log personalizado ─────────────────────────────────────────
compilar -v --log /tmp/debug_latex.log ~/Documents/pub_epsilon-y-beta/econometria
```

---

## 🗂️ Arquitectura

```
script_compilar_latex/
├── main.sh          # Punto de entrada: carga módulos, define variables globales,
│                    # orquesta el flujo completo de compilación
├── config.sh        # Valores por defecto, constantes, inicialización de colores
├── README.md        # Esta documentación
└── lib/
    ├── logger.sh    # Funciones de salida: info, ok, warn, error, paso, titulo
    ├── resolver.sh  # Resuelve cualquier ruta al .tex → TEX_DIR / TEX_BASE / TEX_PATH
    ├── detector.sh  # Detecta el motor LaTeX apropiado inspeccionando el .tex
    ├── validator.sh # Valida argumentos CLI y verifica dependencias del sistema
    ├── cli.sh       # Parseo de argumentos y texto de ayuda
    ├── compiler.sh  # Invoca LaTeX, BibTeX/Biber, makeindex, makeglossaries;
    │                # construye flags; muestra errores del log; limpia auxiliares
    ├── output.sh    # Banner, info del PDF (tamaño/páginas/metadata), mover PDF,
    │                # abrir PDF, sugerir apertura manual
    └── watch.sh     # Modo watch: inotifywait (Linux) / fswatch (macOS)
```

### Responsabilidad de cada módulo

| Archivo | Responsabilidad |
|---------|----------------|
| `main.sh` | Punto de entrada. Carga módulos, inicializa variables, llama `parsear_args → resolver_ruta_tex → detectar_engine → verificar_dependencias → compilar / modo_watch`. Define `compilar()` que orquesta el ciclo completo de pasadas. |
| `config.sh` | Todos los defaults y constantes en un solo lugar. Cambiar `DEFAULT_ENGINE` o `DEFAULT_PASADAS` aquí afecta todo el script. |
| `lib/logger.sh` | `info`, `ok`, `warn`, `error`, `paso`, `titulo`, `separador`, `dim`. Toda salida al usuario pasa por aquí. |
| `lib/resolver.sh` | Acepta cualquier forma de ruta (absoluta, relativa, tilde, con o sin `.tex`) y resuelve `TEX_PATH`, `TEX_DIR`, `TEX_BASE`. |
| `lib/detector.sh` | Inspecciona el `.tex` con grep buscando `fontspec`, `luacode`, etc. y elige `pdflatex`, `xelatex` o `lualatex`. |
| `lib/validator.sh` | Valida engine, pasadas, y que todos los binarios requeridos estén instalados. |
| `lib/cli.sh` | `parsear_args()` y `mostrar_ayuda()`. |
| `lib/compiler.sh` | `ejecutar_latex`, `ejecutar_bibliografia`, `ejecutar_indices`, `mostrar_errores_log`, `limpiar_auxiliares`. Siempre hace `pushd TEX_DIR` antes de compilar. |
| `lib/output.sh` | `banner`, `mostrar_info_pdf`, `mover_pdf`, `abrir_pdf`, `sugerir_apertura`, `elapsed`. |
| `lib/watch.sh` | `modo_watch`, `compilar_segura`, `_watch_linux`, `_watch_macos`. |

---

## 🐛 Bugs Corregidos

### Bug #1: `set -euo pipefail` rompía el modo watch

- **Ubicación**: `set -e` global + `compilar_segura()` (línea 620 original)
- **Descripción**: El `set -e` global hacía que el `|| { ... }` en
  `compilar_segura` no capturase el error correctamente; cualquier fallo
  de compilación terminaba el proceso watch en vez de continuar esperando.
- **Corrección**: En `lib/watch.sh`, `compilar_segura()` desactiva `set -e`
  localmente (`set +e`) antes de llamar a `compilar`, captura el código de
  retorno explícitamente y reactiva `set -e` antes de retornar.

### Bug #2: `local status=${PIPESTATUS[0]}` siempre retornaba 0

- **Ubicación**: `ejecutar_latex()` (líneas 335 y 346 originales)
- **Descripción**: En Bash, `local variable=$(comando)` evalúa `local` como
  el comando y su exit code siempre es 0, descartando el exit code real.
  El error del motor LaTeX pasaba silenciosamente desapercibido.
- **Corrección**: En `lib/compiler.sh`, se declara `local status=0` primero
  y luego se asigna `status=${PIPESTATUS[0]}` en línea separada.

### Bug #3: `limpiar_auxiliares()` no encontraba los auxiliares

- **Ubicación**: `limpiar_auxiliares()` (línea 432 original)
- **Descripción**: Cuando `ARCHIVO` contenía una ruta (no solo un nombre base),
  la función construía rutas incorrectas: buscaba `ruta/al/tex/nombre.aux` en
  el CWD del script en lugar de en el directorio del `.tex`.
- **Corrección**: La función ahora usa `TEX_DIR` y `TEX_BASE` (siempre
  absolutos y correctamente resueltos) en lugar de `ARCHIVO` crudo. Además
  ejecuta la limpieza con `pushd "$TEX_DIR"` para manejar correctamente
  los `.aux` de subdirectorios con `\include`.

---

## ✨ Nuevas Funcionalidades

### 1. Ruta absoluta / relativa al `.tex`

**Antes**: El script compilaba solo archivos en el directorio donde se ejecutaba.
Era necesario hacer `cd` al directorio del `.tex` antes de invocar el script.

**Ahora**: Se puede indicar cualquier ruta:

```bash
compilar ~/Documents/pub_dialectica-y-mercado/capitulo1
compilar ../pub_axiomata/paper
compilar /home/achalmaedison/Documents/pub_res-publica/libro
```

El módulo `lib/resolver.sh` resuelve la ruta, y `lib/compiler.sh` compila
siempre con `pushd "$TEX_DIR"` para que LaTeX encuentre todos los archivos
relativos (`\include`, `\input`, imágenes, `.bib`, `.sty`).

### 2. Detección automática del motor LaTeX

**Antes**: El motor por defecto era siempre `pdflatex`.

**Ahora**: Con `--engine auto` (nuevo default), el módulo `lib/detector.sh`
inspecciona el `.tex` y elige:

| Indicadores en el `.tex` | Motor elegido |
|--------------------------|---------------|
| `\directlua`, `\luaexec`, `\luacode` | `lualatex` |
| `\usepackage{fontspec}`, `\usepackage{polyglossia}`, `\usepackage{unicode-math}` | `xelatex` |
| (ninguno de los anteriores) | `pdflatex` |

El motor detectado se muestra en la salida para que siempre sepas cuál se usó.
Puedes sobreescribirlo con `-e pdflatex` si lo necesitas.

---

## 🔧 Solución de Problemas

### "No se encontró el archivo: ..."

El script muestra los `.tex` disponibles en el directorio indicado.
Verifica:

```bash
# ¿Existe el archivo?
ls ~/Documents/pub_dialectica-y-mercado/*.tex

# ¿La ruta tiene espacios? Usa comillas o escapa el espacio
compilar "~/Documents/03 writing/nota"
compilar ~/Documents/03\ writing/nota
```

### "command not found: xelatex / lualatex"

```bash
# Arch Linux / Archcraft
sudo pacman -S texlive-most

# Kubuntu / Ubuntu
sudo apt install texlive-full

# Verificar instalación
which xelatex && xelatex --version
```

### El PDF no actualiza las referencias bibliográficas

Usa al menos 3 pasadas con el procesador de bibliografía:

```bash
compilar --biber -p 3 ~/Documents/pub_axiomata/paper
```

### Error de fuente con XeLaTeX

```bash
# Verificar que la fuente esté instalada en el sistema
fc-list | grep -i "NombreDeLaFuente"

# Listar todas las fuentes disponibles
fc-list | sort
```

### Modo watch no detecta cambios

```bash
# Arch Linux / Archcraft
sudo pacman -S inotify-tools

# Kubuntu / Ubuntu
sudo apt install inotify-tools

# Verificar
which inotifywait
```

### El PDF no se abre automáticamente (`-a`)

```bash
# Instalar un visor
sudo pacman -S zathura     # Arch (liviano, recomendado)
sudo apt install evince     # Kubuntu / Ubuntu

# Verificar visores disponibles
which evince okular zathura atril xpdf
```

### El motor detectado automáticamente no es el correcto

Especifícalo explícitamente para ignorar la detección:

```bash
compilar -e pdflatex ~/Documents/mi_documento
compilar -e lualatex ~/Documents/CampusTeX-Preuniversitario/modulo
```

---

## 🌍 Variables de Entorno

| Variable | Efecto |
|----------|--------|
| `NO_COLOR=1` | Desactiva todos los colores en la salida (estándar no-color.org) |

```bash
NO_COLOR=1 compilar ~/Documents/pub_axiomata/paper
```

---

## 🤝 Cómo Contribuir / Agregar Funcionalidades

### Para agregar una nueva opción CLI

1. Agrega el flag en `lib/cli.sh` dentro del `case "$1" in`.
2. Declara la variable global con su default en `main.sh`.
3. Agrega el default en `config.sh` si es configurable.
4. Implementa la lógica en el módulo correspondiente de `lib/`.
5. Documenta el flag en `mostrar_ayuda()` (lib/cli.sh) y en este README.

### Para agregar soporte a un nuevo motor

1. Agrega el nombre en `validar_engine()` (lib/validator.sh).
2. Agrega la heurística de detección en `detectar_engine()` (lib/detector.sh).
3. Agrega flags especiales si aplica en `construir_flags()` (lib/compiler.sh).

### Estándares de código

- Máximo 30 líneas por función; si supera, divide con subfunciones.
- Nombres en inglés técnico: `build_argument_parser`, no `hacer_cosas`.
- Documenta el **por qué**, no el **qué** (el código ya dice el qué).
- Siempre usa `pushd / popd` cuando cambies de directorio dentro de una función.
- Valida antes de actuar: verifica que el archivo exista antes de procesarlo.

---

## ⚠️ Notas y Advertencias

**Sobre rutas con espacios**: Siempre usa comillas o escapes:

```bash
compilar "~/Documents/03 writing/mi nota"
compilar ~/Documents/03\ writing/mi\ nota
```

**Sobre `--output DIR`**: El directorio especificado es relativo al CWD
donde se invoca el script, no al directorio del `.tex`. Si necesitas una
ruta absoluta, úsala directamente: `-o /home/achalmaedison/pdfs`.

**Sobre el modo watch en proyectos con `\include`**: El watch vigila todo
el `TEX_DIR`. Si tus capítulos están en subdirectorios del `.tex` principal
(por ejemplo `capitulos/intro.tex`), también se detectarán sus cambios.

**Sobre la limpieza de auxiliares**: El `.log` se elimina junto con los
demás auxiliares al terminar. Si necesitas conservarlo para depuración,
usa `--log /ruta/de/backup.log` antes de compilar: ese archivo no se elimina.

**Sobre LuaLaTeX y proyectos CampusTeX**: LuaLaTeX es notablemente más lento
que pdflatex/xelatex en proyectos grandes. Si solo necesitas compatibilidad
Unicode sin scripting Lua, usa xelatex para mejor rendimiento.
