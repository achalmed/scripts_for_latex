# Proyectos de muestra de LaTeX Studio

Árbol propio para las pruebas de detección y compilación y para las capturas (nunca documentos reales): se copia a una
carpeta temporal y se compila allí.

| carpeta | qué prueba |
|---|---|
| `tesis-multiarchivo/` | un principal con `\input`, `\include`, `\label`, figura, tabla y `.bib` con Biber; `proyecto.yaml` (tipo tesis); los capítulos no son proyectos |
| `articulo-bibtex/` | `% !TEX program` y `% !BIB program = bibtex`, `\bibliography` |
| `con-error/` | un documento que no compila (orden no definida) |
| `con-latexmkrc/` | un `latexmkrc` con `$pdf_mode = 4`: se compila con latexmk |
| `marco/` | un marco con compilador propio (`scripts/build.sh`, `classes/`): sus documentos se compilan con él; `pruebas/` es «Pruebas y plantillas» |
