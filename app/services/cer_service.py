import os
import json
import re
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ══════════════════════════════════════════════════════════════════════
# FONCTIONS DE NETTOYAGE LATEX  (au niveau module, pas dans une fonction)
# ══════════════════════════════════════════════════════════════════════

def nettoyer_texte_latex(text: str) -> str:
    """Nettoie le texte généré par l'IA pour éviter les erreurs LaTeX."""
    if not text:
        return ""
    text = text.replace('\u2019', "'").replace('\u2018', "`")
    text = text.replace('\u201c', "``").replace('\u201d', "''")
    text = text.replace('\u2013', "--").replace('\u2014', "---")
    text = text.replace('\uf0d8', '')
    text = re.sub(r'(\d+)(?<!\\)%', r'\1\\%', text)
    return text


def nettoyer_code_listing(code: str) -> str:
    """Nettoie le code dans lstlisting — les accents > U+00FF → ASCII."""
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
    """Génère une section du CER via Groq. Retourne du Markdown riche."""

    plan_str = "\n".join(
        [f"{i+1}. {p}" for i, p in enumerate(plan_action)]
    )

    source_ctx = f"""
Documents de référence (corbeille / workshop) :
---
{contenu_source[:4000]}
---
""" if contenu_source else ""

    if section == "realisation_etape":
        prompt = f"""Tu es un expert académique et tu rédiges un Cahier d'Étude et de Recherche
(CER) pour un étudiant de l'UCAC-ICAM en ingénierie informatique.

CONTEXTE DU PROSIT : {titre_prosit}

Situation déclenchante :
{contexte}

Besoins identifiés :
{besoins}

Contraintes :
{contraintes}

Problématique : {problematique}

Plan d'action complet :
{plan_str}

{source_ctx}

Tu dois rédiger le contenu détaillé de l'ÉTAPE {etape_index} du plan d'action :
"{etape_label}"

RÈGLES ABSOLUES :
1. Rédige un contenu académique riche, détaillé, d'au moins 400 mots pour cette étape
2. Structure le contenu avec des sous-sections (###) si nécessaire
3. Inclus OBLIGATOIREMENT :
   - Des définitions précises des concepts clés
   - Des exemples concrets liés au contexte du prosit
   - Des tableaux comparatifs si pertinent (en Markdown)
   - Du pseudocode si l'étape implique des algorithmes
   - Des formules mathématiques en notation LaTeX ($...$) si pertinent
   - Des explications step-by-step pour les algorithmes
4. Utilise le contexte du prosit pour illustrer les concepts
5. Écris en français académique, clair et précis
6. Utilise le format Markdown avec **gras**, `code`, tableaux, listes

Génère uniquement le contenu de cette étape, sans en-tête ni introduction générale.
"""

    elif section == "validation":
        prompt = f"""Tu es un expert académique rédigeant un CER pour l'UCAC-ICAM.

PROSIT : {titre_prosit}
Problématique : {problematique}

Plan d'action :
{plan_str}

{source_ctx}

Rédige la section "Validation des pistes de solutions" du CER.

Cette section doit :
1. Répondre à 4-5 questions de généralisation/validation liées au prosit
2. Chaque question-réponse fait 150-200 mots
3. Format : **Question X : [Question] ?** suivi de la réponse argumentée
4. Relier chaque réponse au contexte du prosit
5. Conclure chaque validation avec une mention Validée/Partiellement validée/Infirmée

Génère uniquement le contenu de la section validation.
"""

    elif section == "conclusion":
        prompt = f"""Tu es un expert académique rédigeant un CER pour l'UCAC-ICAM.

PROSIT : {titre_prosit}
Problématique : {problematique}
Plan d'action :
{plan_str}

Rédige la section "Conclusion et retours sur les objectifs" du CER.

La conclusion doit :
1. Rappeler brièvement la problématique
2. Faire un bilan point par point de chaque étape du plan d'action
   avec statut : Atteint / Partiellement atteint / Non atteint
3. Synthétiser la solution retenue pour répondre à la problématique
4. Minimum 250 mots, style académique

Génère uniquement le contenu de la conclusion.
"""

    elif section == "bilan":
        prompt = f"""Tu es un expert académique rédigeant un CER pour l'UCAC-ICAM.

PROSIT : {titre_prosit}
Plan d'action :
{plan_str}

Rédige la section "Bilan critique du travail effectué" du CER.

Le bilan doit :
1. Analyser les points forts du travail réalisé
2. Identifier les limites et difficultés rencontrées
3. Proposer des améliorations et perspectives
4. Mentionner les notions complémentaires à approfondir
5. Minimum 200 mots, style réflexif et critique

Génère uniquement le contenu du bilan critique.
"""

    elif section == "synthese":
        prompt = f"""Tu es un expert académique rédigeant un CER pour l'UCAC-ICAM.

PROSIT : {titre_prosit}
Plan d'action :
{plan_str}

Rédige la section "Synthèse des résultats obtenus" du CER.

La synthèse doit :
1. Résumer les résultats clés de chaque étape du plan d'action
2. Utiliser des bullet points structurés
3. Inclure les données chiffrées/comparatives importantes découvertes
4. Mettre en valeur les résultats les plus importants en **gras**
5. Minimum 200 mots

Génère uniquement la synthèse des résultats.
"""

    elif section == "references":
        prompt = f"""Tu es un expert académique rédigeant un CER pour l'UCAC-ICAM.

PROSIT : {titre_prosit}
Thèmes du plan d'action :
{plan_str}

Génère une bibliographie académique réaliste et pertinente pour ce CER.

La bibliographie doit :
1. Contenir 6-10 références pertinentes
2. Inclure : livres académiques, articles, documentation officielle, cours en ligne
3. Couvrir les thèmes principaux du plan d'action
4. Respecter le format : Auteur, *Titre*, Éditeur/URL, Année
5. Inclure des URLs réelles connues (MIT Press, OpenClassrooms, docs officiels...)

Format Markdown :
- [1] Auteur, *Titre*, ...
- [2] ...

Génère uniquement la bibliographie.
"""

    else:
        return ""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=3000,
    )

    return response.choices[0].message.content


# ══════════════════════════════════════════════════════════════════════
# CONVERSION MARKDOWN → LATEX
# ══════════════════════════════════════════════════════════════════════

def markdown_to_latex(md_text: str) -> str:
    """Convertit du Markdown enrichi en LaTeX propre."""
    if not md_text:
        return ''

    # Nettoyage préalable
    md_text = nettoyer_texte_latex(md_text)

    lines      = md_text.split('\n')
    result     = []
    in_code    = False
    in_item    = False
    in_enum    = False
    in_table   = False
    table_buf  = []

    def process_inline(text):
        """Formate le texte inline : gras, italique, code, liens."""
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
        rows = [r for r in table_buf
                if not re.match(r'^\|[-\s|:]+\|$', r.strip())]
        if not rows:
            table_buf = []
            in_table  = False
            return []

        first_row = rows[0]
        cols      = [c.strip() for c in first_row.strip('|').split('|')]
        nb_cols   = len(cols)
        col_spec  = '|' + '|'.join(['l'] * nb_cols) + '|'

        out = [
            r'\begin{center}',
            r'\begin{tabular}{' + col_spec + '}',
            r'\hline',
        ]
        for i, row in enumerate(rows):
            cells = [c.strip() for c in row.strip('|').split('|')]
            while len(cells) < nb_cols:
                cells.append('')
            if i == 0:
                row_str = ' & '.join(
                    r'\textbf{' + process_inline(c) + '}'
                    for c in cells[:nb_cols]
                )
            else:
                row_str = ' & '.join(
                    process_inline(c) for c in cells[:nb_cols]
                )
            out.append(row_str + r' \\')
            out.append(r'\hline')

        out += [r'\end{tabular}', r'\end{center}', '']
        table_buf = []
        in_table  = False
        return out

    for line in lines:
        stripped = line.strip()

        # ── Blocs de code ─────────────────────────────────────────────
        if stripped.startswith('```'):
            result.extend(close_lists())
            if in_table:
                result.extend(flush_table())
            if in_code:
                result.append(r'\end{lstlisting}')
                result.append('')
                in_code = False
            else:
                lang     = stripped[3:].strip().lower()
                lang_map = {
                    'python': 'Python', 'java': 'Java',
                    'c': 'C', 'cpp': 'C++', 'js': 'JavaScript',
                    'bash': 'bash', 'sql': 'SQL', '': 'Python',
                }
                detected = lang_map.get(lang, 'Python')
                result.append(
                    r'\begin{lstlisting}[language=' + detected + ']'
                )
                in_code = True
            continue

        if in_code:
            result.append(nettoyer_code_listing(line))
            continue

        # ── Tableaux ──────────────────────────────────────────────────
        if stripped.startswith('|'):
            result.extend(close_lists())
            in_table = True
            table_buf.append(stripped)
            continue
        elif in_table:
            result.extend(flush_table())

        # ── Ligne vide ────────────────────────────────────────────────
        if not stripped:
            result.extend(close_lists())
            result.append('')
            continue

        # ── Titres ────────────────────────────────────────────────────
        if stripped.startswith('#### '):
            result.extend(close_lists())
            result.append(r'\paragraph{' + process_inline(stripped[5:]) + '}')
            continue
        if stripped.startswith('### '):
            result.extend(close_lists())
            result.append(r'\subsubsection{' + process_inline(stripped[4:]) + '}')
            continue
        if stripped.startswith('## '):
            result.extend(close_lists())
            result.append(r'\subsection{' + process_inline(stripped[3:]) + '}')
            continue
        if stripped.startswith('# '):
            result.extend(close_lists())
            result.append(r'\section{' + process_inline(stripped[2:]) + '}')
            continue

        # ── Listes non ordonnées ──────────────────────────────────────
        if re.match(r'^[-*+] ', stripped):
            if not in_item:
                result.extend(close_lists())
                result.append(r'\begin{itemize}')
                in_item = True
            result.append(r'  \item ' + process_inline(stripped[2:]))
            continue

        # ── Listes ordonnées ──────────────────────────────────────────
        if re.match(r'^\d+\. ', stripped):
            if not in_enum:
                result.extend(close_lists())
                result.append(r'\begin{enumerate}')
                in_enum = True
            content = re.sub(r'^\d+\.\s+', '', stripped)
            result.append(r'  \item ' + process_inline(content))
            continue

        # ── Paragraphe normal ─────────────────────────────────────────
        result.extend(close_lists())
        result.append(process_inline(stripped))
        result.append('')

    # Fermer ce qui reste ouvert
    result.extend(close_lists())
    if in_table:
        result.extend(flush_table())
    if in_code:
        result.append(r'\end{lstlisting}')

    # Vérifier l'équilibre itemize/enumerate
    text = '\n'.join(result)
    for env in ['itemize', 'enumerate']:
        diff = text.count(f'\\begin{{{env}}}') - text.count(f'\\end{{{env}}}')
        if diff > 0:
            text += f'\n\\end{{{env}}}' * diff

    return text


# ══════════════════════════════════════════════════════════════════════
# GÉNÉRATION DU LATEX COMPLET
# ══════════════════════════════════════════════════════════════════════

def generer_latex_complet(cer) -> str:
    """Génère le document LaTeX complet du CER."""
    from datetime import datetime

    plan       = cer.get_plan_action()
    plan_items = '\n'.join([f'    \\item {p}' for p in plan])

    def md2tex(text):
        return markdown_to_latex(text) if text else ''

    def esc(s):
        """Échappe les caractères spéciaux LaTeX dans les métadonnées."""
        if not s:
            return ''
        return (s.replace('%', '\\%')
                 .replace('&', '\\&')
                 .replace('_', '\\_'))

    # Sections de réalisation
    realisation_sections = ""
    if cer.realisation:
        try:
            real = json.loads(cer.realisation)
            for i, etape in enumerate(plan):
                contenu = real.get(str(i), '')
                etape_esc = esc(etape)
                realisation_sections += (
                    f"\n\\subsection{{{etape_esc}}}\n\n"
                    f"{md2tex(contenu)}\n\n"
                )
        except Exception:
            realisation_sections = md2tex(cer.realisation)

    date_str = (
        cer.created_at.strftime('%d/%m/%Y')
        if cer.created_at else datetime.now().strftime('%d/%m/%Y')
    )

    # Infos page de garde
    titre_esc   = esc(cer.titre_prosit or '')
    etudiant    = esc(cer.etudiant or '')
    pilote_line = (f"    {{\\Large Pilote : {esc(cer.pilote)} \\par}}\n"
                   if cer.pilote else "")
    copilote_line = (f"    {{\\Large Co-pilote : {esc(cer.copilote)} \\par}}\n"
                     if cer.copilote else "")
    promo_line  = (f"    {{\\large {esc(cer.promotion)} \\par}}\n"
                   if cer.promotion else "")

    latex = (
        r"""\documentclass[12pt]{report}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[french]{babel}
\usepackage{graphicx}
\usepackage[a4paper, margin=2.5cm]{geometry}
\usepackage[table]{xcolor}
\usepackage{longtable}
\usepackage{array}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{listings}
\usepackage{enumitem}
\usepackage{float}
\usepackage{caption}
\usepackage{fancyhdr}
\usepackage[hyphens]{url}
\usepackage[colorlinks=true, linkcolor=black, urlcolor=blue, citecolor=black]{hyperref}

\renewcommand\thesection{\Roman{section}}
\renewcommand\thesubsection{\thesection.\arabic{subsection}}

\definecolor{maincolor}{RGB}{180,0,0}
\definecolor{lightgray}{RGB}{240,240,240}
\definecolor{codeblue}{RGB}{0,0,180}

\lstset{
  basicstyle=\small\ttfamily,
  backgroundcolor=\color{lightgray},
  frame=single,
  breaklines=true,
  language=Python,
  keywordstyle=\color{codeblue}\bfseries,
  commentstyle=\color{gray}\itshape,
  showstringspaces=false,
  numbers=left,
  numberstyle=\tiny\color{gray},
  stepnumber=1,
  tabsize=2,
  extendedchars=true,
  literate=
    {é}{{\'{e}}}1 {è}{{\`{e}}}1 {ê}{{\^{e}}}1 {ë}{{\"{e}}}1
    {à}{{\`{a}}}1 {â}{{\^{a}}}1 {ä}{{\"{a}}}1
    {ù}{{\`{u}}}1 {û}{{\^{u}}}1 {ü}{{\"{u}}}1
    {î}{{\^{i}}}1 {ï}{{\"{i}}}1
    {ô}{{\^{o}}}1 {ö}{{\"{o}}}1
    {ç}{{\c{c}}}1
    {É}{{\'{E}}}1 {È}{{\`{E}}}1 {Ê}{{\^{E}}}1
    {À}{{\`{A}}}1 {Â}{{\^{A}}}1
    {Î}{{\^{I}}}1 {Ô}{{\^{O}}}1 {Ù}{{\`{U}}}1
    {Ç}{{\c{C}}}1 {œ}{{\oe}}1 {Œ}{{\OE}}1
    {°}{{$^{\circ}$}}1 {'}{{'}}1,
}

\urlstyle{same}
\sloppy

\begin{document}

% ── PAGE DE GARDE ─────────────────────────────────────────────────────────────
\begin{titlepage}
    \pagestyle{empty}
    \centering
    \vspace*{1.5cm}

    {\color{maincolor}\rule{\textwidth}{4pt}}\\[0.8cm]

    {\Huge\bfseries\color{maincolor} Cahier d'\'Etude et de Recherche}\\[1cm]

    \colorbox{maincolor!10}{%
        \parbox{0.86\textwidth}{\centering\vspace{0.5cm}
            {\Large\bfseries\color{maincolor} """
        + titre_esc
        + r"""}\\[0.4cm]
        \vspace{0.4cm}}%
    }

    \vfill

    \begin{tabular}{rl}
"""
        + (f"        \\textbf{{\\'{{'}}Etudiant :}} & {etudiant} \\\\[0.3cm]\n"
           if etudiant else "")
        + (f"        \\textbf{{Pilote :}} & {esc(cer.pilote)} \\\\[0.3cm]\n"
           if cer.pilote else "")
        + (f"        \\textbf{{Co-pilote :}} & {esc(cer.copilote)} \\\\[0.3cm]\n"
           if cer.copilote else "")
        + (f"        \\textbf{{Promotion :}} & {esc(cer.promotion)} \\\\[0.3cm]\n"
           if cer.promotion else "")
        + f"        \\textbf{{Date :}} & {date_str} \\\\\n"
        + r"""    \end{tabular}

    \vspace{1.5cm}
    {\color{maincolor}\rule{\textwidth}{4pt}}
\end{titlepage}

% ── TABLE DES MATIÈRES ────────────────────────────────────────────────────────
\tableofcontents
\newpage

\setlength{\parskip}{0.5em}
\setlength{\parindent}{0pt}

% ── SECTIONS ──────────────────────────────────────────────────────────────────
\section{Analyse du contexte}

"""
        + md2tex(cer.contexte)
        + r"""

\section{Analyse des besoins}

\subsection*{Besoins}

"""
        + md2tex(cer.besoins)
        + r"""

\subsection*{Contraintes}

"""
        + md2tex(cer.contraintes or '')
        + r"""

\section{D\'efinition de la probl\'ematique}

"""
        + md2tex(cer.problematique)
        + r"""

\section{Plan d'action}

\begin{enumerate}[leftmargin=*, label=\arabic*.]
"""
        + plan_items
        + r"""
\end{enumerate}

\section{R\'ealisation du plan d'action}

"""
        + realisation_sections
        + r"""

\section{Validation des pistes de solutions}

"""
        + md2tex(cer.validation or '')
        + r"""

\section{Conclusion et retours sur les objectifs}

"""
        + md2tex(cer.conclusion or '')
        + r"""

\section{Bilan critique du travail effectu\'e}

"""
        + md2tex(cer.bilan or '')
        + r"""

\section{Synth\`ese des r\'esultats obtenus}

"""
        + md2tex(cer.synthese or '')
        + r"""

\section{R\'ef\'erences bibliographiques}

"""
        + md2tex(cer.references or '')
        + r"""

\end{document}
"""
    )

    return latex