---
tipo: readme
estado: activo
---
# docs/ — documentación de scripts_for_latex: arquitectura, decisiones e historial

Un documento por concepto, con nombre estable. El manual de uso no vive aquí: es
`../script_compilar_latex/README.md`.

## Por dónde empezar

| si eres… | empieza por |
|---|---|
| **quien compila** un `.tex` | `../script_compilar_latex/README.md` |
| **quien amplía** la herramienta (una opción, un motor) | [arquitectura.md](arquitectura.md) → [decisiones.md](decisiones.md) |
| **quien mantiene** o corrige un error | [decisiones.md](decisiones.md) §Pendientes → [arquitectura.md](arquitectura.md) → [historial/](historial/README.md) |
| **otro repo** que quiere saber si depende de este | `../README.md` §Qué es (quién compila qué) → [arquitectura.md](arquitectura.md) §Consumidores |

## Cómo se mantiene

- Lo nuevo va al documento de su concepto; nunca un `.md` por sesión, fase o fecha.
- La decisión y su porqué, a [decisiones.md](decisiones.md); lo que falta, a su §Pendientes.
- Lo cumplido o superado, a `historial/`, con aviso de dónde está lo vigente.
- El índice de abajo lo genera `python3 core/docs.py indice scripts_for_latex --aplicar` desde
  `~/Documents`.

## Índice

<!-- docs:inicio -->
| documento | tipo | estado | qué es |
|---|---|---|---|
| [arquitectura.md](arquitectura.md) | `doc` | `activo` | Arquitectura de compilar_latex: flujo, módulos, estado global, cómo se amplía y quién la usa |
| [decisiones.md](decisiones.md) | `decision` | `activo` | Decisiones de scripts_for_latex |
| [historial/README.md](historial/README.md) | `readme` | `activo` | docs/historial/ — lo cumplido: bitácoras de depuración de script_compilar_latex |
| [historial/bugs-corregidos.md](historial/bugs-corregidos.md) | `bitacora` | `hecho` | Errores corregidos en la reescritura modular de compilar_latex |

<sub>Bloque generado por `core/docs.py indice` desde el frontmatter de docs/ (2026-10-04); no se edita a mano.</sub>
<!-- docs:fin -->
