---
tipo: decision
estado: activo
titulo: "Decisiones de latex-studio"
forma: explicacion
---
# Decisiones de latex-studio

Solo decisiones vigentes, con su porqué (normativa documental §3.3). Lo pendiente vive en
`../estado.md` §Por hacer; lo hecho, en el mensaje de commit. Una decisión superada conserva su
número con una línea «superada por».

## 1. Alcance

### §1.1 Una herramienta modular para el `.tex` suelto (2026-06-22)

El script monolítico se dividió en `main.sh`, `config.sh` y un módulo por responsabilidad en `lib/`
(v3.0.0). El `.tex` puede estar en cualquier ruta y se compila dentro de su carpeta. Motivo: una
sola puerta de entrada para lo que no pertenece a un framework (un post con LaTeX, una nota, una
prueba) sin copiar el script a cada carpeta.

### §1.2 Los frameworks compilan con su propio build (2026-09-20)

`escritura`, `11 Book`, `sgdp/marco_documental` y los `academic-*` de `docencia` no pasan por
aquí; un cambio en este repo no puede romperlos. El único consumidor por código es `compile_tex` de
`docencia` para los `.tex` que no son del framework (contrato en `arquitectura.md` §Consumidores).

### §1.3 No trae diseño (2026-09-20)

Ni clases, ni plantillas, ni preámbulos: eso es de `estilos-visuales` y de cada framework.

### §1.4 Sin latexmk (2026-06-22)

Pasadas fijas (`-p`), 3 en cuanto se pide bibliografía o glosario: quien compila ve y controla
cada pasada.

### §1.5 La carpeta se llama `scripts-latex`; el remoto sigue siendo `scripts_for_latex` (2026-10-05; superada por §1.6)

Renombre aprobado en la Puerta P3 (P3-1: carpeta = `id`, kebab) y aplicado como piloto 1 del
programa con `core/renombrar.py`; el manifiesto guarda `id_anterior: scripts_for_latex`. El remoto
de GitHub no cambia (plan de conversión, C7). Los consumidores leen la carpeta por `SCRIPTS_LATEX`
(`core/env.sh`), salvo el alias de `~/.dotfiles`, que no carga `core/`.

### §1.6 LaTeX Studio: la carpeta pasa a `latex-studio` y la herramienta gana ventana (2026-10-31)

Propuesta aprobada por el autor (`meta/programa/08-mantenimiento/familia-studios-2026-10-31.md`): el repo es un
proyecto independiente de la familia de los studios (Filesystem, Git, Quarto, Raphi). Renombre con
`core/renombrar.py` (etiqueta, respaldo y `UNDO.sh` en `$RESPALDOS_DIR/renombres/2026-10-31-scripts-latex-a-latex-studio/`);
el remoto sigue siendo `scripts_for_latex` y `SCRIPTS_LATEX` sigue siendo el nombre de la variable (contrato de
`core`): solo cambió su valor. La ventana (`studio/`, con el marco común `gui_comun` y acento rosa) no compila por su
cuenta: arma la orden de `script_compilar_latex` y lee el `.log` para mostrar cada error y aviso con su línea; la CLI
y su interfaz para `docencia` no cambian. «Recompilar al guardar» lo hace la ventana (con `QFileSystemWatcher`),
porque el `-w` de la CLI necesita `inotifywait`.

### §1.7 La ventana en QML + Kirigami sobre gui-comun 2.x (2026-11-02)

Fase 5 de la modernización de la familia de studios: la ventana de Widgets (tres páginas, tarjetas y cifras) se
reescribe como espacio de trabajo al estilo Dolphin/Kate sobre `gui-comun` 2.3 (`rediseno.md` §8, L1–L10): tres vistas
(Carpeta de trabajo, Recientes, Historial) sobre un documento actual; la tabla de los `.tex` de la carpeta con su estado
leído del disco; F5 compila, Mayús+F5 simula, Ctrl+B con Biber y Limpiar auxiliares… muestra la lista exacta y confirma
(R3); solo LuaLaTeX en la ventana (regla 6; pdfLaTeX y XeLaTeX quedan a la CLI para el material heredado que los
declare); el registro de cada corrida (`--log`) se guarda por documento en la caché y de él salen Problemas, Registro y
el estado; el studio corre con `/usr/bin/python3` y la CLI y su contrato con `docencia` no cambian. Lo que el marco
necesitó (`ListaDiagnosticos`; `Tareas.proceso(progreso_de=)`) subió a `gui-comun` 2.3.0.

### §1.8 Reingeniería: entorno de escritura científica sobre proyectos detectados (2026-11-02)

Encargo del autor del 2026-11-02 (la ventana debe reconocerse como un entorno de escritura científica, no como una
lista de archivos) y decisiones del director de la reingeniería. Diagnóstico, referencias (TeXstudio, TeXmaker, VS Code
con LaTeX Workshop, Overleaf) y las decisiones R1–R16 en `reingenieria.md`; lo esencial: un proyecto es un documento
principal con lo que incluye (R1), detectado en carpetas de trabajo configurables (por omisión `WRITING_DIR` y
`DESPACHO_DIR` de `core/env.py`; la lista del usuario va a sus ajustes, nunca al repo, R2); cada proyecto se compila
con su compilador (el `<marco>/scripts/build.sh` de su marco, latexmk si tiene `latexmkrc`, o `main.sh`) y con el motor que
declare o LuaLaTeX + Biber (R4, R5); editor integrado, PDF integrado con `pdftoppm` y SyncTeX (QtPdf no está
instalado, R10) y errores con causa y acción (R9). Supera §1.7 en la distribución; la ventana 2.0 queda en
`rediseno.md` y en `docs/figuras/antes/`. §1.2 sigue en pie: la ventana compila un proyecto de un marco **con el build
del marco**, nunca con `main.sh`. §1.4 vale para la CLI: la ventana usa latexmk solo para el proyecto que lo pide con
su `latexmkrc`.

### §1.9 La CLI gana `-k` (`--conservar`) y lee `CORE_DIR` (2026-11-02)

`-k` no borra los auxiliares al terminar bien: SyncTeX necesita el `.synctex.gz`, el autocompletado de `\ref` lee el
`.aux` y las pasadas siguientes van más rápido. Sin `-k` todo sigue igual (contrato con `docencia`). El logger busca
`core/` subiendo carpetas como siempre y, si no lo encuentra (un worktree fuera de `~/Documents`, una copia de
pruebas), usa `CORE_DIR` de `core/env.sh` si está exportada.

### §1.13 El editor, la barra de búsqueda y la lista de problemas son los de `gui-comun` 3.1 (2026-11-03)

Lo que este studio construyó y Quarto copió subió a la base con nombre nuevo: `EditorTexto` (antes `EditorArchivo`),
`BarraBuscarReemplazar` (`BarraBusqueda`), `ListaErrores` (`ListaProblemas`) y `gui_comun.editor.ControladorEditor`
(el controlador propio del editor); las copias se retiraron, con la del resaltado. Lo propio de LaTeX se le da al editor
de la base como ganchos: el autocompletado (`EspacioEscritura.completarLatex` y `disparaLatex`, que calcula Python como
antes; las órdenes con argumentos dan `insertar` + `cierre` en vez de `retroceso`), Ctrl+clic para SyncTeX (`ctrlClic`)
y la letra y el ajuste de línea de los ajustes del studio. La lista de problemas lleva en su `cabecera` los filtros por
nivel y «Revisar dependencias»; su rol de ubicación es `ubicacion`. El visor PDF sigue propio hasta que la base tenga la
selección, los enlaces y la búsqueda (§1.11).

**Y el visor, con la 3.2** (el mismo día): la selección, los enlaces y la búsqueda de §1.11 subieron a la base
(`VistaPdf` con `CapaQtPdf` y `BusquedaQtPdf`, `gui_comun.visor_pdf.VisorPdf`). `studio/latex_app/controladores/visor.py` hereda de
`VisorPdf` y añade solo SyncTeX (`abrir` con la carpeta del `.synctex.gz`, `haySynctex`, `desdeCodigo`, que marca con
`marcarRecuadro`, y `haciaCodigo`); `VistaPdf` lleva el doble clic y «Ir al código de este punto» a `haciaCodigo`. Se
retiraron `VisorPdf.qml`, `CapaQtPdf.qml`, `BusquedaQtPdf.qml`, `DocumentoQtPdf.qml`, `PaginaQtPdf.qml` y el renderizado
de `studio/latex_app/visor.py` (que queda solo con SyncTeX); `tests/test_visor_qtpdf.py` ejercita las piezas de la base. La
3.2 arregla además el cursor de `EditorTexto` (`\frac{|}{}`, lo vigila `test_autocompletado_en_el_editor_de_la_base`).
Una trampa de PySide: una propiedad de la subclase con la señal de la base como `notify` tumba QML al crear el
metaobjeto (fallo de segmentación); `haySynctex` tiene su señal propia.

### §1.14 Configurar el documento por el esquema de su marco (2026-11-08)

El autor pidió controlar desde la ventana todo lo configurable de sus documentos (metadatos, elementos visibles,
opciones), en docencia, escritura, los documentos legislativos y los demás marcos. Se decidió que **cada marco declara
lo suyo en `latex-studio.yml`** y la ventana lo pinta de forma genérica (`docs/configuracion-de-documentos.md`): así lo
configurable vive una sola vez, junto a las clases que lo implementan, y un marco nuevo no exige tocar la ventana.
Descartado: campos fijos por marco dentro de LaTeX Studio (acoplaría la ventana a cada clase y se desfasaría). La
escritura es la única excepción a «nunca se escriben fuentes» fuera de Ctrl+S: solo el preámbulo, con la diferencia a
la vista y confirmación, y nunca sobre un archivo con cambios sin guardar en el editor.

### §1.15 Complementaria de TeXstudio; editor sin ortografía por omisión; visor sobremuestreado (2026-11-08)

El autor quiere usar TeXstudio y LaTeX Studio a la vez: editar en uno y compilar o ver en el otro. Se decidió abrir en
TeXstudio desde la ventana (archivo y línea; el principal como maestro) y vigilar el proyecto abierto entero, no solo
lo abierto en el editor: lo guardado fuera se recarga, el PDF compilado fuera se muestra y, si se pide, se compila. La
revisión ortográfica que KDE enciende sola en los campos de texto queda apagada (marcaba en rojo el LaTeX en el idioma
de Sonnet) y el visor dibuja al doble de resolución (Pdfium a 1× empastaba el texto frente a Poppler).

**Una receta, dos programas (2026-11-08).** TeXstudio no podía compilar los documentos de un marco: su «Compilar» es
un motor a secas, sin las clases del marco ni Biber. Se decidió que la receta siga existiendo una sola vez
(`compilador.receta`) y que TeXstudio la llame por un puente sin Qt, `studio/compilar.py`; LaTeX Studio ofrece
escribir esa orden en la configuración de TeXstudio. Descartado: copiar la receta en un guion de TeXstudio (se
desfasaría) o escribir su configuración con QSettings (perdería los valores de tipos propios de TeXstudio, que Qt no
sabe leer): se edita el `.ini` como texto, solo cuatro claves, con TeXstudio cerrado (al salir lo reescribe), respaldo
al lado y «Deshacer». Es configuración de otro programa, no una fuente: la escribe solo el autor, al confirmar. El
SyncTeX inverso puede llevar a TeXstudio (ajuste), y el marco de docencia pasa `-synctex=1` desde este día.

**Versiones de un mismo `.tex` (2026-11-08).** Un `.tex` de `academic-exam` produce tres PDF (`--modo` de su
`build.sh`), pero F5, aquí y en TeXstudio, solo producía el examen en blanco. Se decidió que el marco declare sus
versiones en `latex-studio.yml` (cómo se piden, cómo se llama cada salida) y que el documento declare la suya con un
comentario mágico que su compilador lee: la ventana sigue sin saber nada de docencia y cualquier editor compila la que
pide el documento. Elegir otra en la ventana no escribe (como compilar); fijarla escribe por «Configurar», con la
diferencia a la vista, junto con la línea `TXS-program:view` que hace que el visor de TeXstudio abra ese PDF.
Descartado: órdenes de usuario de TeXstudio por versión (serían de un marco en la configuración global de TeXstudio).

**Okular, el visor por omisión (2026-11-08).** El visor integrado no siempre seguía a la compilación (con versiones, el
documento declaraba el solucionario y la ventana miraba el examen) y el autor lo veía menos nítido que un visor de
escritorio. Se decidió que, con Okular instalado, el PDF se vea en Okular: recarga solo, SyncTeX en los dos sentidos
(`#src:` hacia el PDF; su editor externo `main.py --ir %f %l` de vuelta, a la ventana abierta por un socket local) y
todo lo de Okular (búsqueda, anotaciones, presentación). El integrado queda en F7 y en Ajustes. Descartado: incrustar
Okular (KParts es C++/Widgets; la ventana es QML). Los avisos sin decisión pasan a las notificaciones de KDE (gui-comun
4.1), que no ocupan la ventana.

**Superada en parte (2026-11-10): el PDF a la derecha del código por omisión.** El autor pidió ver el PDF junto al
código y Okular en ventana aparte solo si lo elige. Incrustar Okular sigue descartado (KParts no tiene enlace para
Python ni cabe en una escena QML; reparentar su ventana no funciona en Wayland). Lo que motivó el cambio del 08-11 ya no
vale: el integrado sigue a la versión elegida (`p.job`, desde las versiones del mismo día) y pinta sobremuestreado
(gui-comun 4.1). El ajuste pasa a una clave nueva (`visor/okular_ventana`, falso por omisión) para que quien nunca lo
tocó vea el cambio; «Ver el PDF en Okular» (Ctrl+Alt+O) sigue abriéndolo allí a mano. Además, sin archivo en la orden,
la ventana arranca en la página de proyectos: el último abierto ya no se reabre solo, queda marcado en la tabla.

**Inclusiones con macros y órdenes propias (2026-11-10).** El CV incluye su cuerpo con `\input{profiles/\CVprofile}`
y sus anexos con `\inputAnexos{…}`, una orden suya que envuelve un `\input`: el detector veía 2 de sus 36 archivos. Ahora
el análisis guarda las macros simples (la primera definición, que es la de omisión en `\ifdefined\X\else\def\X{…}\fi`),
las órdenes cuyo cuerpo hace `\input{#1}` y las llamadas con una ruta por argumento; una macro en una ruta da primero su
valor y después todas las variantes que existen (`profiles/*.tex`), porque es un parámetro y cada variante es un archivo
del proyecto (caché versión 6).

## 2. Motor

### §1.16 Los datos del proyecto los declara su marco: la pestaña «Datos» (2026-11-17)

La vista Escritura suma una pestaña «Datos» junto a Archivos, Estructura y Bibliografía: las figuras, tablas y cifras
que el proyecto puede citar, con la orden LaTeX que las inserta (doble clic, en el cursor, como `\cite` desde la
bibliografía), si su paquete tiene una versión más nueva y un botón para traerla, y otro para abrir el programa que las
produce. La ventana no sabe qué es un paquete: corre las tres órdenes de la sección `datos:` del `latex-studio.yml` del
marco (`recursos` devuelve JSON, `actualizar`, `productor.orden`; contrato §8 de `configuracion-de-documentos.md`), en
un hilo y con `{proyecto}` = la carpeta más cercana con el `marcador` del marco. Escritura la declara para sus informes
(los paquetes de datafw; abre Datafw Studio); un marco sin `datos:` deja la pestaña vacía con su explicación. «Actualizar»
escribe en el proyecto (figuras, tablas, cifras, su ficha), nunca en el texto, y se confirma. Se descartó leer los
paquetes desde aquí: el repo es público y autónomo, y docencia o el CV no deben cargar nada de datafw. Las cuatro
pestañas van a lo ancho de la barra (con su ancho natural se desplazaba y «Archivos» quedaba fuera de la vista).
Pruebas: `tests/test_datos.py`, sobre el marco de muestra (`studio/ejemplo/proyectos/marco`, su `datos.yml` y
`studio/ejemplo/proyectos/marco/scripts/datos_muestra.py`).

### §1.18 La biblioteca del marco en la pestaña «Citas» (2026-11-17)

«Citas» deja de ser solo las entradas de los `.bib`: si el marco declara su biblioteca (sección `biblioteca:` del
`latex-studio.yml`, contrato §9), tres chips cambian entre «Del proyecto», la biblioteca entera (con portada, autor,
año y clave; doble clic cita, y si el libro aún no es fuente del proyecto, el marco lo añade a sus fuentes y a su `.bib`
tras confirmar) y las fichas del proyecto (tipo, clave y página, el texto; doble clic inserta la cita textual con su
página). La ventana no sabe qué es Calibre ni Zotero: corre las órdenes que el marco declara, en hilos, y citar va en
dos tiempos (primero sin aplicar). Escritura la sirve con `biblioteca-studio/lib/consulta.py`. Pruebas: la biblioteca
de muestra del marco de ejemplo en `tests/test_datos.py`.

### §1.19 Fichar y la ayuda de la IA, como en Yachay (2026-11-17)

Dos capacidades de Yachay llegan a la vista Escritura, siempre por lo que el marco declara (la ventana no sabe nada de
la norma de fichas, de Calibre, de Zotero ni de qué prompt sirve a qué parte):

- **Fichar** (contrato §9 ampliado: `formulario`, `ficha`, `nueva_ficha`, `guardar_ficha`). En Citas › Fichas, el chip
  «Nueva ficha» (y «Fichar este libro…» en el menú de un libro de la biblioteca) abre un formulario que describe el marco:
  los tipos (textual, paráfrasis, síntesis, fuente), sus secciones, si llevan página y categoría, y los rótulos. Clic
  derecho en una ficha, «Editar la ficha…»: se lee con su **huella** y se guarda con ella; si cambió fuera desde que se abrió
  (en Yachay, en Biblioteca Studio, a mano), la orden responde `ficha_cambiada` y el diálogo la recarga sin pisarla.
  Guardar va en dos tiempos, como citar: «Revisar» simula (el nombre del archivo, el cotejo contra el PDF, lo que la norma
  objeta, si el libro se suma a las fuentes) y «Guardar la ficha» escribe lo revisado con `--aplicar`: esa es la
  confirmación (regla de las fuentes: solo lo que el marco declara y se confirma). El texto del documento no se toca.
- **La ayuda de la IA de la parte abierta** (contrato §10, nuevo: `ayuda:` con `prompt` y `pegar`; Herramientas, Ctrl+Alt+I; Ctrl+Alt+A desde §1.26).
  «Copiar el prompt» pone en el portapapeles el que el marco arma para la parte (escritura: el prompt del ecosistema que
  le toca a su `\componente`, traducido para un chat externo, con su entrada rellena). La respuesta del chat se pega en el
  diálogo y «Comprobar lo pegado» la pasa a la orden `pegar` junto con el texto del editor (dos archivos en la caché):
  vuelve el cambio sugerido (o lo que no va: una sección, una clave que el escrito no tiene) y «Poner en el editor»
  reemplaza el tramo en el editor, seleccionado y con Ctrl+Z para deshacer. **La ventana no llama a ningún modelo ni
  escribe el archivo**: el autor lo revisa y guarda con Ctrl+S.

Escritura las sirve con `biblioteca-studio/lib/consulta.py` (decisiones §9.4 y §9.5 de biblioteca-studio). La muestra
(`studio/ejemplo/proyectos/marco/scripts/datos_muestra.py`) declara las seis órdenes sin datos reales; pruebas en
`tests/test_datos.py`, capturas en `docs/figuras/latex-studio-ficha.png` y `latex-studio-ayuda-ia.png`
(`studio/capturar.py --ficha`, `--ayuda-ia`).

### §1.20 «Nuevo documento»: crear lo que el marco sabe crear, sin la terminal (2026-11-18)

El autor pidió crear un informe, una tesis, una monografía, un artículo, un ensayo o un libro con botones y formularios,
sin `proyecto/main.py nuevo` en la terminal. Como en §1.16 y §1.18, **la ventana no sabe nada de ningún marco**: el marco
declara la sección `nuevo:` de su `latex-studio.yml` (contrato §11) con dos órdenes, `tipos` (los tipos, su línea, sus
variantes o esquemas y los campos del formulario, con rótulo, si es obligatorio y sus opciones) y `crear` (recibe el
formulario en JSON). La sección se busca en cada carpeta de trabajo y en los marcos de los proyectos detectados
(`datos.declaraciones_nuevo`); con varios marcos que la declaran, se elige el marco primero.

Crear va en dos tiempos, como citar y fichar: **«Revisar»** corre `crear` sin `--aplicar` y el marco crea el documento en
un temporal (escritura: `--raiz-proyectos`) y devuelve la carpeta real de destino, los archivos y el principal, sin tocar
la carpeta real; **«Crear y abrir»**, la única acción rellena del diálogo, corre lo revisado con `--aplicar` y abre el
principal en el editor. Cualquier cambio del formulario invalida lo revisado. Las opciones van en lista (las variantes,
con su descripción en la misma línea) y los tipos en tarjetas con su línea, sin nubes de pastillas. Se abre con el botón
«Nuevo documento» de la página de proyectos, Ctrl+N (Archivo › Nuevo documento…) y la paleta; si no hay proyectos, el
mensaje vacío lo ofrece.

Escritura lo sirve con `escritura/scripts/nuevo_documento.py`, un guion delgado sobre `proyecto/main.py nuevo` (el slug
sale del título con `slug_de_titulo` de `escritura/proyecto/lib/crear.py`). Antes se corrigió en escritura el fallo que lo hacía peligroso:
`nuevo informe` no reenviaba `--raiz-proyectos` (ni el subtítulo, el autor ni la profundidad) a `reporting/main.py
nuevo`, y un informe «de prueba» nacía en la carpeta real. La muestra (`studio/ejemplo/proyectos/marco/scripts/nuevo_muestra.py`)
declara tres tipos sin datos reales. Pruebas: `tests/test_datos.py` (declarar, simular sin escribir, crear) y
`tests/test_controladores.py` (el controlador con el marco detectado); captura con `studio/capturar.py --nuevo memoria`.

### §1.21 «Antes de entregar»: los controles de la cadena de evidencia, declarados por el marco (2026-11-18)

La fase 1 de la investigación del flujo de conocimiento («cerrar la cadena de evidencia», su §7) pide cuatro controles al
final de un documento académico o técnico, que no dependan de la memoria (Haynes et al., 2009): cifras vivas (Gentzkow y
Shapiro, 2014; Christensen y Miguel, 2018), la lista de control del tipo (Appelbaum et al., 2018; von Elm et al., 2007),
referencias verificables y citas textuales cotejadas (ICMJE, 2025; Jergas y Baethge, 2015; Roig, 2015) y el uso de la IA
registrado y declarado (COPE, 2023; Comisión Europea, 2025). Como en §1.16 a §1.20, **la ventana no sabe qué es ninguno**:
el marco declara la sección `entrega:` (contrato §12) con tres órdenes, `revisar`, `marcar` y `registrar_ia`, y la
ventana pinta lo que devuelven.

- **El diálogo** (Herramientas › «Antes de entregar…», Ctrl+Alt+E y la paleta; `studio/latex_app/qml/componentes/DialogoEntrega.qml`,
  `studio/latex_app/controladores/entrega.py`). Arriba, el veredicto: «Listo para entregar» o «Faltan N». Debajo, un grupo por control,
  cada uno con su punto de color (rojo falla, ámbar aviso, verde bien, hueco lo manual sin marcar), su nombre, su detalle,
  una línea tenue con el porqué y la fuente, y sus hallazgos (los cinco primeros y «Ver los N»): un clic cierra el diálogo
  y abre el archivo en esa línea. La única acción rellena es «Revisar de nuevo»; nada de pastillas.
- **Ninguna lista bloquea por su cuenta**: el veredicto lo calcula la ventana (`datos.veredicto`): listo si no hay fallas y
  todo lo manual está marcado o justificado. Los avisos se leen y no bloquean: un número de redacción escrito a mano o una
  obra que aún no está en la biblioteca no deben impedir entregar, pero se ven.
- **Lo manual**, con casilla y nota: la casilla lo da por hecho; sin casilla y con nota, queda justificado («no aplica»).
  Se escribe al tocar la casilla o al terminar la nota (`marcar --aplicar`): el clic es la confirmación, como en una lista
  de control en papel, y el diálogo revisa de nuevo. El estado vive en el proyecto (escritura: `<proyecto>/registro/entrega.yml`, con
  fecha), no en la ventana.
- **El registro de la IA**: «Poner en el editor» de la ayuda de la IA (§1.19) llama a `registrar_ia --aplicar` con la
  fecha, el archivo, la parte, el prompt (título, ruta, versión y su texto, del que el marco guarda solo la huella) y un
  resumen del cambio («reemplazó 3 líneas de texto por 4»). Es lo único que la ventana escribe sin un segundo paso: el
  autor ya aceptó el cambio, y un registro que pidiera confirmación aparte se saltaría. Deshacer el cambio con Ctrl+Z no
  borra el uso: se declara de más, nunca de menos. El texto del documento sigue escribiéndose solo con Ctrl+S.

Escritura lo sirve con `escritura/scripts/antes_de_entregar.py` (un módulo por control en `escritura/scripts/entrega/`, las listas en
`escritura/config/entrega/listas/`; `escritura/docs/verificacion.md` §9). La muestra (`studio/ejemplo/proyectos/marco/scripts/entrega_muestra.py`)
declara las tres órdenes con comprobaciones de juguete y sin datos reales. Pruebas: `tests/test_datos.py` (declarar,
revisar, marcar y registrar, simulando y aplicando; el veredicto y lo mal formado) y `tests/test_controladores.py` (el
controlador en sus hilos); captura con `studio/capturar.py --entrega` en `docs/figuras/latex-studio-antes-de-entregar.png`.

### §1.25 El PDF etiquetado se activa desde «Configurar el documento»: el destino `metadatos_documento` (2026-11-18)

La mejora C13.1 (LaTeX Project, 2025; ISO, 2014) pide el PDF etiquetado y accesible con `\DocumentMetadata`, que tiene
que ir **antes** de `\documentclass`: ninguno de los destinos que la ventana sabía escribir (opción de clase, orden en el
preámbulo, clave de una lista) llega ahí. El destino nuevo `{metadatos_documento: <clave>}` edita una clave dentro de
`\DocumentMetadata{…}` en el principal (nunca en `metadata.tex`: ahí ya sería tarde), con las mismas reglas que una
lista: la omisión la quita, una orden sin claves se quita, y sin orden se inserta justo antes de `\documentclass`. Así
el etiquetado es opcional por documento y quitarlo deja el texto como estaba (la prueba lo comprueba byte a byte). El
marco decide qué claves expone (escritura: `tagging`, `lang`, `pdfstandard`, `pdfversion`) y «Antes de entregar» revisa
el PDF que sale.

### §1.22 La norma del flujo de conocimiento: la matriz, el asistente de pregunta, la autoevaluación, el texto alternativo y el aviso antes de copiar un prompt (2026-11-18)

El autor aprobó como norma `prompts/00 metodo/FLUJO_DE_CONOCIMIENTO.md` (67 mejoras con su fuente; el fundamento, en
`FLUJO_DE_CONOCIMIENTO_FUNDAMENTO.md` §5) y pidió que los programas la cumplan de manera estricta. A LaTeX Studio le tocan,
con escritura como marco, estas; como en §1.16 a §1.21, **la ventana no sabe qué es ninguna**: corre lo que el marco
declara y pinta lo que devuelve, con la línea tenue «por qué · fuente» que el marco da.

- **La matriz de consistencia viva** (C1.1, C1.3; Hernández Sampieri et al., 2014, Calibre 732; Gerring, 2012; King et
  al., 1994; Popper, 2007, Calibre 617; Alvesson y Sandberg, 2011): una sección nueva del contrato, `matriz:` (§13), y un
  panel, Herramientas › «Matriz de consistencia…» (Ctrl+Alt+M; `DialogoMatriz.qml`, `controladores/matriz.py`). Arriba,
  «Nada huérfano» o cuántos elementos huérfanos; cada fila con su problema, objetivo e hipótesis, debajo la evidencia que la
  refutaría y el supuesto que cuestiona, sus indicadores (por su nombre; la referencia `estudio@vN/indicador` en la ayuda)
  y su sección (un clic va a ella). «Generar el cuadro» lo escribe el marco. Un panel y no una pestaña lateral más: la
  matriz se mira de vez en cuando, y las cuatro pestañas de la barra ya están a un cuarto de ancho.
- **El asistente de pregunta** (C1.2; Booth et al., 2016; Varian, 1997; Mendoza Bellido, 2022, Calibre 578), como ventana
  (`DialogoPregunta.qml`): cuatro pasos (tema, rompecabezas, pregunta delimitada, evidencia), cada uno con su pregunta, su
  ayuda, un ejemplo y su fuente; «Revisar» pide los avisos del marco sin escribir y «Guardar en la matriz» escribe tras
  revisar. Los pasos los da el marco (`guia`), no la ventana.
- **La autoevaluación con la rúbrica** (C11.2; Andrade, 2019; Panadero y Jonsson, 2013): dos órdenes más en `entrega:`
  (`rubrica`, `autoevaluar`), la rúbrica en el formato común del ecosistema (el mismo que usa docencia) y el diálogo
  «Autoevaluación» (`DialogoRubrica.qml`), con un botón desde el control de «Antes de entregar» (la clave `accion` del
  control). Cada criterio se guarda por separado con su justificación: el clic en «Guardar» es la confirmación.
- **El texto alternativo obligatorio al insertar una figura** (C8.3; W3C, 2024, Calibre 10443; LaTeX Project, 2025): si
  el marco da `insertar_alt` en la figura de la pestaña Datos (§8), el doble clic abre `DialogoAlt.qml` con el borrador y
  no inserta sin texto. La ventana escapa lo que LaTeX no admite dentro de `alt={…}`.
- **El aviso antes de copiar un prompt** (C12.3; Comisión Europea, 2025; NIST, 2023, Calibre 10441): `revisar_prompt` en
  `ayuda:` (§10). Avisa y deja decidir («Copiar de todos modos»), porque quien sabe si el dato puede salir es el autor; si
  la revisión falla, también pregunta: copiar a ciegas sería peor que preguntar de más.

- **El lector frío** (C11.4; COPE Council, 2017): `lector_frio` en `entrega:` y «Versión para lector frío» en el pie de
  «Antes de entregar»: el marco copia el proyecto fuera del documento, quita la autoría y compila; la ventana abre el PDF.
  Los comentarios del revisor vuelven por el marco como un control con sus hallazgos (un clic, a la línea): cambios
  sugeridos que el autor atiende, nunca aplicados solos.

Pruebas: `tests/test_datos.py` (cada sección sobre la muestra, simulando y aplicando) y `tests/test_controladores.py` (los
controladores en sus hilos). Capturas con `studio/capturar.py` (`--matriz`, `--pregunta 3`, `--rubrica`, `--alt`) en
`docs/figuras/`.

### §1.23 El revisor del editor: estilo y LaTeX con reglas citadas, que sugiere y no reescribe (2026-11-18)

Las mejoras C6.1 (Williams y Bizup, 2017; McCloskey, 2019; Gopen y Swan, 1990), C6.2 (PLAIN, 2011, Calibre 10510;
McCloskey, 2019) y C13.2 (Trettin, 2016; Fear, 2020; Wright, 2024) piden revisar el texto mientras se escribe y no solo al
final. Una sección nueva, `revisor:` (contrato §14), y una pestaña del panel inferior, «Revisión» (`RevisionEditor.qml`,
`controladores/revisor.py`), que se pone al día al guardar y con Ctrl+Alt+R sobre lo que está en el editor (aún sin
guardar). Una pestaña del panel inferior y no subrayados en el editor: el editor común de `gui-comun` no tiene capas de
marcas, y una lista con «por qué · fuente» enseña la regla, que es lo que pide la mejora. **Nada del panel cambia el
texto**: la norma pide un revisor que sugiere y nunca reescribe solo. El perfil de lector lo decide el marco (escritura lo
lee del `proyecto.yaml`).

### §1.24 Las plantillas que ahorran tiempo (2026-11-18)

La mejora C13.4 (Knauff y Nejasmic, 2014: Word fue más rápido que LaTeX en varias tareas, salvo en ecuaciones) obliga a
que LaTeX Studio reduzca el costo de LaTeX en lo que más se repite. Una sección nueva, `plantillas:` (contrato §15), y
Herramientas › «Insertar una plantilla…» (Ctrl+Alt+T; `DialogoPlantillas.qml`, `controladores/plantillas.py`): la lista a
la izquierda, el formulario corto y lo compuesto a la derecha, «Insertar» en el cursor. Las plantillas las da el marco;
la barra de insertar (§1.17) sigue para lo genérico (sección, figura suelta, tabla, cita, ecuación).

### §1.26 Los huecos de la comprobación de la guía del flujo (2026-11-18)

Cinco huecos de `prompts/00 metodo/GUIA_FLUJO_DE_CONOCIMIENTO.md` §9, cerrados sin que la ventana aprenda nada de un marco.
**«Nuevo documento»** ofrece la nota de política, el informe NISO y «Láminas» (las de un proyecto que no las tiene; lo
resuelve escritura; la ventana solo aprendió que una opción obligatoria con `omision` ya está llena). **La autoevaluación** tiene su
entrada, Herramientas › «Autoevaluación con la rúbrica…» (sin atajo), si el marco declara `rubrica` y `autoevaluar`.
**«Ajustes de composición»** llega a los informes (norma de cita y PDF accesible, compilados); la lámina no los admite:
beamer detiene la compilación ante `\DocumentMetadata` y su biblatex fija APA. **Las listas** de la nota de política y del
informe NISO son del marco. **Ctrl+Alt+I era de dos acciones** (la paleta de `gui-comun`, convención de KDE, y la ayuda
de la IA): un atajo repetido no ejecuta ninguna. Cede la ventana, no el marco común: la ayuda pasa a **Ctrl+Alt+A** y
`tests/test_studio.py` exige `Acciones.conflictos()` vacío.

### §1.17 Rediseño: una mesa de escritura al estilo de Datafw Studio (2026-11-17)

El autor pidió que LaTeX Studio dejara de sentirse «un editor más» y fuera, como Datafw Studio, interactivo, fácil e
igual de completo. Se aprobó una maqueta y se rehizo la piel, no la mecánica: la ventana sigue sobre `VentanaStudio`,
con sus menús, su paleta, sus paneles y sus pruebas, y la barra de herramientas larga se cambió por una **barra ligera**
(en Proyectos, «Tus documentos»; en Escritura, el documento, el estado de su última compilación en una línea y tres
acciones: Compilar o Detener, Configurar y el programa de sus datos si el marco lo declara; ⋮ abre todas las órdenes).
**Proyectos** son tarjetas con la **miniatura de la primera página** (`pdftoppm` en un hilo, a la caché, con nombre
por ruta y fecha del PDF y escrita entera antes de que QML la lea: `studio/latex_app/miniaturas.py`), su tipo, «hace 2 h»
(`compilador.hace`) y un punto con su estado; «Lista» vuelve a la tabla de columnas y la ficha deja lo técnico (motor,
compilador, la orden exacta) bajo «Detalles técnicos». **Escritura** suma la **barra de insertar**: sección, figura,
tabla (una rejilla celda por celda, booktabs), cita (las entradas de los `.bib`, por `proyectos.completar`), ecuación,
referencia (las `\label` del proyecto), lista, y negrita, énfasis y nota al pie sobre lo elegido; cada diálogo muestra
el LaTeX antes de escribirlo y solo escribe en el cursor (`DialogoInsertar.qml`). Debajo del editor, la **franja del
primer problema** con su causa, su arreglo, «Ir a la línea», «Siguiente» y «Ver todos», y en el pie las palabras del
archivo (sin órdenes ni comentarios). La barra lateral pierde la cabecera del proyecto (está arriba) y sus pestañas se
llaman Archivos, Esquema, Citas y Datos; las figuras de Datos llevan su miniatura. El `Chip` es el de Datafw Studio,
para que los dos studios se lean como familia. Sin colores propios, sin marca dentro de la ventana y sin QtWidgets,
como antes. Pruebas: `tests/test_rediseno.py` y las tarjetas en `tests/test_controladores.py`.

### §1.10 El visor pinta con QtPdf cuando está; `pdftoppm` queda de respaldo (2026-11-03)

El autor instaló `qml6-module-qtquick-pdf` y `python3-pyside6.qtpdf`. Cada página la pinta ahora Qt con `PdfPageImage`
(`PaginaQtPdf.qml`, sobre un `PdfDocument` en `DocumentoQtPdf.qml`; desde §1.13, los de `gui-comun` 3.2), dentro del mismo recuadro de
`VisorPdf`: así se conservan el tamaño en puntos de cada página, el zoom, las miniaturas, la marca de SyncTeX (código →
PDF) y el doble clic (PDF → código), que `PdfMultiPageView` no deja poner con su vista propia. Los dos componentes viven
aparte para que `VisorPdf` no importe `QtQuick.Pdf`: sin el módulo, o con `LATEX_STUDIO_VISOR=pdftoppm`, el visor sigue
con `pdftoppm` (§1.8, R10). Dos trampas, anotadas en el componente: asignar `document` devuelve `currentFrame` a 0 y
rompe el enlace con la página (todas salían como la primera; se fija a mano y lo vigila una prueba), y QtPdf pinta la
página sin fondo (el papel blanco va debajo, como lo da un PDF impreso). La selección de texto, los enlaces y la
búsqueda llegaron el 2026-11-03 (§1.11).

### §1.11 Seleccionar, seguir enlaces y buscar en el PDF, sin perder SyncTeX (2026-11-03)

Con QtPdf, cada página lleva encima una capa (`CapaQtPdf.qml`; desde §1.13, la de `gui-comun` 3.2) con `PdfSelection`,
`PdfLinkModel` y los resultados de un `PdfSearchModel` (`BusquedaQtPdf.qml`, uno para todo el documento); las dos viven
aparte, como las de §1.10, y sin el módulo el visor sigue igual que antes. Arrastrar con el ratón selecciona (el patrón
de `PdfMultiPageView`: un `DragHandler` sin destino; la lista de páginas no se desplaza con él, lo vigila una prueba);
Ctrl+C copia, Ctrl+A toma la página, Esc suelta; clic derecho, un menú (copiar, toda la página, ir al código, buscar).
Un clic suelto borra la selección y **el doble clic sigue siendo de SyncTeX** (la capa no lo toma). Los enlaces internos
van a su página y su punto; los externos pasan por `Visor.abrirEnlace`, que **solo abre `http`, `https` y `mailto`**
(un PDF puede llevar enlaces a `file:` o a órdenes). La búsqueda (Ctrl+Alt+F o el botón de la barra; Ctrl+F sigue
siendo del editor) resalta todos los resultados, marca el actual y salta con Intro y Mayús+Intro. Todo en puntos de la
página, escalado con el zoom del visor. Fuera: seleccionar a través de varias páginas (una página por selección, como
`PdfMultiPageView`).

### §1.12 Problemas de Biber desde su `.blg`; autocompletado de argumentos; plegado descartado con `TextArea` (2026-11-03)

- **Biber**: los errores y avisos salen de su `.blg` (`compilador.problemas_de_blg`, `con_blg`) cuando es de esa
  corrida, en lugar de las líneas que imprime: el compilador del marco calla a Biber, y un error de sintaxis del `.bib`
  llega con el archivo y la línea (Biber 2.19 nombra la copia temporal con un hash: el `.bib` es el último «Found BibTeX
  data source» anterior). Tres explicaciones nuevas: cita sin entrada, error de sintaxis, clave repetida.
- **Autocompletado**: cada orden con argumentos lleva su firma (`\frac{numerador}{denominador}`) y se inserta con sus
  llaves y el cursor en la primera (`estructura.FIRMAS`); los argumentos conocidos se completan: paquetes (los del
  proyecto también), clases, estilos de BibTeX y los archivos del proyecto para `\input`, `\include` (sin extensión),
  `\includegraphics`, `\addbibresource` y `\bibliography` (`estructura.archivos_de`, sin carpetas ocultas ni de
  auxiliares, con tope).
- **Plegado, multicursor y corrector**: el `TextArea` de Qt Quick no respeta los bloques invisibles de `QTextDocument`
  (probado: la altura del contenido no cambia al ocultar líneas), no tiene varios cursores y admite un solo
  `QSyntaxHighlighter` por documento (el de KSyntaxHighlighting; el de Sonnet lo sustituiría). Las tres cosas piden otro
  editor: `KTextEditor` es QtWidgets (fuera de la familia, regla de `gui-comun`) y un editor propio sobre `QQuickPaintedItem`
  es un proyecto en sí. **Recomendación al autor**: dejarlas fuera mientras el editor sea un `TextArea`; si se echan de
  menos, «Abrir en el editor externo» (Kate) las da para ese archivo.

### §2.1 LuaLaTeX + Biber es el motor normativo (2026-09-20)

Regla 7 del `CLAUDE.md` raíz. Ningún ejemplo ni valor nuevo se escribe para pdflatex o xelatex, que
se conservan para material heredado que los declare.

### §2.2 `DEFAULT_ENGINE` en `auto`, y `auto` cae en `pdflatex` (2026-09-20)

Superada por §2.3 (2026-10-03).

### §2.3 `auto` es lualatex, salvo el comentario mágico (2026-10-03)

La heurística por paquetes contradecía la regla 7 y no veía `\usepackage[…]{fontspec}`. `auto` lee
`% !TEX program = …` en las 5 primeras líneas (la convención de `docencia/scripts/lib/common.sh`)
y, sin él, elige lualatex. El andamio de los decks de `docencia` ya declara `lualatex`.

## 3. Robustez del ciclo de compilación (2026-10-03)

### §3.1 El estado del motor se lee con `set +e` y `PIPESTATUS`

Justo después del pipeline, en los tres modos: un error sale con 1 y con el extracto del `.log` del
motor. Antes, `|| true` y `set -e` hacían que un fallo con un PDF anterior se anunciara como éxito.

### §3.2 Un fallo devuelve 1, no hace `exit`

`compilar` se detiene en la primera pasada que falla y el modo watch sigue vigilando;
`mostrar_info_pdf` rechaza un PDF anterior a la compilación o vacío.

### §3.3 La salida de la corrida va a `SALIDA_LOG`

El `--log` o un temporal; nunca `LOG_FILE`, que es del logger de `core/`, ni el `.log` del motor,
que este reescribe en cada pasada.

### §3.4 La limpieza borra solo los auxiliares del documento

Y los `.aux` que su `.aux` declara con `\@input`; ningún otro de la carpeta. `--draft` dice que no
hay PDF y borra el de 0 bytes que deja lualatex.

### §3.5 `--dry-run` simula sin escribir (2026-10-05)

`-n`/`--dry-run` imprime las órdenes que ejecutaría (o, con `-c`, los auxiliares que borraría) y
sale antes de crear el temporal, sin llamar al motor. Es el `--dry-run` real que exige RQ-COD-02;
`simula_por_defecto` sigue en `false` porque compilar es lo que se le pide a la herramienta. Lo
prueba `script_compilar_latex/tests/dry-run.sh`.

## 4. Código y relación con `core/`

### §4.1 El logger es el de `core/shell-lib/logger.sh` (2026-09-07)

El `logger.sh` de la suite es un envoltorio que solo añade sus nombres cortos.

### §4.2 Manifiesto `suite.yml` (2026-09-15)

Según `core/suite.schema.yml`; los bloques de los README los genera `core/suites.py`.

### §4.3 `set -euo pipefail` en `main.sh` (2026-06-22)

Con los códigos de salida capturados en línea aparte de `local` y `set +e` local donde hace falta
leer un estado (§3.1). Los módulos de `lib/` se cargan con `source` y heredan la opción. La bitácora
de la reescritura modular quedó en git: `git show 2a833c3:docs/historial/bugs-corregidos.md`.

### §4.4 Nombres en español (2026-10-03)

El manual anterior pedía nombres en inglés técnico; el código nunca lo siguió y el ecosistema
escribe en español.

## 5. Documentación

### §5.1 Un lector por documento (2026-10-03)

El manual de `script_compilar_latex/` es para quien usa; `arquitectura.md`, para quien amplía; el
README, la puerta. El contrato con `docencia` vive solo en `arquitectura.md` §Consumidores.

### §5.2 `docs/` se conserva con un README corto: apartamiento de la matriz (2026-10-05)

La normativa documental (2.3, fila 13) prohíbe `docs/` en una suite cuyo README tiene menos de 200
líneas, pero recomienda `docs/decisiones.md` (D) y pide la sección «Consumidores» (N) en el documento
dueño del contrato. Se conservan `decisiones.md` y `arquitectura.md` (dueño de §Consumidores) y se
retiran la carpeta de historial de `docs/` (prohibida, 5.3: git la conserva) y su índice
(obligatorio solo desde cinco documentos, 3.5). Apartamiento asentado según 0.5 y 2.5.
