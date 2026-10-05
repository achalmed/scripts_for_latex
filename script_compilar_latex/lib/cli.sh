#!/usr/bin/env bash
# ==============================================================================
# lib/cli.sh — Interfaz de línea de comandos (parseo de argumentos)
# ==============================================================================

# mostrar_ayuda()
# Imprime la ayuda completa y sale con código 0.
mostrar_ayuda() {
    cat <<EOF

${BOLD}${SCRIPT_NAME}${NC} v${VERSION} — Compilador universal LaTeX

${BOLD}USO${NC}
  compilar [OPCIONES] [ARCHIVO_O_RUTA]

${BOLD}ARCHIVO / RUTA${NC}
  Puede ser cualquiera de estas formas:
    index                          → busca index.tex en el directorio actual
    tesis                          → busca tesis.tex en el directorio actual
    ../pub_dialectica/capitulo1    → ruta relativa al directorio actual
    ~/Documents/04\ index/_pubs/pub_dialectica/articulo
                                   → ruta absoluta completa
    ~/Documents/03\ writing/nota   → con tilde de home

  Si no se indica, el default es: ${BOLD}index${NC}
  La extensión .tex es opcional (se añade automáticamente si falta).

${BOLD}MOTOR${NC}
  -e, --engine ENGINE     Motor LaTeX a usar:
                            auto      lualatex, salvo %!TEX program (default)
                            lualatex  el motor del ecosistema
                            pdflatex  solo para material heredado que lo exija
                            xelatex   solo para material heredado que lo exija

  auto lee las 5 primeras líneas del .tex: «% !TEX program = pdflatex|xelatex|lualatex»
  manda; sin esa línea, lualatex (regla del ecosistema: LuaLaTeX + Biber).

${BOLD}COMPILACIÓN${NC}
  -p, --pasadas N         Número de compilaciones (default: 2)
                          Se ajusta a 3 automáticamente si usas bibliografía.
  --draft                 Modo borrador: comprueba que compila, SIN producir PDF.

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
  -n, --dry-run           Simula: dice qué ejecutaría (y, con -c, qué borraría) sin escribir nada.
  -w, --watch             Modo vigilancia: recompila al detectar cambios.
  -h, --help              Muestra esta ayuda.
      --version           Muestra la versión.

${BOLD}EJEMPLOS${NC}
  # Compilar index.tex en el directorio actual (detección automática de motor)
  compilar

  # Compilar un archivo en cualquier lugar de tu sistema
  compilar ~/Documents/04\ index/_pubs/pub_dialectica-y-mercado/articulo
  compilar ~/Documents/03\ writing/nota_metodologica

  # Documento con bibliografía (biblatex + Biber)
  compilar --biber -p 3 ~/Documents/04\ index/_pubs/pub_axiomata/paper

  # Presentación Beamer con bibliografía, abrir al terminar
  compilar --biber -a ~/Documents/03\ writing/slides_unsch

  # LuaLaTeX con índice y glosario, salida en build/
  compilar -e lualatex -i -g -o build ~/Documents/04\ index/_pubs/pub_res-publica/libro

  # Modo watch durante la escritura
  compilar -w ~/Documents/02\ analysis/informe

  # Solo limpiar auxiliares de un documento
  compilar -c ~/Documents/04\ index/_pubs/pub_numerus-scriptum/capitulo2

  # Compilar silenciosamente (para CI/CD o cron)
  compilar -s ~/Documents/03\ writing/reporte && echo "OK"

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
#   USAR_MAKEGLOSSARIES ABRIR_PDF VERBOSE LATEX_LOG MODO_SIMULAR
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
                LATEX_LOG="${2:?"--log requiere una ruta de archivo"}"
                shift 2
                ;;
            -s|--silencioso)    MODO_SILENCIOSO=true;      shift ;;
            -v|--verbose)       VERBOSE=true;               shift ;;
            -c|--limpiar)       SOLO_LIMPIAR=true;          shift ;;
            -n|--dry-run)       MODO_SIMULAR=true;          shift ;;
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
