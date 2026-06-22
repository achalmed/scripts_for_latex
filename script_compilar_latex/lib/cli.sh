#!/usr/bin/env bash
# ==============================================================================
# lib/cli.sh — Interfaz de línea de comandos (parseo de argumentos)
# Proyecto: compilar_latex
# ==============================================================================

# mostrar_ayuda()
# Imprime la ayuda completa y sale con código 0.
mostrar_ayuda() {
    cat <<EOF

${BOLD}${SCRIPT_NAME}${NC} v${VERSION} — Compilador universal LaTeX

${BOLD}USO${NC}
  ./compilar_latex.sh [OPCIONES] [ARCHIVO_O_RUTA]

${BOLD}ARCHIVO / RUTA${NC}
  Puede ser cualquiera de estas formas:
    index                          → busca index.tex en el directorio actual
    tesis                          → busca tesis.tex en el directorio actual
    ../pub_dialectica/capitulo1    → ruta relativa al directorio actual
    /home/achalmaedison/Documents/pub_dialectica/articulo
                                   → ruta absoluta completa
    ~/Documents/03\ writing/nota   → con tilde de home

  Si no se indica, el default es: ${BOLD}index${NC}
  La extensión .tex es opcional (se añade automáticamente si falta).

${BOLD}MOTOR${NC}
  -e, --engine ENGINE     Motor LaTeX a usar:
                            auto      detecta automáticamente (default)
                            pdflatex  máxima compatibilidad
                            xelatex   Unicode nativo, fuentes del sistema
                            lualatex  Lua embebido, tipografía avanzada

  Detección automática inspecciona el .tex buscando:
    fontspec / polyglossia / unicode-math → xelatex
    \\directlua / luacode                  → lualatex
    (nada especial)                        → pdflatex

${BOLD}COMPILACIÓN${NC}
  -p, --pasadas N         Número de compilaciones (default: 2)
                          Se ajusta a 3 automáticamente si usas bibliografía.
  --draft                 Modo borrador: omite imágenes, más rápido.

${BOLD}BIBLIOGRAFÍA E ÍNDICES${NC}
  -b, --bibtex            Ejecuta BibTeX entre compilaciones.
  --biber                 Ejecuta Biber (para biblatex) en lugar de BibTeX.
  -i, --makeindex         Ejecuta makeindex para índices temáticos.
  -g, --makeglossaries    Ejecuta makeglossaries para glosarios.

${BOLD}SALIDA${NC}
  -o, --output DIR        Mueve el PDF generado al directorio indicado.
  -s, --silencioso        Suprime la salida del compilador (solo errores).
  -v, --verbose           Muestra la salida completa del compilador.
  -a, --abrir             Abre el PDF automáticamente al terminar.
  --log FILE              Guarda el log en FILE (default: ARCHIVO.log).

${BOLD}UTILIDADES${NC}
  -c, --limpiar           Elimina archivos auxiliares y sale.
  -w, --watch             Modo vigilancia: recompila al detectar cambios.
  -h, --help              Muestra esta ayuda.
      --version           Muestra la versión.

${BOLD}EJEMPLOS${NC}
  # Compilar index.tex en el directorio actual (detección automática de motor)
  ./compilar_latex.sh

  # Compilar un archivo en cualquier lugar de tu sistema
  ./compilar_latex.sh ~/Documents/pub_dialectica-y-mercado/articulo
  ./compilar_latex.sh /home/achalmaedison/Documents/03\ writing/nota_metodologica

  # Documento con bibliografía (biblatex + Biber)
  ./compilar_latex.sh --biber -p 3 ~/Documents/pub_axiomata/paper

  # Presentación Beamer con XeLaTeX, abrir al terminar
  ./compilar_latex.sh -e xelatex -a ~/Documents/03\ writing/slides_unsch

  # LuaLaTeX con índice y glosario, salida en build/
  ./compilar_latex.sh -e lualatex -i -g -o build ~/Documents/pub_res-publica/libro

  # Modo watch durante la escritura
  ./compilar_latex.sh -w ~/Documents/02\ analysis/informe

  # Solo limpiar auxiliares de un documento
  ./compilar_latex.sh -c ~/Documents/pub_numerus-scriptum/capitulo2

  # Compilar silenciosamente (para CI/CD o cron)
  ./compilar_latex.sh -s ~/Documents/03\ writing/reporte && echo "OK"

${BOLD}VARIABLES DE ENTORNO${NC}
  NO_COLOR=1    Desactiva todos los colores en la salida.

${BOLD}ARCHIVOS AUXILIARES QUE SE LIMPIAN${NC}
  .aux .bbl .bcf .blg .fdb_latexmk .fls .glg .glo .gls .idx .ilg .ind
  .ist .lof .log .lot .nav .out .run.xml .snm .synctex.gz .toc .vrb .xdv .ptc

EOF
}

# parsear_args()
# Lee todos los argumentos de la línea de comandos y configura las variables globales.
#
# Arguments:
#   "$@" — todos los argumentos pasados a main.sh
#
# Sets (global):
#   ARCHIVO ENGINE PASADAS MODO_SILENCIOSO SOLO_LIMPIAR MODO_WATCH
#   MODO_DRAFT DIRECTORIO_SALIDA USAR_BIBTEX USAR_BIBER USAR_MAKEINDEX
#   USAR_MAKEGLOSSARIES ABRIR_PDF VERBOSE LOG_FILE
parsear_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -e|--engine)
                ENGINE="${2:?"--engine requiere un argumento: auto|pdflatex|xelatex|lualatex"}"
                validar_engine "$ENGINE" || exit 1
                shift 2
                ;;
            -p|--pasadas)
                PASADAS="${2:?"--pasadas requiere un número"}"
                validar_pasadas "$PASADAS" || exit 1
                shift 2
                ;;
            -o|--output)
                DIRECTORIO_SALIDA="${2:?"--output requiere una ruta de directorio"}"
                shift 2
                ;;
            --log)
                LOG_FILE="${2:?"--log requiere una ruta de archivo"}"
                shift 2
                ;;
            -s|--silencioso)    MODO_SILENCIOSO=true;      shift ;;
            -v|--verbose)       VERBOSE=true;               shift ;;
            -c|--limpiar)       SOLO_LIMPIAR=true;          shift ;;
            -w|--watch)         MODO_WATCH=true;            shift ;;
            --draft)            MODO_DRAFT=true;            shift ;;
            -b|--bibtex)        USAR_BIBTEX=true;           shift ;;
            --biber)            USAR_BIBER=true;            shift ;;
            -i|--makeindex)     USAR_MAKEINDEX=true;        shift ;;
            -g|--makeglossaries) USAR_MAKEGLOSSARIES=true;  shift ;;
            -a|--abrir)         ABRIR_PDF=true;             shift ;;
            -h|--help)          mostrar_ayuda; exit 0       ;;
            --version)          echo "${SCRIPT_NAME} v${VERSION}"; exit 0 ;;
            -*)
                error "Opción desconocida: '$1'"
                echo "  Usa --help para ver las opciones disponibles."
                exit 1
                ;;
            *)
                # Argumento posicional: ruta o nombre del archivo .tex
                ARCHIVO="$1"
                shift
                ;;
        esac
    done

    # --bibtex y --biber son mutuamente excluyentes
    if $USAR_BIBTEX && $USAR_BIBER; then
        error "--bibtex y --biber son mutuamente excluyentes. Elige uno."
        exit 1
    fi

    # Incrementar pasadas automáticamente si se usa bibliografía o glosarios
    # (necesitan al menos 3 compilaciones para resolver todas las referencias)
    if ( $USAR_BIBTEX || $USAR_BIBER || $USAR_MAKEGLOSSARIES ) \
        && [ "$PASADAS" -lt 3 ]; then
        PASADAS=3
        warn "Pasadas ajustadas a 3 para resolver referencias bibliográficas / glosarios."
    fi

    # Log por defecto: se define después de resolver la ruta del .tex (en main)
    # Aquí solo guardamos si el usuario lo especificó explícitamente.
    # (El default se asigna en main() tras resolver TEX_BASE)
}
