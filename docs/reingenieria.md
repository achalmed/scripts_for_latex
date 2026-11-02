---
tipo: doc
estado: activo
forma: explicacion
titulo: "Reingeniería de LaTeX Studio (2026-11-02): de una lista de documentos a un entorno de escritura científica"
creado: 2026-11-02
---
# Reingeniería de LaTeX Studio: diagnóstico, distribución y decisiones

Encargo del autor del 2026-11-02 (§3.5 de la instrucción maestra de la reingeniería de los diez studios, con §4–§6):
LaTeX Studio deja de ser «la tabla de los `.tex` de una carpeta» y pasa a ser el entorno predeterminado para escribir,
compilar y revisar los proyectos LaTeX del autor, con la arquitectura de su disciplina. Este documento es el diagnóstico
de la ventana 2.0 (la de la fase 5, `docs/rediseno.md`), la justificación de la nueva distribución y las decisiones R1–R16
que la siguen. Lo construido y lo que quedó fuera está en §6 y en `estado.md`.

## 1. Diagnóstico de la ventana 2.0 (leído en el código, `respaldo/antes-reingenieria-2026-11-02`)

Capturas de antes: `docs/figuras/antes/latex-studio-{oscuro,claro,paleta}.png`.

### 1.1 Qué hace cada función hoy

| función | dónde | qué hace de verdad |
|---|---|---|
| Carpeta de trabajo | `controladores/espacio.py` | una sola carpeta (QSettings); la tabla lista sus `.tex` **sin entrar en subcarpetas** (`compilador.documentos_en`) |
| Tabla de documentos | `controladores/documentos.py`, `Main.qml` | una fila por `.tex` con `\documentclass` o sin él: un capítulo `\input` sale como «documento» aparte; estado leído del disco (PDF frente al `.tex`, el `.log`) |
| Recientes, Compilaciones | `historial.py` | listas en QSettings (12 y 60) |
| Compilar (F5), con Biber (Ctrl+B), Simular (Mayús+F5) | `corrida.py`, `compilador.Opciones.orden` | `main.sh` con las opciones **de la sesión** (motor `auto`/`lualatex`, pasadas, bibliografía): las mismas para todos los documentos, no las del proyecto |
| Limpiar auxiliares… | `corrida.limpiar` | `main.sh -c` tras mostrar la lista y confirmar (correcto) |
| Problemas | `compilador.problemas_de_registro` | errores y avisos de la última pasada y de Biber, con archivo y línea (correcto y probado) |
| «Ir a la línea» | `espacio.abrirEnEditor` | lanza **Kate** (u otro editor externo) en la línea: la ventana no edita |
| Abrir el PDF | `espacio.abrir` | `xdg-open`: el PDF **sale de la ventana** a Okular |
| Abrir en Dolphin | `espacio.abrirDolphin` | `xdg-open <carpeta>`: abre la carpeta pero **no señala el archivo** |
| Recompilar al guardar | `documentos._vigilar` | vigila solo el `.tex` principal (no los `\input` ni el `.bib`) |
| Paleta Ctrl+K | `aplicacion.entradas_paleta` | vistas, carpetas recientes, documentos de la carpeta |

### 1.2 Lo incompleto, lo ficticio y lo que no se comporta

- **No hay proyectos**: un `.tex` es una fila. `escritura` tiene 428 `.tex` con `\documentclass` y muchos más
  capítulos; los capítulos (`content/01-ficha.tex`) aparecerían como documentos que no compilan solos.
- **El motor no es el del proyecto**: las opciones de la sesión mandan sobre todos. Un proyecto de `escritura` (clase
  `informe`, `tesis`…) **no compila** con `main.sh`: su clase vive en `escritura/classes/` y solo `escritura/scripts/build.sh`
  pone `TEXINPUTS` y deja los auxiliares en `.build/` (decisión §1.2: «los frameworks compilan con su propio build»).
  La ventana 2.0 compila esos maestros con `main.sh` y el resultado es «File `informe.cls' not found».
- **`latexmkrc`, `% !TEX root`, `% !BIB program`, arara** no se leen; solo `% !TEX program` en las 5 primeras líneas.
- **No edita**: «Ir a la línea» y «Abrir en el editor» delegan en Kate; no hay resaltado, estructura, autocompletado,
  buscar y reemplazar ni navegación entre archivos del proyecto.
- **No hay visor**: el PDF se abre fuera (`xdg-open`), sin SyncTeX; tras compilar con éxito `main.sh` **borra** el
  `.synctex.gz` junto con los auxiliares, así que SyncTeX era imposible aunque hubiera visor.
- **Errores sin explicación**: el mensaje crudo del `.log` («LaTeX Error: File `x.sty' not found»), sin causa probable
  ni acción recomendada (§5.4 de la instrucción).
- **Una sola carpeta, sin subcarpetas**: no hay raíces de trabajo, profundidad ni detección.
- **Datos ficticios**: ninguno; todo lo que se muestra se lee del disco o del historial. **Botones sin
  comportamiento**: ninguno; «Configurar atajos» y «Configurar barras» no existen (no se ofrecen).
- **Sin cola**: no se compilan varios proyectos seguidos; no hay reconstrucción completa ni revisión de dependencias.

### 1.3 Problemas de KDE

- El selector de archivos y de carpetas es el `FileDialog`/`FolderDialog` de QtQuick con una `QGuiApplication`
  (`gui_comun.nucleo` 2.x): sin el tema de plataforma de KDE se ve el diálogo «extraño» de Qt Quick que vio el autor.
  Lo corrige la base (`gui-comun` 3.0, `QApplication`); aquí basta usar esos mismos diálogos (§4, R14).
- «Abrir en Dolphin» no señala el archivo (`xdg-open <carpeta>`): debe ser `dolphin --select <ruta>`; abrir el PDF con
  su aplicación y mostrarlo en Dolphin son operaciones distintas (§4.2 de la instrucción).

### 1.4 Arquitectura y usabilidad

La ventana es una variación de Dolphin: navegación · tabla · detalles con pestañas · consola · barra de estado. Con el
nombre oculto se reconoce un gestor de archivos, no un entorno de escritura. El trabajo principal (escribir, ver el
PDF, corregir un error) obliga a saltar entre tres aplicaciones.

### 1.5 Riesgos

| riesgo | mitigación |
|---|---|
| escribir sobre las fuentes del autor | el editor solo escribe con Ctrl+S explícito; si el archivo cambió en disco desde que se abrió, avisa y no sobrescribe sin confirmación; la compilación nunca escribe fuentes (R7) |
| recorrer cientos de carpetas en cada arranque | caché por fecha de modificación y tamaño en `$XDG_CACHE_HOME`; recorrido en una tarea con progreso y cancelable; sin leer PDF (R3) |
| el despacho (sensible, cliente) | ninguna ruta ni nombre del despacho en el repo: la carpeta por omisión sale de `DESPACHO_DIR` de `core/env.py` en la máquina; ninguna prueba ni captura la usa (R2) |
| romper el contrato de `docencia` con `main.sh` | la CLI solo **gana** una opción (`-k`, conservar auxiliares) y lee `CORE_DIR` si su búsqueda hacia arriba falla; ruta, `-s`, argumento, códigos de salida y `auto` no cambian (R8) |
| la caché de páginas del PDF crece | `$XDG_CACHE_HOME/latex-studio/paginas`, con límite de tamaño y borrado de lo más antiguo (R11) |
| QtPdf no instalado y sin `sudo` | visor propio con `pdftoppm`; la mejora con `PdfMultiPageView` queda anotada para el autor (R10) |

## 2. Referencias y distribución

| referencia | qué se toma | qué no |
|---|---|---|
| **TeXstudio / TeXmaker** | estructura del documento a la izquierda, editor en el centro, visor PDF integrado a la derecha con SyncTeX (Ctrl+clic), mensajes y registro abajo plegables, F5 / Ctrl+B para compilar | la barra de 40 iconos; el visor como ventana aparte |
| **VS Code + LaTeX Workshop** | árbol del proyecto y esquema (secciones, figuras, etiquetas) en la barra lateral, Problemas con archivo y línea que salta al editor, autocompletado de `\ref` y `\cite`, compilación por receta según el proyecto (`latexmkrc`, comentario mágico) | la configuración por JSON |
| **Overleaf** | página de proyectos antes del editor; un proyecto = documento principal + sus archivos; el registro con «errores con explicación y sugerencia» | la nube; la colaboración |

Distribución (justificada por la tarea: escribir mirando el resultado y corregir lo que el compilador dice):

```
┌ barra de compilación: [Compilar ▸] [■] proyecto · motor · estado │ Guardar · Buscar · SyncTeX · Abrir PDF ┐
│ Proyectos ▸ (lista con estado)   │ pestañas de archivos abiertos     │ visor PDF (páginas, zoom,   │
│ ─ el abierto ─                    │ editor con resaltado LaTeX/BibTeX │  miniaturas, SyncTeX)       │
│   Archivos (principal, \input,   │ números de línea, buscar/reempl.  │                             │
│   .bib, latexmkrc)                │ autocompletado                    │                             │
│   Estructura (secciones, fig.,    │                                   │                             │
│   tablas, etiquetas)              │                                   │                             │
├───────────────────────────────────┴───────────────────────────────────┴─────────────────────────────┤
│ plegable: Problemas (con causa y acción) · Registro · Salida de la orden                               │
└ barra de estado: proyecto · motor · línea:columna · tarea en curso ─────────────────────────────────────┘
```

Y antes de abrir un proyecto (o con Ctrl+1), la **página de proyectos** al estilo Overleaf: los detectados, agrupados
por categoría, con carpeta, principal, motor, estado, última compilación, errores y avisos, bibliografía y auxiliares;
selección múltiple para la cola de compilación. Con los nombres ocultos, la ventana es la de un editor LaTeX.

## 3. Decisiones

- **R1. Un proyecto es un documento principal.** Un `.tex` con `\documentclass` sin comentar, que no es `subfiles`
  ni declara `% !TEX root`, y que ningún otro principal incluye. Sus archivos: los `\input`, `\include`, `\subfile`,
  `\import`/`\subimport` resueltos recursivamente, los `.bib` de `\addbibresource`/`\bibliography` y la configuración
  (`latexmkrc`, `.latexmkrc`, `proyecto.yaml`, `fuentes.yml`). Varios principales pueden compartir carpeta (las
  pruebas de `escritura` lo hacen); cada uno es un proyecto. Los incluidos no son proyectos aparte.
- **R2. Carpetas de trabajo configurables.** Por omisión `WRITING_DIR` y `DESPACHO_DIR` de `core/env.py` (las que
  existan), más las que el usuario añada con el diálogo de KDE; la lista y la profundidad (6 por omisión) se guardan en
  sus ajustes (QSettings), nunca en el repo. Se saltan las carpetas ocultas, `node_modules`, `_site`, `_freeze`,
  `.quarto`, `site_libs`, `.build` y `build`.
- **R3. Detección rápida.** Recorrido con `os.scandir` en una tarea con progreso y cancelable; cada `.tex` se lee
  una vez y su análisis se guarda en `$XDG_CACHE_HOME/latex-studio/proyectos.json` por (fecha, tamaño); el estado del PDF
  sale de las fechas, sin abrirlo.
- **R4. Motor: el declarado manda.** Orden: `% !TEX program` (o `TS-program`) → directivas `% arara:` → `latexmkrc`
  (`$pdf_mode`) → sin declaración, LuaLaTeX. Bibliografía: `% !BIB program` → `backend=` de biblatex → `\bibliography`
  sin biblatex (BibTeX) → biblatex (Biber). La ventana no ofrece pdfLaTeX ni XeLaTeX para un proyecto que no los declare.
- **R5. El compilador es el del proyecto.** (a) Si una carpeta superior tiene el compilador de su marco
  (`scripts/build.sh`) y la clase del documento vive en su `classes/`, se compila con él (es `escritura`: decisión
  §1.2; sus auxiliares van a `.build/`). (b) Con `latexmkrc`, `latexmk` (que lo lee). (c) Si no, `main.sh` con el motor y
  la bibliografía detectados. Nunca se elige otro motor que el del proyecto.
- **R6. Categorías solo con información.** `pruebas`/`plantillas` en la ruta → «Pruebas y plantillas»; `proyecto.yaml`
  (`tipo`, `esquema`, `tema`) → Tesis, Artículos, Documentos legislativos o Escritura académica; la clase (`tesis`,
  `articulo`, `monografia`, `ensayo`, `informe`…; `dictamen` legislativo; `oficio`, `memorando`, `acta`, `solicitud`,
  `agenda` institucionales); la carpeta (`theses`, `articles`, `essays`, `monographs`, `reports`); `fuentes.yml` →
  Escritura académica. Sin nada de eso, «Otros proyectos». La séptima categoría (pruebas) sale del nombre de la carpeta:
  sin ella, 220 pruebas del marco taparían los documentos.
- **R7. La compilación nunca toca las fuentes**; el editor escribe solo al guardar (Ctrl+S), y si el archivo cambió en
  disco desde que se abrió, avisa y ofrece recargar o sobrescribir.
- **R8. La CLI gana `-k` (`--conservar`)**: no borra los auxiliares al terminar bien. La ventana la usa siempre: SyncTeX
  necesita el `.synctex.gz`, el autocompletado de `\ref` lee el `.aux` y las pasadas siguientes son más rápidas (es lo
  que hacen TeXstudio, latexmk y Overleaf). «Limpiar auxiliares…» sigue mostrando la lista y confirmando.
- **R9. Errores presentables.** Cada problema lleva descripción, archivo y línea, **causa probable y acción
  recomendada** (paquete o clase que falta → `kpsewhich`/marco; referencia o cita indefinida; Biber sin `.bcf`; orden no
  definida; `$` que falta; entorno sin cerrar; archivo `\input` que no existe; recursión de `\input`), y el detalle
  técnico (las líneas del registro) desplegable. La regla está en `latex_app/diagnostico.py`, sin Qt, probada.
- **R10. Visor PDF propio.** Páginas con `pdftoppm` (PNG a la resolución del zoom, por demanda); miniaturas a baja
  resolución; zoom, ajuste al ancho, recarga al recompilar conservando la página; SyncTeX `view` (código → PDF,
  Ctrl+clic o Ctrl+Alt+J) y `edit` (PDF → código, doble clic). Con QtPdf instalado
  (`sudo apt install qml6-module-qtquick-pdf python3-pyside6.qtpdf`) se podría pasar a `PdfMultiPageView`.
- **R11. Caché de páginas acotada.** `$XDG_CACHE_HOME/latex-studio/paginas/<clave>/`, 200 MB como mucho; al pasarse se
  borran los PDF renderizados más antiguos. La clave lleva la fecha del PDF: recompilar invalida solo ese documento.
- **R12. Editor**: `TextArea` con `org.kde.syntaxhighlighting` (LaTeX, BibTeX; tema claro u oscuro de KSyntaxHighlighting
  según la luminosidad del fondo de Kirigami, que es el de Lliphi), números de línea, buscar y reemplazar con
  expresiones regulares (en Python), ir a línea, autocompletado (órdenes, entornos, `\ref`/`\eqref` de las `\label`,
  `\cite` de las claves de los `.bib`), comentar líneas.
- **R13. Atajos de editor LaTeX** (TeXstudio): F5 y Ctrl+B compilar, F6 reconstruir, Esc detiene, Ctrl+S guardar,
  Ctrl+F buscar, Ctrl+R reemplazar, Ctrl+G ir a línea, Ctrl+Espacio completar, Ctrl+clic o Ctrl+Alt+J SyncTeX,
  Ctrl+T comentar, F8 siguiente problema, Ctrl+1/Ctrl+2 proyectos/escritura, Ctrl+K paleta (no choca).
- **R14. KDE**: abrir el PDF con su aplicación (`xdg-open`), mostrar en Dolphin señalándolo (`dolphin --select`; sin
  Dolphin, la carpeta con `xdg-open`), abrir carpeta (`xdg-open`); elegir carpetas con `FolderDialog` (con la
  `QApplication` de `gui-comun` 3.0 es el de KDE). Las tres operaciones viven en `latex_app/escritorio.py` hasta que
  `gui-comun` 3.0 las traiga; entonces se sustituyen.
- **R15. Cola de compilación.** Varios proyectos marcados en la página de proyectos se compilan uno tras otro, cada uno
  con su compilador; la cola se ve y se cancela.
- **R16. Revisión de dependencias.** Antes de compilar (y con su propia orden): clases y paquetes del principal y sus
  incluidos que `kpsewhich` no encuentra (ni la carpeta del proyecto ni el marco), archivos `\input` o `.bib` que no
  existen, motor y bibliografía instalados. Solo lee.

## 4. Lo que queda para `gui-comun` 3.0

`QApplication` (los diálogos de KDE), las tres funciones de escritorio de R14, el componente de errores presentables
(aquí `componentes/ErrorPresentable.qml`) y una ventana sin plantilla. Se anotan en `registro.md` («Para promover»).
