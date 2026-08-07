import os
import json
import re
from groq import Groq

# ══════════════════════════════════════════════════════════════════════
# LAZY INIT CLIENT GROQ
# ══════════════════════════════════════════════════════════════════════

_client = None

def get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


# ══════════════════════════════════════════════════════════════════════
# UTILITAIRES LATEX
# ══════════════════════════════════════════════════════════════════════

def _esc(s: str) -> str:
    """Échappe les caractères spéciaux LaTeX pour les métadonnées."""
    if not s:
        return ''
    replacements = [
        ('\\', '\\textbackslash{}'),
        ('&',  '\\&'),
        ('%',  '\\%'),
        ('_',  '\\_'),
        ('#',  '\\#'),
        ('{',  '\\{'),
        ('}',  '\\}'),
        ('$',  '\\$'),
        ('^',  '\\^{}'),
        ('~',  '\\~{}'),
    ]
    for old, new in replacements:
        s = s.replace(old, new)
    return s


def nettoyer_texte_latex(text: str) -> str:
    if not text:
        return ""
    text = text.replace('\u2019', "'").replace('\u2018', "`")
    text = text.replace('\u201c', "``").replace('\u201d', "''")
    text = text.replace('\u2013', "--").replace('\u2014', "---")
    text = text.replace('\uf0d8', '')
    text = re.sub(r'(\d+)(?<!\\)%', r'\1\\%', text)
    return text


def nettoyer_code_listing(code: str) -> str:
    return ''.join(c if ord(c) <= 0x00FF else '?' for c in code)


# ══════════════════════════════════════════════════════════════════════
# GÉNÉRATION DES SECTIONS VIA GROQ
# ══════════════════════════════════════════════════════════════════════

def generer_section_cer(
    section: str,
    titre_prosit: str,
    contexte: str,
    besoins: str,
    contraintes: str,
    problematique: str,
    plan_action: list,
    contenu_source: str = "",
    etape_index: int = None,
    etape_label: str = None
) -> str:
    plan_str = "\n".join([f"{i+1}. {p}" for i, p in enumerate(plan_action)])
    source_ctx = (
        f"\nDocuments de référence (corbeille / workshop) :\n---\n{contenu_source[:4000]}\n---\n"
        if contenu_source else ""
    )

    if section == "realisation_etape":
        prompt = f"""Tu es un expert académique rédigeant un CER pour l'UCAC-ICAM.

PROSIT : {titre_prosit}
Contexte : {contexte}
Besoins : {besoins}
Contraintes : {contraintes}
Problématique : {problematique}
Plan d'action : {plan_str}
{source_ctx}

Rédige le contenu détaillé de l'ÉTAPE {etape_index} : "{etape_label}"

RÈGLES :
1. Minimum 400 mots, style académique rigoureux
2. Sous-sections (###) si nécessaire
3. Inclure : définitions formelles, exemples liés au prosit, tableaux comparatifs si pertinent,
   pseudocode/code si algorithmique, formules mathématiques ($...$) si pertinent
4. Markdown : **gras**, `code`, tableaux |col|col|, listes
5. Génère UNIQUEMENT le contenu, sans en-tête général
"""

    elif section == "validation":
        prompt = f"""Tu es un expert académique rédigeant un CER pour l'UCAC-ICAM.

PROSIT : {titre_prosit} | Problématique : {problematique}
Plan : {plan_str}
{source_ctx}

Rédige "Validation des pistes de solutions" :
- 4-5 sous-sections, chacune = une piste sous forme de question
- Format : sous-titre "Piste X : [question] ?" puis réponse 150-200 mots
- Conclure chaque piste : "**Piste validée / partiellement validée / invalidée.**"
"""

    elif section == "conclusion":
        prompt = f"""CER UCAC-ICAM — PROSIT : {titre_prosit}
Problématique : {problematique} | Plan : {plan_str}

Rédige "Conclusion et retours sur les objectifs" :
1. Rappel de la problématique
2. Bilan par étape (Atteint / Partiellement / Non atteint) en liste à puces
3. Synthèse de la réponse à la problématique
Minimum 250 mots.
"""

    elif section == "bilan":
        prompt = f"""CER UCAC-ICAM — PROSIT : {titre_prosit} | Plan : {plan_str}

Rédige "Bilan critique du travail effectué" en liste à puces :
- Points forts
- Limites et difficultés
- Perspectives et approfondissements possibles
Minimum 200 mots, style réflexif.
"""

    elif section == "synthese":
        prompt = f"""CER UCAC-ICAM — PROSIT : {titre_prosit} | Plan : {plan_str}

Rédige "Synthèse des résultats obtenus" :
- Résumé par étape en bullet points
- Données chiffrées si disponibles
- Résultats clés en **gras**
Minimum 200 mots.
"""

    elif section == "references":
        prompt = f"""CER UCAC-ICAM — PROSIT : {titre_prosit} | Thèmes : {plan_str}

Génère une bibliographie académique de 6-10 références.
Format OBLIGATOIRE (une référence par ligne) :
[1] Auteur, *Titre*, Éditeur, Année.
[2] ...
Inclure : livres académiques, articles, URLs réels (MIT, OpenClassrooms, docs officiels).
NE génère QUE la bibliographie, pas d'autre texte.
"""

    else:
        return ""

    response = get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=3000,
    )
    return response.choices[0].message.content


# ══════════════════════════════════════════════════════════════════════
# CONVERSION MARKDOWN → LATEX
# Produit du LaTeX conforme au style du PDF exemple (boîtes tcolorbox,
# puces rouges, numéros rouges gras, booktabs, lstlisting)
# ══════════════════════════════════════════════════════════════════════

def markdown_to_latex(md_text: str) -> str:
    if not md_text:
        return ''
    md_text   = nettoyer_texte_latex(md_text)
    lines     = md_text.split('\n')
    result    = []
    in_code   = False
    in_item   = False
    in_enum   = False
    in_table  = False
    table_buf = []

    def pi(text):
        """Process inline markdown."""
        text = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', text)
        text = re.sub(r'\*(.+?)\*',     r'\\textit{\1}', text)
        text = re.sub(r'`([^`]+)`',     r'\\texttt{\1}', text)
        text = re.sub(r'\[(.+?)\]\((.+?)\)', r'\\href{\2}{\1}', text)
        return text

    def close_lists():
        nonlocal in_item, in_enum
        out = []
        if in_item:
            out.append('\\end{itemize}')
            in_item = False
        if in_enum:
            out.append('\\end{enumerate}')
            in_enum = False
        return out

    def flush_table():
        nonlocal table_buf, in_table
        if not table_buf:
            return []
        # Filtrer les lignes séparatrices
        rows = [r for r in table_buf if not re.match(r'^\|[-\s|:]+\|$', r.strip())]
        if not rows:
            table_buf = []; in_table = False
            return []
        cols    = [c.strip() for c in rows[0].strip('|').split('|')]
        nb_cols = len(cols)
        out = [
            r'\begin{center}',
            r'\begin{tabular}{' + 'l' * nb_cols + '}',
            r'\toprule',
        ]
        for i, row in enumerate(rows):
            cells = [c.strip() for c in row.strip('|').split('|')]
            while len(cells) < nb_cols:
                cells.append('')
            if i == 0:
                out.append(' & '.join(r'\textbf{' + pi(c) + '}' for c in cells[:nb_cols]) + r' \\')
                out.append(r'\midrule')
            else:
                out.append(' & '.join(pi(c) for c in cells[:nb_cols]) + r' \\')
        out += [r'\bottomrule', r'\end{tabular}', r'\end{center}', '']
        table_buf = []; in_table = False
        return out

    LANG_MAP = {
        'python':'Python','java':'Java','c':'C','cpp':'C++',
        'js':'JavaScript','bash':'bash','sql':'SQL','':'Python'
    }

    for line in lines:
        s = line.strip()

        # ── Blocs de code ─────────────────────────────────────────────
        if s.startswith('```'):
            result.extend(close_lists())
            if in_table: result.extend(flush_table())
            if in_code:
                result += [r'\end{lstlisting}', '']
                in_code = False
            else:
                lang = LANG_MAP.get(s[3:].strip().lower(), 'Python')
                result.append(r'\begin{lstlisting}[language=' + lang + ']')
                in_code = True
            continue

        if in_code:
            result.append(nettoyer_code_listing(line))
            continue

        # ── Tableaux ──────────────────────────────────────────────────
        if s.startswith('|'):
            result.extend(close_lists())
            in_table = True
            table_buf.append(s)
            continue
        elif in_table:
            result.extend(flush_table())

        # ── Ligne vide ────────────────────────────────────────────────
        if not s:
            result.extend(close_lists())
            result.append('')
            continue

        # ── Titres ────────────────────────────────────────────────────
        if s.startswith('#### '):
            result.extend(close_lists())
            result.append(r'\paragraph{' + pi(s[5:]) + '}')
            continue
        if s.startswith('### '):
            result.extend(close_lists())
            result.append(r'\subsubsection{' + pi(s[4:]) + '}')
            continue
        if s.startswith('## '):
            result.extend(close_lists())
            result.append(r'\subsection{' + pi(s[3:]) + '}')
            continue
        if s.startswith('# '):
            result.extend(close_lists())
            result.append(r'\section{' + pi(s[2:]) + '}')
            continue

        # ── Listes non ordonnées (puces rouges comme dans le PDF) ─────
        if re.match(r'^[-*+] ', s):
            if not in_item:
                result.extend(close_lists())
                result.append(
                    r'\begin{itemize}[leftmargin=1.5cm,'
                    r' label=\textcolor{maincolor}{$\bullet$}]'
                )
                in_item = True
            result.append(r'  \item ' + pi(s[2:]))
            continue

        # ── Listes ordonnées (numéros rouges gras comme dans le PDF) ──
        if re.match(r'^\d+\. ', s):
            if not in_enum:
                result.extend(close_lists())
                result.append(
                    r'\begin{enumerate}[leftmargin=1.5cm,'
                    r' label=\textcolor{maincolor}{\textbf{\arabic*.}}]'
                )
                in_enum = True
            result.append(r'  \item ' + pi(re.sub(r'^\d+\.\s+', '', s)))
            continue

        # ── Paragraphe normal ─────────────────────────────────────────
        result.extend(close_lists())
        result.append(pi(s))
        result.append('')

    result.extend(close_lists())
    if in_table: result.extend(flush_table())
    if in_code:  result.append(r'\end{lstlisting}')

    text = '\n'.join(result)
    for env in ['itemize', 'enumerate']:
        diff = text.count(f'\\begin{{{env}}}') - text.count(f'\\end{{{env}}}')
        if diff > 0:
            text += f'\n\\end{{{env}}}' * diff
    return text


# ══════════════════════════════════════════════════════════════════════
# PRÉAMBULE LATEX  (identique au .tex exemple fourni)
# ══════════════════════════════════════════════════════════════════════

PREAMBLE = r"""\documentclass[12pt,a4paper]{report}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\usepackage{graphicx}
\usepackage{enumitem}
\usepackage{xcolor}
\usepackage{fancyhdr}
\usepackage{mdframed}
\usepackage{array}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{tabularx}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{listings}
\usepackage{float}
\usepackage{caption}
\usepackage{tikz}
\usetikzlibrary{positioning,shapes,arrows,calc}
\usepackage{url}
\usepackage{ragged2e}
\usepackage[colorlinks=true, linkcolor=black, urlcolor=blue, citecolor=black]{hyperref}
\usepackage{parskip}
\usepackage{titlesec}
\usepackage{multirow}
\usepackage{tcolorbox}
\tcbuselibrary{theorems,skins,breakable}

\geometry{margin=2.5cm, headheight=15pt}

% ===== COULEURS =====
\definecolor{maincolor}{RGB}{180,0,0}
\definecolor{lightgray}{RGB}{240,240,240}
\definecolor{codeblue}{RGB}{0,0,180}
\definecolor{lightblue}{RGB}{220,235,248}
\definecolor{lightgreen}{RGB}{230,255,230}
\definecolor{lightyellow}{RGB}{255,255,220}
\definecolor{lightred}{RGB}{255,240,240}
\definecolor{sectiongray}{RGB}{80,80,80}
\definecolor{darkgreen}{RGB}{0,120,0}

% ===== BOITES TCOLORBOX =====
\tcbset{
  defbox/.style={colback=lightblue,colframe=maincolor,
    fonttitle=\bfseries,arc=4pt,boxrule=1.5pt,breakable},
  proofbox/.style={colback=lightgreen,colframe=darkgreen,
    fonttitle=\bfseries\color{darkgreen},arc=4pt,boxrule=1pt,breakable},
  propbox/.style={colback=lightyellow,colframe=orange!70!black,
    fonttitle=\bfseries,arc=4pt,boxrule=1pt,breakable},
  warnbox/.style={colback=lightred,colframe=maincolor,
    fonttitle=\bfseries\color{maincolor},arc=4pt,boxrule=1pt,breakable}
}

% ===== STYLE CODE =====
\lstset{
  basicstyle=\small\ttfamily,
  backgroundcolor=\color{lightgray},
  frame=single, breaklines=true, language=Python,
  keywordstyle=\color{codeblue}\bfseries,
  commentstyle=\color{gray}\itshape,
  showstringspaces=false,
  numbers=left, numberstyle=\tiny\color{gray},
  stepnumber=1, tabsize=2,
  literate=
    {é}{{\'{e}}}1 {è}{{\`{e}}}1 {ê}{{\^{e}}}1 {ë}{{\"{e}}}1
    {à}{{\`{a}}}1 {â}{{\^{a}}}1 {ù}{{\`{u}}}1 {û}{{\^{u}}}1
    {î}{{\^{i}}}1 {ï}{{\"{i}}}1 {ô}{{\^{o}}}1 {ç}{{\c{c}}}1
    {É}{{\'{E}}}1 {È}{{\`{E}}}1 {À}{{\`{A}}}1 {Î}{{\^{I}}}1
    {Ç}{{\c{C}}}1 {œ}{{\oe}}1 {Œ}{{\OE}}1 {°}{{$^{\circ}$}}1,
}

% ===== EN-TÊTES FANCYHDR =====
\urlstyle{same}
\sloppy
\makeatletter
\g@addto@macro{\UrlBreaks}{\UrlOrds}
\makeatother

\renewcommand\thesection{\Roman{section}}
\renewcommand\thesubsection{\thesection.\arabic{subsection}}
"""


# ══════════════════════════════════════════════════════════════════════
# GÉNÉRATION DU LATEX COMPLET
# ══════════════════════════════════════════════════════════════════════

def generer_latex_complet(cer) -> str:
    """
    Génère le document LaTeX complet conforme au PDF exemple :
    CER_MAWAMBA_TOWA_Maëva_X2028.pdf
    """
    from datetime import datetime

    plan = cer.get_plan_action()

    date_str = (
        cer.created_at.strftime('%d/%m/%Y')
        if cer.created_at else datetime.now().strftime('%d/%m/%Y')
    )

    def md2tex(text):
        return markdown_to_latex(text) if text else ''

    # ── Titre : décomposer "Prosit NX — Thème" sur 2 lignes ───────────
    titre_raw = cer.titre_prosit or 'CER'
    m = re.match(
        r'^(Prosit\s+N[°o]?\s*\d+\s*[—\-–]+\s*.+?)\s*[—\-–]+\s*(.+)$',
        titre_raw, re.IGNORECASE
    )
    if m:
        t1 = _esc(m.group(1).strip())
        t2 = _esc(m.group(2).strip())
        titre_tikz_lines = (
            f"      {{\\Huge \\textbf{{\\underline{{{t1}}}}}}} \\\\[0.4cm]\n"
            f"      {{\\Huge \\textbf{{\\underline{{{t2}}}}}}} \\\\[0.6cm]\n"
        )
        theme_court = _esc(m.group(2).strip()[:38])
    else:
        t1 = _esc(titre_raw)
        titre_tikz_lines = (
            f"      {{\\Huge \\textbf{{\\underline{{{t1}}}}}}} \\\\[0.6cm]\n"
        )
        theme_court = _esc(titre_raw[:38])

    # ── Infos page de garde ───────────────────────────────────────────
    etudiant_esc  = _esc(cer.etudiant  or '')
    pilote_esc    = _esc(cer.pilote    or '')
    copilote_esc  = _esc(cer.copilote  or '')
    promotion_esc = _esc(cer.promotion or '')

    pilote_line   = f"  {{\\Large Pilote :{pilote_esc} \\par}}\n"   if cer.pilote   else ""
    copilote_line = f"  {{\\Large Co-pilote : {copilote_esc} \\par}}\n" if cer.copilote else ""
    promo_line    = f"  {{\\large {promotion_esc} \\par}}\n"         if cer.promotion else ""

    # ── Besoins / Contraintes → liste LaTeX ───────────────────────────
    def to_itemize_rouge(text: str) -> str:
        """Convertit un texte (une ligne = un item) en itemize rouge."""
        items = [
            l.lstrip('-•* \t').strip()
            for l in (text or '').splitlines()
            if l.strip() and not l.strip().startswith('#')
        ]
        if not items:
            return ''
        lines = [
            r'\begin{itemize}[leftmargin=1.5cm,'
            r' label=\textcolor{maincolor}{$\bullet$}]'
        ]
        for it in items:
            lines.append(r'  \item ' + _esc(it))
        lines.append(r'\end{itemize}')
        return '\n'.join(lines)

    # ── Plan d'action ─────────────────────────────────────────────────
    plan_items = '\n'.join(
        f'  \\item {_esc(p)}' for p in plan
    )

    # ── Réalisation ───────────────────────────────────────────────────
    realisation_sections = ""
    if cer.realisation:
        try:
            real = json.loads(cer.realisation)
            for i, etape in enumerate(plan):
                contenu = real.get(str(i), '')
                realisation_sections += (
                    "\n% " + "─" * 60 + "\n"
                    f"\\subsection{{{_esc(etape)}}}\n"
                    "% " + "─" * 60 + "\n\n"
                    + md2tex(contenu) + "\n\n"
                )
        except Exception:
            realisation_sections = md2tex(cer.realisation)

    # ── Validation → sous-sections ────────────────────────────────────
    # Le md2tex gère déjà les ### comme \subsubsection
    validation_tex = md2tex(cer.validation or '')

    # ── Bibliographie → \begin{thebibliography} ───────────────────────
    def build_biblio(text: str) -> str:
        if not text:
            return (
                r'\begin{thebibliography}{99}' + '\n'
                r'\bibitem{cormen} T.~H. Cormen, C.~E. Leiserson, R.~L. Rivest'
                r' et C.~Stein, \textit{Introduction \`{a} l\'algorithmique},'
                r' 3\`{e}me \'ed., Dunod, 2010.' + '\n'
                r'\end{thebibliography}'
            )
        items = re.findall(
            r'\[(\d+)\]\s+(.+?)(?=\n\s*\[\d+\]|\Z)',
            text, re.DOTALL
        )
        if not items:
            # Fallback : liste à puces → thebibliography auto-numérotée
            lignes = [l.lstrip('-•* ').strip() for l in text.splitlines() if l.strip()]
            out = [r'\begin{thebibliography}{99}']
            for j, l in enumerate(lignes, 1):
                l = re.sub(r'\*(.+?)\*', r'\\textit{\1}', l)
                out.append(f'\\bibitem{{ref{j}}} {l}')
            out.append(r'\end{thebibliography}')
            return '\n'.join(out)
        out = [r'\begin{thebibliography}{99}', '']
        for num, content in items:
            content = content.strip().replace('\n', ' ')
            content = re.sub(r'\*(.+?)\*', r'\\textit{\1}', content)
            out.append(f'\\bibitem{{ref{num}}}\n{content}\n')
        out.append(r'\end{thebibliography}')
        return '\n'.join(out)

    biblio_tex = build_biblio(cer.references or '')

    # ══════════════════════════════════════════════════════════════════
    # ASSEMBLAGE DU DOCUMENT
    # ══════════════════════════════════════════════════════════════════

    doc = PREAMBLE

    # En-têtes fancyhdr (dépend du titre → après PREAMBLE)
    doc += f"""
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\fancyhead[L]{{\\textcolor{{maincolor}}{{\\textbf{{UCAC-ICAM}}}}}}
\\fancyhead[R]{{\\textcolor{{maincolor}}{{\\textbf{{CER -- {theme_court}}}}}}}
\\fancyfoot[C]{{\\textcolor{{sectiongray}}{{\\thepage}}}}
\\renewcommand{{\\headrulewidth}}{{1.5pt}}
\\renewcommand{{\\headrule}}{{%
  \\hbox to\\headwidth{{\\color{{maincolor}}\\leaders\\hrule height \\headrulewidth\\hfill}}}}

\\begin{{document}}

% ============================================================
%                     PAGE DE GARDE
% ============================================================
\\begin{{titlepage}}
  \\pagestyle{{empty}}
  % Cadre rouge épais tout autour (identique au PDF exemple)
  \\begin{{tikzpicture}}[remember picture, overlay]
    \\draw[line width=24pt, color=maincolor]
      (current page.north west) rectangle (current page.south east);
  \\end{{tikzpicture}}
  \\centering
  \\vspace{{1cm}}

  % ── Logo ──────────────────────────────────────────────────────────
  % Utilise logo.jpg si présent dans le même dossier que le .tex
  % Sinon, bloc TikZ de remplacement (commenter/décommenter selon le cas)
  %\\includegraphics[width=5cm]{{logo.jpg}}
  \\begin{{tikzpicture}}
    \\fill[maincolor, rounded corners=6pt] (0,0) rectangle (5.5,2.2);
    \\fill[white, rounded corners=3pt] (0.15,0.15) rectangle (5.35,2.05);
    \\node[font=\\Large\\bfseries, text=maincolor] at (2.75,1.6) {{UCAC-ICAM}};
    \\node[font=\\footnotesize, text=sectiongray] at (2.75,1.0)
      {{Universit\\\'{{e}} Catholique d'Afrique Centrale}};
    \\node[font=\\footnotesize, text=sectiongray] at (2.75,0.55)
      {{Institut Catholique d'Arts et M\\\'{{e}}tiers}};
    \\draw[maincolor, line width=0.6pt] (0.9,1.3) -- (4.6,1.3);
  \\end{{tikzpicture}}

  \\vspace{{1.5cm}}

  % ── Titre dans encadré TikZ arrondi (identique au PDF exemple) ────
  \\begin{{tikzpicture}}
    \\node[draw=maincolor, line width=1.5pt, rounded corners=5pt,
          inner sep=16pt, align=center] {{
{titre_tikz_lines}      {{\\Huge \\textbf{{Cahier d\\'\\\'{{E}}tude}}}} \\\\[0.3cm]
      {{\\Huge \\textbf{{et de Recherche}}}}
    }};
  \\end{{tikzpicture}}

  \\vfill

  % ── Informations étudiant / encadrants ────────────────────────────
  {{\\Large \\textbf{{{etudiant_esc}}} \\par}}
  \\vspace{{0.4cm}}
  {{\\large {date_str} \\par}}
  \\vspace{{0.6cm}}
{pilote_line}{copilote_line}{promo_line}\\end{{titlepage}}

% ============================================================
%                  TABLE DES MATIÈRES
% ============================================================
{{
\\renewcommand{{\\baselinestretch}}{{2.0}}
\\tableofcontents
}}
\\newpage

% ============================================================
\\section{{Analyse du contexte}}
% ============================================================

{md2tex(cer.contexte)}

% ============================================================
\\section{{Analyse des besoins}}
% ============================================================

\\subsection*{{Besoins}}
{to_itemize_rouge(cer.besoins)}

\\subsection*{{Contraintes}}
{to_itemize_rouge(cer.contraintes)}

\\subsection*{{Probl\\\'{{e}}matique}}

\\begin{{mdframed}}[backgroundcolor=lightblue, linecolor=maincolor, linewidth=2pt,
  innerleftmargin=10pt, innerrightmargin=10pt,
  innertopmargin=8pt, innerbottommargin=8pt]
\\textit{{{_esc(cer.problematique or '')}}}
\\end{{mdframed}}

% ============================================================
\\section{{G\\\'{{e}}n\\\'{{e}}ralisation}}
% ============================================================

\\begin{{center}}
  \\large\\textbf{{\\textcolor{{maincolor}}{{{_esc(titre_raw)}}}}}
\\end{{center}}

Ce prosit s\\'inscrit dans un domaine fondamental de l\\'informatique et des
math\\\'{{e}}matiques appliqu\\\'{{e}}es. Les notions \\\'{{e}}tudi\\\'{{e}}es ont
une port\\\'{{e}}e th\\\'{{e}}orique et pratique d\\\'{{e}}passant le seul cadre de ce prosit.

% ============================================================
\\section{{Plan d\\'action}}
% ============================================================

\\begin{{enumerate}}[leftmargin=1.5cm, label=\\textcolor{{maincolor}}{{\\textbf{{\\arabic*.}}}}]
{plan_items}
\\end{{enumerate}}

% ============================================================
\\section{{R\\\'{{e}}alisation du plan d\\'action}}
% ============================================================

{realisation_sections}

% ============================================================
\\section{{Validation des pistes de solutions}}
% ============================================================

{validation_tex}

% ============================================================
\\section{{Conclusion et retours sur les objectifs}}
% ============================================================

{md2tex(cer.conclusion or '')}

% ============================================================
\\section{{Bilan critique du travail effectu\\\'{{e}}}}
% ============================================================

{md2tex(cer.bilan or '')}

% ============================================================
%                 BIBLIOGRAPHIE
% ============================================================

{biblio_tex}

\\end{{document}}
"""
    return doc