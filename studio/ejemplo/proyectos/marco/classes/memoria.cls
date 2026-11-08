% memoria.cls — la clase del marco de muestra (sobre article).
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{memoria}[2026/11/02 clase de muestra]
\LoadClass[11pt]{article}

% Lo que configura LaTeX Studio (config/latex-studio.yml): metadatos y elementos visibles, todos con su omisión.
\RequirePackage{pgfkeys}
\newif\ifmem@logo \mem@logotrue
\newif\ifmem@fecha \mem@fechatrue
\pgfkeys{/memoria/.cd, logo/.is if=mem@logo, fecha/.is if=mem@fecha}
\newcommand{\configuracion}[1]{\pgfkeys{/memoria/.cd,#1}}
\def\mem@organizacion{}\newcommand{\organizacion}[1]{\def\mem@organizacion{#1}}
\def\mem@responsable{}\newcommand{\responsable}[1]{\def\mem@responsable{#1}}
\def\mem@logo{}\newcommand{\logo}[1]{\def\mem@logo{#1}}
