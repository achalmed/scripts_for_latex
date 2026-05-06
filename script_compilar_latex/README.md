# compilar_latex.sh — Script Universal de Compilación LaTeX

Script de shell completo para compilar documentos LaTeX con **pdflatex**, **XeLaTeX** y **LuaLaTeX**, con soporte para bibliografía, índices, glosarios, modo watch, limpieza automática y mucho más.

---

## Características

| Funcionalidad            | Detalle                                            |
| ------------------------ | -------------------------------------------------- |
| **3 motores**            | pdflatex · xelatex · lualatex                      |
| **Bibliografía**         | BibTeX (`-b`) y Biber (`--biber`)                  |
| **Índices**              | makeindex (`-i`) y makeglossaries (`-g`)           |
| **Modo watch**           | Recompila automáticamente al guardar (`-w`)        |
| **Modo draft**           | Compilación rápida sin imágenes (`--draft`)        |
| **Limpieza**             | Elimina todos los auxiliares al terminar           |
| **Directorio de salida** | Mueve el PDF a donde quieras (`-o DIR`)            |
| **Abrir PDF**            | Detecta y usa el visor disponible (`-a`)           |
| **Colores y feedback**   | Mensajes claros con iconos y colores               |
| **Detección de errores** | Muestra extracto del log en caso de fallo          |
| **Info del PDF**         | Páginas, tamaño, título y autor                    |
| **SyncTeX**              | Generado automáticamente (compatible con editores) |

---

## Requisitos

### LaTeX

Instala una distribución TeX completa:

```bash
# Debian / Ubuntu
sudo apt install texlive-full

# Fedora / RHEL
sudo dnf install texlive-scheme-full

# macOS (con Homebrew)
brew install --cask mactex

# Arch Linux
sudo pacman -S texlive-most
```

### Herramientas opcionales

| Herramienta   | Paquete              | Para qué                           |
| ------------- | -------------------- | ---------------------------------- |
| `pdfinfo`     | `poppler-utils`      | Mostrar páginas y metadata del PDF |
| `inotifywait` | `inotify-tools`      | Modo watch en Linux                |
| `fswatch`     | `fswatch` (Homebrew) | Modo watch en macOS                |

```bash
# Linux
sudo apt install poppler-utils inotify-tools

# macOS
brew install poppler fswatch
```

---

## Instalación

```bash
# Descargar o copiar el script
chmod +x compilar_latex.sh

# (Opcional) Moverlo a tu PATH para usarlo desde cualquier directorio
sudo cp compilar_latex.sh /usr/local/bin/compilar_latex
```

---

## Uso rápido

```bash
./compilar_latex.sh [OPCIONES] [ARCHIVO]
```

Si no se indica `ARCHIVO`, se usa `index` (compila `index.tex`).

---

## Opciones completas

### Compilación

| Opción                | Descripción                                                  |
| --------------------- | ------------------------------------------------------------ |
| `-e, --engine ENGINE` | Motor LaTeX: `pdflatex` (por defecto), `xelatex`, `lualatex` |
| `-p, --pasadas N`     | Número de compilaciones (por defecto: 2)                     |
| `--draft`             | Modo borrador: más rápido, sin imágenes embebidas            |

### Bibliografía e índices

| Opción                 | Descripción                                       |
| ---------------------- | ------------------------------------------------- |
| `-b, --bibtex`         | Ejecuta BibTeX entre compilaciones                |
| `--biber`              | Ejecuta Biber (para biblatex) entre compilaciones |
| `-i, --makeindex`      | Ejecuta makeindex para índices temáticos          |
| `-g, --makeglossaries` | Ejecuta makeglossaries para glosarios             |

### Salida

| Opción             | Descripción                               |
| ------------------ | ----------------------------------------- |
| `-o, --output DIR` | Mueve el PDF al directorio indicado       |
| `-s, --silencioso` | Suprime la salida del compilador          |
| `-v, --verbose`    | Muestra la salida completa del compilador |
| `-a, --abrir`      | Abre el PDF automáticamente al terminar   |
| `--log FILE`       | Guarda el log en un archivo personalizado |

### Utilidades

| Opción          | Descripción                               |
| --------------- | ----------------------------------------- |
| `-c, --limpiar` | Solo elimina archivos auxiliares y sale   |
| `-w, --watch`   | Modo watch: recompila al detectar cambios |
| `-h, --help`    | Muestra la ayuda                          |

---

## Ejemplos por caso de uso

### 1. Compilación básica (artículo, informe, tarea)

```bash
# Compilar index.tex con pdflatex (la configuración más simple)
./compilar_latex.sh

# Especificar un archivo diferente
./compilar_latex.sh mi_informe
./compilar_latex.sh reporte_final
```

### 2. Presentación Beamer

```bash
# Con pdflatex (compatible con la mayoría de temas)
./compilar_latex.sh slides

# Con XeLaTeX para usar fuentes del sistema en la presentación
./compilar_latex.sh -e xelatex slides
```

### 3. Tesis o documento largo con bibliografía

```bash
# Con BibTeX (referencias .bib clásicas)
./compilar_latex.sh -e pdflatex -b -p 3 tesis

# Con biblatex + Biber (recomendado para documentos modernos)
./compilar_latex.sh -e xelatex --biber -p 3 tesis

# Con LuaLaTeX + Biber (máxima compatibilidad Unicode y fuentes)
./compilar_latex.sh -e lualatex --biber -p 3 tesis
```

### 4. Libro con índice temático y glosario

```bash
./compilar_latex.sh -e lualatex -i -g -p 3 libro
```

### 5. Documento con fuentes del sistema (xelatex/lualatex)

Ideal cuando usas `fontspec`, `polyglossia` o fuentes TTF/OTF instaladas:

```bash
# XeLaTeX: más rápido, excelente para Unicode y fuentes del sistema
./compilar_latex.sh -e xelatex documento

# LuaLaTeX: más lento pero con Lua embebido y tipografía avanzada
./compilar_latex.sh -e lualatex documento
```

### 6. Modo watch para edición continua

Recompila automáticamente cada vez que guardas el `.tex`, `.bib`, `.sty` o `.cls`:

```bash
# Modo watch básico
./compilar_latex.sh -w tesis

# Watch con XeLaTeX y bibliografía
./compilar_latex.sh -w -e xelatex --biber tesis
```

> **Tip:** Combínalo con un visor con recarga automática como Zathura o Evince para un flujo de edición en tiempo real.

### 7. Borrador rápido (draft)

Omite imágenes para compilar más rápido mientras escribes:

```bash
./compilar_latex.sh --draft tesis
```

### 8. Guardar PDF en carpeta específica

```bash
# Guardar en ./build/
./compilar_latex.sh -o build tesis

# Guardar en ruta absoluta
./compilar_latex.sh -o /home/usuario/documentos/pdfs tesis
```

### 9. Abrir el PDF automáticamente al terminar

El script detecta el visor disponible (evince, okular, zathura, etc.):

```bash
./compilar_latex.sh -a tesis
./compilar_latex.sh -e xelatex -a slides
```

### 10. Solo limpiar archivos auxiliares

Útil para hacer limpieza sin compilar, o para subir el proyecto a git:

```bash
./compilar_latex.sh -c
./compilar_latex.sh -c mi_archivo
```

### 11. Compilación silenciosa (para scripts CI/CD)

```bash
./compilar_latex.sh -s tesis && echo "OK" || echo "FALLO"
```

### 12. Máxima verbosidad (depuración)

```bash
./compilar_latex.sh -v --log debug.log tesis
```

---

## Archivos auxiliares que se limpian

El script elimina automáticamente al finalizar:

```
.aux  .bbl  .bcf  .blg  .fdb_latexmk  .fls  .glg  .glo  .gls
.idx  .ilg  .ind  .ist  .lof  .log  .lot  .nav  .out  .run.xml
.snm  .synctex.gz  .toc  .vrb  .xdv
```

> El `.log` se elimina junto con los demás auxiliares. Si necesitas conservarlo, usa `--log mi_log.txt` para guardarlo en otra ubicación antes de limpiar.

---

## Cuándo usar cada motor

| Motor        | Ideal para                                          | Codificación           | Fuentes             |
| ------------ | --------------------------------------------------- | ---------------------- | ------------------- |
| **pdflatex** | Compatibilidad máxima, artículos, presentaciones    | UTF-8 (con `inputenc`) | TeX/PostScript      |
| **xelatex**  | Unicode nativo, fuentes del sistema, multilingual   | UTF-8 nativo           | TTF/OTF del sistema |
| **lualatex** | Tipografía avanzada, scripts Lua, documentos largos | UTF-8 nativo           | TTF/OTF del sistema |

**Regla general:**

- Documento en inglés sin fuentes especiales → **pdflatex**
- Documento con caracteres especiales o fuentes del sistema → **xelatex**
- Necesitas scripting avanzado dentro del documento → **lualatex**

---

## Estructura de proyecto recomendada

```
mi_proyecto/
├── compilar_latex.sh       ← el script
├── main.tex                ← archivo principal
├── referencias.bib         ← bibliografía (si aplica)
├── capitulos/
│   ├── introduccion.tex
│   ├── desarrollo.tex
│   └── conclusiones.tex
├── imagenes/
│   └── ...
├── estilos/
│   └── mi_estilo.sty
└── build/                  ← PDFs generados (-o build)
```

Compilación para este proyecto:

```bash
./compilar_latex.sh -e xelatex --biber -o build main
```

---

## Solución de problemas

### Error: "command not found: xelatex"

```bash
# Verificar instalación
which xelatex || echo "No instalado"
sudo apt install texlive-xetex
```

### El PDF no actualiza las referencias bibliográficas

Usa al menos 3 pasadas:

```bash
./compilar_latex.sh -b -p 3 mi_doc
# o con biber:
./compilar_latex.sh --biber -p 3 mi_doc
```

### Error de fuente con XeLaTeX

Verifica que la fuente esté instalada en el sistema:

```bash
fc-list | grep -i "NombreDeLaFuente"
```

### "inotifywait: command not found" en modo watch

```bash
sudo apt install inotify-tools    # Linux
brew install fswatch              # macOS
```

### El PDF no se abre automáticamente

```bash
sudo apt install evince   # o zathura, okular
./compilar_latex.sh -a mi_doc
```

---

## Variables de entorno

| Variable     | Descripción                    |
| ------------ | ------------------------------ |
| `NO_COLOR=1` | Desactiva colores en la salida |

```bash
NO_COLOR=1 ./compilar_latex.sh tesis
```

---

## Integración con git

Añade al `.gitignore`:

```gitignore
# Auxiliares LaTeX
*.aux
*.bbl
*.bcf
*.blg
*.fdb_latexmk
*.fls
*.glg
*.glo
*.gls
*.idx
*.ilg
*.ind
*.lof
*.log
*.lot
*.nav
*.out
*.run.xml
*.snm
*.synctex.gz
*.toc
*.vrb
*.xdv

# Directorio de salida (opcional)
build/
```

---

## Licencia

Script de uso libre. Modifica, redistribuye y adapta según necesites.
