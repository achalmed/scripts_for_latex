---
tipo: doc
titulo: 'Configuración de documentos: el esquema latex-studio.yml que cada marco publica'
estado: activo
forma: referencia
---
# Configuración de documentos desde LaTeX Studio (`latex-studio.yml`)

Contrato entre LaTeX Studio y los marcos LaTeX del ecosistema (docencia, escritura, qillqasqa/marco_documental, yupay,
cv, CampusTeX). Pedido del autor el 2026-11-08: tener desde la ventana el mayor control posible de cada documento —
editar sus metadatos (curso, estudiante, código, fecha, título, autor, logos…), mostrar u ocultar sus elementos (nivel,
tiempo, puntaje, cajas, títulos de etapa, número y título de paso…) y elegir sus opciones (tema, salida, modo…).

**Regla de reparto.** LaTeX Studio no sabe nada de ningún marco: lee el esquema que el marco publica y pinta un
formulario genérico. Lo que un documento puede configurar lo decide y lo implementa su marco (sus clases), una sola
vez, en su repo. Un marco nuevo solo tiene que escribir su `latex-studio.yml`.

## 1. Dónde vive el esquema

LaTeX Studio busca, desde la carpeta del documento principal hacia arriba (hasta 10 niveles), el primer archivo de
estos tres nombres, relativos a cada carpeta: `latex-studio.yml`, el mismo dentro de `config/` y el mismo dentro
de `config/` bajo `core/` (así lo publica escritura). El primero que
encuentra es el esquema del marco del documento. Sin esquema, el documento recibe solo la sección genérica (§5).

## 2. Forma del esquema

```yaml
# <marco>/config/latex-studio.yml — lo que LaTeX Studio puede configurar en los documentos de este marco
version: 1
marco: docencia
documentos:                      # uno por familia de clases; se elige el primero cuya lista `clases` contiene la clase
  - nombre: Evaluación
    clases: [academic-exam]      # vacío u omitido: todas las clases
    categoria: Docencia y evaluaciones   # opcional: la categoría de la barra lateral para estos documentos
    icono: view-calendar-tasks           # opcional: su icono (Breeze)
    secciones:
      - titulo: Datos de la evaluación
        icono: document-properties          # nombre de icono de Breeze
        descripcion: Lo que imprime el membrete.  # opcional
        campos:
          - clave: curso                    # única dentro del documento
            etiqueta: Curso
            tipo: texto                     # texto · texto_largo · interruptor · opcion · numero · archivo · fecha
            ayuda: Nombre del curso tal como sale en el membrete.   # opcional
            omision: ""                     # el valor cuando el documento no lo escribe (opcional)
            opciones: [a, b]                # solo tipo opcion
            opciones_desde: {carpeta: ../../estilos-visuales/temas, extension: .yml}  # alternativa a `opciones`
            destino: {orden: '\curso'}      # dónde se lee y se escribe (§3)
```

`categoria` (y `icono`) dice en qué categoría de la ventana aparecen esos documentos; una categoría que no es de las
fijas se crea sola. Así ningún documento de un marco con esquema cae en «Otros proyectos». Sin categoría declarada, la
ventana decide por la clase y por la carpeta (reglas R6 de `proyectos.categorizar`: también reconoce la salida de Quarto
junto a su `.qmd`, las plantillas de Pandoc, `vendor/`, `archivo/` y `notas/`).

`opciones_desde` lista los nombres (sin extensión) de los archivos de una carpeta, relativa al archivo del esquema;
sirve para valores que cambian con el marco (temas, formatos). `tipo: archivo` es una ruta (logo, imagen) relativa al
documento.

## 3. Destinos: dónde se lee y se escribe cada campo

| destino | en el documento | lectura | escritura |
|---|---|---|---|
| `{orden: '\curso'}` | `\curso{valor}` en el preámbulo | el argumento de la última aparición | reemplaza el argumento; si no está, inserta la línea tras la última orden del mismo esquema (o tras `\documentclass`); vacío = se quita la línea |
| `{orden: '\setmeta', clave: titulo}` | `\setmeta{titulo}{valor}` | el segundo argumento | igual que arriba |
| `{opcion_clase: bn}` con `tipo: interruptor` | `\documentclass[…, bn]{…}` | presente o no | añade o quita la bandera |
| `{opcion_clase: tema}` | `\documentclass[…, tema=congreso]{…}` | el valor de la clave | reemplaza, añade o (vacío) quita la clave |
| `{lista: '\configuracion', clave: nivel}` | `\configuracion{nivel=false, …}` | el valor de la clave; `true`/`false` para interruptores | edita la clave dentro de la lista; si el valor es el de `omision`, la quita; si la lista queda vacía, quita la orden |
| `{metadatos_documento: tagging}` | `\DocumentMetadata{tagging=on, lang=es-PE, …}` **antes** de `\documentclass`, siempre en el principal | el valor de la clave | edita la clave; la omisión o el vacío la quitan; sin claves, se quita la orden; sin orden, se inserta justo antes de `\documentclass` (decisiones §1.25; el PDF etiquetado y accesible, C13.1) |

Cualquier destino admite `archivo: metadata.tex` (relativo a la carpeta del principal): se lee y se escribe en ese
archivo si existe y, si no, en el principal. Solo se toca el preámbulo (lo anterior a `\begin{document}`) y las
líneas comentadas no cuentan.

## 4. Cómo escribe LaTeX Studio

Nunca escribe al cambiar un campo. «Aplicar» muestra primero la diferencia (archivo y líneas antes → después) y solo
escribe tras confirmar; después puede compilar. Es la única escritura de fuentes fuera de Ctrl+S en el editor, y no
pisa un archivo que el editor tenga con cambios sin guardar. Un documento del despacho se configura igual que
cualquier otro: es el autor quien lo abre; las pruebas y las sesiones del asistente no abren, leen ni configuran
documentos del despacho (usan `studio/ejemplo/`).

## 5. La sección genérica (todo documento)

Sin esquema, o además del esquema, todo documento muestra «Documento»: título (`\title`), autor (`\author`), fecha
(`\date`) y las opciones de la clase como texto libre. Un marco puede ocultarla con `generica: false` en su
`documentos[i]`.

## 6. Qué hace cada marco (estado)

| marco | esquema | qué expone |
|---|---|---|
| docencia | `docencia/config/latex-studio.yml` | `academic-exam`: datos de la evaluación, presentación de preguntas, solución, cajas, membrete y salida (`\configuracion{…}` de la clase, 2026-11-08); `academic-report`, `academic-beamer`: sus metadatos |
| escritura | `escritura/core/config/latex-studio.yml` | opciones de clase (formato, tema, salida, modo, doblecara…), metadatos `\setmeta` de `metadata.tex`, los datos de sus paquetes (§8), la biblioteca, la ayuda de la IA, los documentos nuevos y «Antes de entregar» (§9 a §12) |
| qillqasqa (marco_documental) | `qillqasqa/marco_documental/config/latex-studio.yml` | los documentos institucionales y legislativos: sus metadatos y opciones |
| yupay | `yupay/…/latex-studio.yml` | la rendición de viáticos |
| cv | `cv/main/config/latex-studio.yml` | el CV multiperfil (categoría «Currículum vítae») |
| CampusTeX (`11 Book`) | `11 Book/config/latex-studio.yml` | los libros de curso (categoría «Libros de curso») |
| bookmarks | `bookmarks/config/latex-studio.yml` | solo la categoría del directorio institucional |

Docencia declara además las versiones de `academic-exam` (examen, claves, soluciones, todos; §7).

## 7. Versiones de un mismo `.tex` (`versiones:`)

Un marco cuyo compilador produce varias salidas de un mismo documento —docencia: el examen en blanco, la hoja de claves
y el solucionario de una evaluación— lo declara en `documentos[i]`:

```yaml
    versiones:
      comentario: MODO             # «% !MODO = soluciones» al inicio del .tex: la versión que compila F5
      argumento: --modo            # cómo se le pide una versión a <marco>/scripts/build.sh
      omision: examen              # la que vale si el documento no declara ninguna
      lista:
        - {clave: examen, nombre: Estudiante (enunciados), job: "{nombre}"}
        - {clave: soluciones, nombre: Solucionario (paso a paso), job: "{nombre}-soluciones"}
```

`job` es el nombre de la salida (`{nombre}` = el del `.tex`): de él salen el PDF, el `.log` y el `.synctex.gz` que la
ventana muestra y lee. El compilador del marco **debe** aceptar `<argumento> <clave>` y, sin él, compilar la versión
que declara el comentario (o la omisión), así cualquier editor que lo llame sin argumentos compila la que pide el
documento. Con eso:

- **la ventana** muestra un selector «Versión» bajo el proyecto abierto: elegir una la compila (F5, con
  `<argumento> <clave>`) y la muestra, **sin escribir en el documento**;
- **«Configurar el documento»** añade la sección «Versión»: fija la que compila F5 por omisión escribiendo, antes de
  `\documentclass`, `% !MODO = soluciones` y `% !TeX TXS-program:view = txs:///view-pdf-internal --embedded
  ?m)-soluciones.pdf` (el visor de TeXstudio abre así ese PDF; `?m)` es el nombre del maestro sin comillas, que `%` sí
  pone); la de omisión quita las dos líneas. La primera vez que TeXstudio ve esa orden pregunta si la permite
  (seguridad de sus comentarios mágicos): «Yes to All» la guarda en su lista blanca y no vuelve a preguntar, porque la
  orden es la misma en todos los documentos;
- **`studio/compilar.py`** (el «Compilar» de TeXstudio) compila la declarada, o la que diga `--version <clave>`;
  `--versiones` las lista.

La muestra (`studio/ejemplo/proyectos/marco`) declara `completa` y `resumen` con `--version` y `% !VERSION`; docencia,
las cuatro de `academic-exam` con `--modo` y `% !MODO`. Pruebas: `tests/test_versiones.py`.

## 8. Datos del proyecto (`datos:`)

Un marco cuyos documentos citan datos producidos fuera (figuras, tablas y cifras de un paquete) lo declara al nivel
del esquema; la pestaña «Datos» de la vista Escritura lo muestra (decisiones §1.16):

```yaml
datos:
  nombre: Datos de datafw          # el título de la pestaña y de sus avisos
  marcador: proyecto.yaml          # {proyecto} = la carpeta más cercana al principal que lo tiene (sin él: la del principal)
  recursos: [../../scripts/datos.sh, recursos, '{proyecto}', --json]   # imprime el JSON de abajo (60 s como mucho)
  actualizar: [../../scripts/datos.sh, importar, '{proyecto}', --actualizar]   # trae la última versión (se confirma)
  productor: {nombre: Datafw Studio, orden: [/usr/bin/python3, ../../../datafw/studio/main.py, --publicacion, '{proyecto}']}
```

Un argumento que empieza con «.» es una ruta relativa al esquema. `recursos` imprime
`{"paquetes": [{estudio, usada, ultima, nueva}], "figuras": [{id, titulo, insertar, existe}], "tablas": [{id, titulo,
insertar, existe, variantes}], "cifras": [{macro, valor}]}`; `insertar` es el texto que el doble clic pone en el
cursor. Una figura puede traer además `alt` (el texto alternativo: un borrador desde el indicador o el ya aprobado),
`alt_aprobado` y `insertar_alt` (la orden con el hueco `{alt}`): entonces el texto alternativo es **obligatorio** al
insertarla (decisiones §1.22; mejora C8.3 del flujo de conocimiento): el doble clic abre el diálogo con el borrador, el
autor lo corrige y lo aprueba, y la ventana pone `insertar_alt` con `{alt}` lleno (sin llaves y con `% & # _ $`
escapados); sin texto no se inserta. Lo declara escritura (`escritura/core/config/latex-studio.yml`, con `reporting/main.py recursos` e `importar
--actualizar`); la muestra, `studio/ejemplo/proyectos/marco` (su `datos.yml` y `studio/ejemplo/proyectos/marco/scripts/datos_muestra.py`). Pruebas:
`tests/test_datos.py`.

## 9. La biblioteca del proyecto (`biblioteca:`)

Un marco cuyos documentos citan una biblioteca (libros con su clave y sus fichas) lo declara al nivel del esquema; la
pestaña «Citas» lo muestra (decisiones §1.18):

```yaml
biblioteca:
  nombre: Biblioteca
  marcador: proyecto.yaml          # {proyecto}: la carpeta más cercana al principal que lo tiene (sin ella, no aplica)
  buscar: [/usr/bin/python3, ../../../biblioteca-studio/lib/consulta.py, buscar, '{texto}']
  fichas: [/usr/bin/python3, ../../../biblioteca-studio/lib/consulta.py, fichas, '{proyecto}']
  citar:  [/usr/bin/python3, ../../../biblioteca-studio/lib/consulta.py, citar, '{proyecto}', '{id}']   # + --aplicar al confirmar
  abrir:  [/usr/bin/python3, ../../../biblioteca-studio/studio/main.py, 'biblioteca-studio://libro/{id}']
```

`buscar` imprime `[{calibre_id, clave, titulo, autores, anio, pdf, portada, insertar}]`; `fichas`, `[{archivo, nombre,
tipo, clave, pagina, verificacion, texto, insertar}]`; `citar`, `{clave, nueva, escrito, insertar}`: con `nueva` la
ventana pide confirmación y la repite con `--aplicar`.

Fichar desde la pestaña (decisiones §1.19; opcional: sin estas cuatro, la pestaña solo lista las fichas):

```yaml
  formulario:    [/usr/bin/python3, ../../../biblioteca-studio/lib/consulta.py, formulario]
  ficha:         [/usr/bin/python3, ../../../biblioteca-studio/lib/consulta.py, ficha, '{proyecto}', '{archivo}']
  nueva_ficha:   [/usr/bin/python3, ../../../biblioteca-studio/lib/consulta.py, nueva_ficha, '{proyecto}', '{datos}']   # + --aplicar al guardar
  guardar_ficha: [/usr/bin/python3, ../../../biblioteca-studio/lib/consulta.py, guardar_ficha, '{proyecto}', '{archivo}', '{huella}', '{datos}']   # + --aplicar
```

`formulario` imprime `{tipos: [{clave, nombre, secciones, literal, pagina, categoria, libro}], categorias}`: la ventana
pinta el formulario con eso. `ficha` (`{archivo}` es el nombre del archivo de la ficha) imprime `{archivo, huella, tipo,
calibre_id, clave, pagina, categoria, uso, verificacion, secciones: [{titulo, texto}], problemas}`. `{datos}` es un JSON
`{tipo, calibre_id, pagina, categoria, tema, uso, secciones: {título: texto}}`; las dos órdenes de escribir imprimen
`{archivo, verificacion: {estado, metodo, fecha}, detalle, problemas, nueva_fuente, renombra, antes, escrito}` (sin
`--aplicar`, `escrito` es falso: nada se escribió), `{codigo: "ficha_cambiada", error, actual}` si la ficha cambió desde
que se leyó con esa `huella`, o `{error}`.

## 10. La ayuda de la IA de una parte (`ayuda:`)

Un marco cuyos documentos tienen prompts por parte lo declara al nivel del esquema; la ventana lo ofrece en Herramientas ›
«Ayuda de la IA para esta parte…» (Ctrl+Alt+I; decisiones §1.19):

```yaml
ayuda:
  nombre: Ayuda de la IA
  marcador: proyecto.yaml
  prompt: [/usr/bin/python3, ../../../biblioteca-studio/lib/consulta.py, prompt_parte, '{proyecto}', '{archivo}']   # + --componente c
  pegar:  [/usr/bin/python3, ../../../biblioteca-studio/lib/consulta.py, pegar_parte, '{proyecto}', '{archivo}', '{pegado}', --tex, '{tex}']
```

`{archivo}` es el archivo abierto, relativo a `{proyecto}`. `prompt` imprime `{prompt, componente, titulo, componentes:
[{clave, titulo}], fuente: {ruta, titulo, version}, aviso, largo, contexto: {fichas, obras}}` o `{error}`; la ventana copia
`prompt` al portapapeles. `pegar` recibe dos rutas de archivos de la caché de la ventana: `{pegado}` (lo que respondió el
chat) y `{tex}` (el texto del editor, que puede tener cambios sin guardar), e imprime `{ok, errores, avisos, componente,
antes, despues, diff}`: si `ok` y el autor acepta, la ventana reemplaza `antes` por `despues` en el editor. Ninguna de las
dos escribe nada ni llama a un modelo. Opcional, `revisar_prompt: [..., '{prompt}', ...]` (decisiones §1.22; mejora C12.3):
antes de copiar, la ventana escribe el prompt en un archivo de su caché (`{prompt}`) y la orden imprime `{sensible, nivel:
alto|medio|ninguno, hallazgos: [{tipo, nivel, linea, texto}], total, porque, fuente}`; si `sensible`, el diálogo lo dice
con su porqué y su fuente y copiar queda a decisión del autor («Copiar de todos modos» o «No copiar»); si la orden falla,
también pregunta. Sin la orden, copia sin preguntar. Las declara escritura (`escritura/core/config/latex-studio.yml`);
la muestra, `studio/ejemplo/proyectos/marco` (`studio/ejemplo/proyectos/marco/scripts/datos_muestra.py`), las §9 y §10.
Pruebas: `tests/test_datos.py`.

## 11. Documentos nuevos (`nuevo:`)

Un marco que sabe crear documentos (un informe, una tesis, un artículo…) lo declara al nivel del esquema; la ventana lo
ofrece en «Nuevo documento» (Ctrl+N, el botón de la página de proyectos y la paleta; decisiones §1.20):

```yaml
nuevo:
  nombre: Escritura                # el marco, en la lista de marcos (si hay varios que declaran `nuevo:`)
  tipos: [/usr/bin/python3, ../../scripts/nuevo_documento.py, tipos]
  crear: [/usr/bin/python3, ../../scripts/nuevo_documento.py, crear, '{datos}']   # + --aplicar al crear
```

La sección se busca en cada carpeta de trabajo (el esquema en ella o en una de arriba) y en el marco de cada proyecto
detectado; un argumento que empieza con «.» es una ruta relativa al esquema, y las órdenes corren en la carpeta de trabajo.
`tipos` imprime `{marco, tipos: [{clave, nombre, descripcion, carpeta, variante: {rotulo, omision, opciones: [{clave,
nombre, descripcion}]}, campos: [{clave, rotulo, obligatorio, tipo, opciones, omision, segun_variante}]}]}`: `tipo` es
`texto`, `lineas` (un valor por línea) u `opcion` (con `opciones: [{clave, nombre}]`); `segun_variante` (`{variante:
[claves]}`) dice qué opciones admite cada variante, y un campo sin ninguna para la elegida no se muestra. `{datos}` es el
JSON `{tipo, variante, <clave>: valor…}` del formulario. Sin `--aplicar`, `crear` **simula**: crea el documento en un
temporal y devuelve `{destino, carpeta, slug, tipo, principal, archivos, avisos, escrito: false}` sin tocar la carpeta
real; con `--aplicar` lo crea y devuelve lo mismo con `escrito: true`, y la ventana abre `principal`. Un problema (falta
un dato obligatorio, la carpeta ya existe) vuelve como `{error}`. Lo declara escritura (`escritura/core/config/latex-studio.yml`,
con `escritura/scripts/nuevo_documento.py` sobre `proyecto/main.py nuevo`); la muestra, `studio/ejemplo/proyectos/marco`
(`studio/ejemplo/proyectos/marco/scripts/nuevo_muestra.py`). Pruebas: `tests/test_datos.py` y `tests/test_controladores.py`.

## 12. Antes de entregar (`entrega:`)

Un marco que sabe revisar un documento antes de entregarlo lo declara al nivel del esquema; la ventana lo ofrece en
Herramientas › «Antes de entregar…» (Ctrl+Alt+E y la paleta; decisiones §1.21):

```yaml
entrega:
  nombre: Antes de entregar
  marcador: proyecto.yaml          # {proyecto}: la carpeta más cercana al principal que lo tiene (sin ella, no aplica)
  revisar: [/usr/bin/python3, ../../scripts/antes_de_entregar.py, revisar, '{proyecto}']
  marcar: [/usr/bin/python3, ../../scripts/antes_de_entregar.py, marcar, '{proyecto}', '{id}', '{estado}', '{nota}']   # + --aplicar
  registrar_ia: [/usr/bin/python3, ../../scripts/antes_de_entregar.py, registrar_ia, '{proyecto}', '{datos}']          # + --aplicar
```

`revisar` (120 s como mucho; no escribe nada) imprime `{tipo, lista: {clave, nombre, fuente}, grupos: [{clave, nombre}],
controles: [{id, grupo, nombre, porque, fuente, estado, detalle, hallazgos: [{archivo, linea, texto}]}]}` o `{error}`.
`estado` es `ok`, `aviso`, `falla` o `manual` (un punto que marca el autor; lleva además `marcado`: `hecho`, `justificado` o
vacío, y `nota`); `porque` es una línea y `fuente` la referencia que lo funda, que la ventana pinta tenues bajo el nombre;
`archivo` es relativo a `{proyecto}` (o absoluto) y un clic en el hallazgo lo abre en esa `linea`. Los `grupos` dan el
orden y el título de las secciones del diálogo. **El veredicto es de la ventana** (`datos.veredicto`): «Listo para
entregar» solo si ningún control está en `falla` y todo `manual` está marcado; si no, «Faltan N» (las fallas más lo manual
sin marcar). Los avisos no bloquean.

`marcar` guarda un punto manual: `{id}` es el del control, `{estado}` es `hecho` (la casilla), `justificado` (sin casilla y
con nota) o `pendiente`, y `{nota}` puede ir vacía; imprime `{id, estado, nota, fecha, escrito}` o `{error}` (justificar
sin nota, un punto que no es manual). `registrar_ia` recibe en `{datos}` el JSON `{archivo, parte, prompt: {titulo, ruta,
version, componente, texto}, resumen}` de un cambio de la ayuda de la IA (§10) que el autor puso en el editor, y lo
agrega al registro del marco (escritura: `<proyecto>/ia/registro.yml`, del que regenera `<proyecto>/ia/declaracion.tex`); imprime `{uso, total,
escrito}`. Las dos simulan sin `--aplicar`; la ventana las corre con él: marcar al tocar la casilla o al terminar la nota
(y vuelve a revisar), registrar al pulsar «Poner en el editor». Lo declara escritura (`escritura/core/config/latex-studio.yml`,
con `escritura/scripts/antes_de_entregar.py`; sus controles, en `escritura/docs/verificacion.md` §9); la muestra,
`studio/ejemplo/proyectos/marco` (`studio/ejemplo/proyectos/marco/scripts/entrega_muestra.py`). Pruebas: `tests/test_datos.py` y
`tests/test_controladores.py`.

**La autoevaluación con la rúbrica** (opcional; decisiones §1.22; mejora C11.2):

```yaml
  rubrica: [/usr/bin/python3, ../../scripts/antes_de_entregar.py, rubrica, '{proyecto}']
  autoevaluar: [/usr/bin/python3, ../../scripts/antes_de_entregar.py, autoevaluar, '{proyecto}', '{datos}']   # + --aplicar
```

`rubrica` imprime `{rubrica, origen, ruta, puntajes: {clave: {puntaje, justificacion, fecha}}, nota: {nota, vetos, faltan},
cambio, problemas, porque, fuente}`; `rubrica` tiene el **formato común** del ecosistema (`{titulo, fuente, criterios:
[{clave, nombre, peso, niveles: [{puntaje, descriptor}]}]}`, el de `escritura/config/entrega/rubrica.schema.yml`) o es
`null` si el documento no tiene; `cambio` dice que la rúbrica cambió desde que se puntuó. `autoevaluar` recibe en `{datos}`
`{clave, puntaje, justificacion}` y, con `--aplicar`, lo guarda (imprime `{puntajes, nota, escrito}` o `{error}`: un
puntaje que no es nivel, una justificación corta). La ventana lo pinta en «Autoevaluación» (`DialogoRubrica.qml`): los
niveles del mejor al peor con su descriptor, la justificación y «Guardar» por criterio.

**El lector frío** (opcional; decisiones §1.22; mejora C11.4): `lector_frio: [..., '{proyecto}']` con `--aplicar` prepara
fuera del documento una versión sin nombres para un revisor externo y la compila; imprime `{pdf, quitado: [{archivo, linea,
campo}], pendientes, escrito}` o `{error}`. La ventana la ofrece en el pie de «Antes de entregar» («Versión para lector
frío») y abre el PDF. Los comentarios del revisor los trae el marco y vuelven como un control más, con sus hallazgos.

**Un control con `accion`** (`autoevaluar` o `matriz`) lleva en el diálogo el botón que abre su ventana (la autoevaluación,
la matriz de consistencia de §13): el control se resuelve allí y «Antes de entregar» lo vuelve a revisar.

## 13. La matriz de consistencia (`matriz:`)

Un marco cuyos documentos tienen matriz de consistencia (problema, objetivos, hipótesis, variables, indicadores y método)
la declara al nivel del esquema; la ventana la muestra en Herramientas › «Matriz de consistencia…» (Ctrl+Alt+M) y ofrece
el «Asistente de pregunta» (decisiones §1.22; mejoras C1.1 a C1.3 del flujo de conocimiento):

```yaml
matriz:
  nombre: Matriz de consistencia
  marcador: proyecto.yaml
  leer: [/usr/bin/python3, ../../scripts/matriz.py, leer, '{proyecto}']
  cuadro: [/usr/bin/python3, ../../scripts/matriz.py, cuadro, '{proyecto}']        # + --aplicar
  nueva: [/usr/bin/python3, ../../scripts/matriz.py, nueva, '{proyecto}']          # + --aplicar
  guia: [/usr/bin/python3, ../../scripts/matriz.py, guia]
  pregunta: [/usr/bin/python3, ../../scripts/matriz.py, pregunta, '{proyecto}', '{datos}']   # + --aplicar
```

`leer` (no escribe) imprime `{archivo, existe, no_aplica, porque, fuente, pregunta, metodo, columnas: [{clave, nombre,
porque, fuente}], filas: [{id, nivel, problema, objetivo, hipotesis, variables, indicadores: [{ref, existe, nombre,
detalle}], secciones: [{ref, existe, archivo, linea}], prueba, refutaria, supuesto, linea, problemas: [{estado, texto,
clase}]}], huerfanos: [{estado, fila, texto, clase, archivo, linea}], cuadro: {archivo, existe, al_dia}}`; `estado` es
`falla` (una hipótesis sin indicador o sin sección, un indicador o una sección que no existen) o `aviso` (falta lo que la
refutaría o el supuesto que cuestiona; un indicador que no se pudo comprobar). `archivo` es relativo a `{proyecto}`; un
clic en una sección lleva a su línea y «Editar la fila» abre la matriz en su línea. `cuadro` y `nueva` escriben con
`--aplicar` e imprimen `{archivo, escrito}` o `{error}` (el marco no pisa un cuadro escrito a mano). `guia` imprime
`{titulo, porque, fuente, pasos: [{clave, titulo, pregunta, ayuda, ejemplos, campos: [{clave, rotulo, tipo: texto|lineas,
obligatorio}], porque, fuente}]}`; `pregunta` recibe los valores del asistente en `{datos}` e imprime `{ok, avisos:
[{paso, estado, texto}], archivo, escrito}`: sin `--aplicar` revisa, con él guarda. Lo declara escritura
(`escritura/core/config/latex-studio.yml`, con `escritura/scripts/matriz.py`); la muestra,
`studio/ejemplo/proyectos/marco/scripts/flujo_muestra.py`. Pruebas: `tests/test_datos.py` y `tests/test_controladores.py`.

## 14. El revisor del editor (`revisor:`)

Un marco que sabe revisar el estilo y el LaTeX de un archivo lo declara al nivel del esquema; la ventana lo muestra en la
pestaña «Revisión» del panel inferior, al guardar y con Herramientas › «Revisar el estilo» (Ctrl+Alt+R) (decisiones §1.23;
mejoras C6.1, C6.2 y C13.2):

```yaml
revisor:
  marcador: proyecto.yaml
  revisar: [/usr/bin/python3, ../../scripts/revisor.py, revisar, '{archivo}', --proyecto, '{proyecto}', --nombre, '{ruta}']
  reglas: [/usr/bin/python3, ../../scripts/revisor.py, reglas]
```

`{archivo}` es una copia del texto del editor (con lo no guardado) en la caché de la ventana y `{ruta}` la ruta real.
`revisar` (30 s como mucho; no escribe nada) imprime `{perfil: {clave, nombre}, reglas: [{clave, clase: estilo|latex,
nombre, porque, fuente}], hallazgos: [{linea, columna, largo, regla, clase, texto, sugerencia}], resumen}` o `{error}`. La
ventana junta cada hallazgo con su regla y pinta la línea, el nombre, lo hallado, la sugerencia y la línea tenue «por qué
· fuente»; un clic va a la línea. **Sugiere y nunca reescribe**: nada del panel cambia el texto. El perfil de lector
(académico, decisor, estudiante) lo decide el marco. La muestra, `flujo_muestra.py`; pruebas en `tests/test_datos.py` y
`tests/test_controladores.py`.

## 15. Las plantillas (`plantillas:`)

Un marco con plantillas para lo que más se repite lo declara al nivel del esquema; la ventana lo ofrece en Herramientas ›
«Insertar una plantilla…» (Ctrl+Alt+T) (decisiones §1.24; mejora C13.4):

```yaml
plantillas:
  marcador: proyecto.yaml
  listar: [/usr/bin/python3, ../../scripts/plantillas.py, listar, '{proyecto}']
  componer: [/usr/bin/python3, ../../scripts/plantillas.py, componer, '{proyecto}', '{datos}']
```

`listar` imprime `{plantillas: [{clave, nombre, descripcion, porque, fuente, campos: [{clave, rotulo, tipo:
texto|lineas|opcion, opciones: [{clave, nombre}], omision, obligatorio, ayuda}]}]}`; `componer` recibe `{plantilla,
valores}` e imprime `{insertar, avisos}` o `{error}`. Ninguna escribe: la ventana muestra lo compuesto y lo pone en el
cursor al pulsar «Insertar». La muestra, `flujo_muestra.py`; pruebas en `tests/test_datos.py` y `tests/test_controladores.py`.
