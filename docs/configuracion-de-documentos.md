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
            opciones_desde: {carpeta: ../../sistema-editorial/temas, extension: .yml}  # alternativa a `opciones`
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
| escritura | `escritura/core/config/latex-studio.yml` | opciones de clase (formato, tema, salida, modo, doblecara…) y metadatos `\setmeta` de `metadata.tex` |
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

