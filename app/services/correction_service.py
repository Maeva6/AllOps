# app/services/correction_service.py
import os
import json
import re
import subprocess
import tempfile
from groq import Groq

_client = None

def get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
    return _client

TYPES_DOC = {
    "tp":        "Travail Pratique (TP)",
    "td":        "Travail Dirigé (TD)",
    "corbeille": "Corbeille d'exercices",
    "workshop":  "Workshop / Atelier",
    "exam":      "Examen / Devoir surveillé",
    "autre":     "Document académique",
}


# ══════════════════════════════════════════════════════════════════════
# REPAIR JSON — Gère les réponses IA mal formatées
# ══════════════════════════════════════════════════════════════════════

def reparer_json(raw: str) -> str:
    """
    Tente de réparer un JSON mal formé retourné par l'IA.
    Stratégies appliquées dans l'ordre :
    1. Nettoyer les backticks markdown
    2. Extraire le tableau JSON
    3. Corriger les guillemets non échappés dans les valeurs
    4. Tronquer à la dernière entrée valide
    """
    # Étape 1 : nettoyer le markdown
    raw = re.sub(r'^```(?:json)?\s*', '', raw.strip())
    raw = re.sub(r'\s*```$', '', raw)
    raw = raw.strip()

    # Étape 2 : extraire le tableau []
    m = re.search(r'\[', raw)
    if m:
        raw = raw[m.start():]

    # Essai direct
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Étape 3 : corriger les guillemets non échappés dans les valeurs de string
    # Remplacer les " qui ne sont pas des délimiteurs JSON
    # Stratégie : parser caractère par caractère
    fixed = _fix_json_strings(raw)
    try:
        return json.loads(fixed)
    except Exception:
        pass

    # Étape 4 : tronquer à la dernière entrée complète
    truncated = _truncate_to_valid(raw)
    try:
        return json.loads(truncated)
    except Exception:
        pass

    # Étape 5 : extraction manuelle des objets
    return _extract_objects_manually(raw)


def _fix_json_strings(text: str) -> str:
    """Corrige les guillemets non échappés dans les valeurs JSON."""
    result = []
    i = 0
    in_string = False
    prev_char = ''

    while i < len(text):
        ch = text[i]

        if ch == '"' and prev_char != '\\':
            if in_string:
                # Fin de string : vérifier le contexte
                # Si le prochain char non-espace est : , } ]
                j = i + 1
                while j < len(text) and text[j] in ' \t\n\r':
                    j += 1
                next_meaningful = text[j] if j < len(text) else ''
                if next_meaningful in ':,}]"':
                    in_string = False
                    result.append('"')
                else:
                    # Guillemet dans la valeur → échapper
                    result.append('\\"')
                    i += 1
                    prev_char = '"'
                    continue
            else:
                in_string = True
                result.append('"')
        elif ch == '\n' and in_string:
            result.append('\\n')
        elif ch == '\r' and in_string:
            i += 1
            prev_char = ch
            continue
        elif ch == '\t' and in_string:
            result.append('\\t')
        else:
            result.append(ch)

        prev_char = ch
        i += 1

    return ''.join(result)


def _truncate_to_valid(text: str) -> str:
    """Tronque à la dernière accolade fermante valide."""
    # Trouver toutes les positions de }
    # et essayer de fermer le tableau à chaque }
    depth = 0
    last_valid = 0

    for i, ch in enumerate(text):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                last_valid = i + 1

    if last_valid > 0:
        candidate = text[:last_valid] + ']'
        # Nettoyer la virgule finale avant ]
        candidate = re.sub(r',\s*\]', ']', candidate)
        return candidate

    return text


def _extract_objects_manually(text: str) -> list:
    """Extraction manuelle des champs connus."""
    items = []
    # Trouver les blocs { ... }
    pattern = re.compile(r'\{[^{}]*\}', re.DOTALL)

    for m in pattern.finditer(text):
        block = m.group(0)
        item = {}

        for field in ['numero', 'enonce', 'reponse', 'explication',
                      'conseils', 'difficulte']:
            fm = re.search(
                rf'"{field}"\s*:\s*"((?:[^"\\]|\\.)*)"',
                block, re.DOTALL
            )
            if fm:
                item[field] = fm.group(1).replace('\\n', '\n')

        # Notions (liste)
        nm = re.search(r'"notions"\s*:\s*\[(.*?)\]', block, re.DOTALL)
        if nm:
            notions = re.findall(r'"([^"]*)"', nm.group(1))
            item['notions'] = notions

        if item.get('enonce') or item.get('reponse'):
            items.append(item)

    return items


# ══════════════════════════════════════════════════════════════════════
# GÉNÉRATION DE LA CORRECTION
# ══════════════════════════════════════════════════════════════════════

def generer_correction(contenu: str, titre: str, type_doc: str) -> list:
    """Génère une correction détaillée via Groq."""
    type_label = TYPES_DOC.get(type_doc, "Document académique")

    prompt = f"""Tu es un professeur expert qui corrige des documents académiques.

Voici un {type_label} intitulé "{titre}" :

---
{contenu[:7000]}
---

Pour CHAQUE exercice/question identifié :
1. Identifie le numéro et l'énoncé
2. Donne la réponse complète et correcte
3. Explique le raisonnement étape par étape
4. Liste les notions clés (max 4)
5. Donne un conseil pour éviter les erreurs classiques
6. Évalue la difficulté : facile, moyen ou difficile

RÈGLES STRICTES pour le JSON :
- Réponds UNIQUEMENT avec un tableau JSON valide
- Aucun texte avant ou après, aucune balise markdown
- Dans les valeurs string : utilise \\n pour les sauts de ligne
- N'utilise JAMAIS de guillemets droits " à l'intérieur des valeurs — utilise ' à la place
- Échappe tous les caractères spéciaux correctement

Format EXACT (respecte-le scrupuleusement) :
[
  {{
    "numero": "Exercice 1",
    "enonce": "Texte de l enonce sans guillemets",
    "reponse": "La reponse complete",
    "explication": "Explication detaillee etape par etape",
    "notions": ["notion1", "notion2"],
    "conseils": "Conseil pratique",
    "difficulte": "moyen"
  }}
]"""

    response = get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Tu es un correcteur académique. "
                    "Réponds UNIQUEMENT avec du JSON valide. "
                    "Dans les strings JSON, n'utilise JAMAIS de guillemets droits — "
                    "utilise des apostrophes à la place. "
                    "Utilise \\n pour les sauts de ligne dans les valeurs."
                )
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=4000,
    )

    raw = response.choices[0].message.content.strip()

    # Parsing robuste
    result = reparer_json(raw)

    if isinstance(result, list):
        corrections = result
    else:
        corrections = []

    # Valider et normaliser chaque item
    cleaned = []
    for i, item in enumerate(corrections):
        if not isinstance(item, dict):
            continue
        if not (item.get('enonce') or item.get('reponse')):
            continue
        cleaned.append({
            'numero':      str(item.get('numero', f'Exercice {i+1}')),
            'enonce':      str(item.get('enonce', '')),
            'reponse':     str(item.get('reponse', '')),
            'explication': str(item.get('explication', '')),
            'notions':     item.get('notions', []) if isinstance(
                               item.get('notions'), list) else [],
            'conseils':    str(item.get('conseils', '')),
            'difficulte':  str(item.get('difficulte', 'moyen')),
        })

    return cleaned


def generer_resume_notions(corrections: list, titre: str) -> str:
    """Génère un résumé pédagogique des notions abordées."""
    if not corrections:
        return ""

    toutes_notions = []
    for c in corrections:
        toutes_notions.extend(c.get('notions', []))
    notions_uniques = list(set(toutes_notions))[:20]

    if not notions_uniques:
        return ""

    prompt = f"""Tu es un professeur. Voici les notions abordées dans "{titre}" :
{', '.join(notions_uniques)}

Génère un paragraphe de synthèse pédagogique (150-200 mots) qui :
1. Relie ces notions entre elles
2. Explique leur importance pratique
3. Suggère comment les approfondir

Réponds uniquement avec le texte du paragraphe.
"""
    response = get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=400,
    )
    return response.choices[0].message.content.strip()


# ══════════════════════════════════════════════════════════════════════
# GÉNÉRATION DU DOCUMENT CORRIGÉ — LaTeX
# ══════════════════════════════════════════════════════════════════════

def _esc_tex(text: str) -> str:
    """Échappe les caractères spéciaux LaTeX."""
    if not text:
        return ''
    replacements = [
        ('\\', '\\textbackslash{}'),
        ('&',  '\\&'),
        ('%',  '\\%'),
        ('$',  '\\$'),
        ('#',  '\\#'),
        ('_',  '\\_'),
        ('{',  '\\{'),
        ('}',  '\\}'),
        ('~',  '\\textasciitilde{}'),
        ('^',  '\\textasciicircum{}'),
    ]
    for src, dst in replacements:
        text = text.replace(src, dst)
    return text


def _md_to_tex_simple(text: str) -> str:
    """Conversion Markdown simple → LaTeX pour le document corrigé."""
    if not text:
        return ''

    # Échapper d'abord les caractères spéciaux
    # (sauf les accents UTF-8 qui passent par inputenc)
    text = text.replace('%', '\\%')
    text = text.replace('&', '\\&')
    text = text.replace('$', '\\$').replace('\\$\\$', '$$')  # garder les formules
    text = text.replace('#', '\\#')
    text = text.replace('_', '\\_')

    # Gras et italique
    text = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', text)
    text = re.sub(r'\*(.+?)\*',     r'\\textit{\1}', text)
    text = re.sub(r'`([^`]+)`',     r'\\texttt{\1}', text)

    # Apostrophes
    text = text.replace('\u2019', "'").replace('\u2018', "`")

    # Sauts de ligne
    text = text.replace('\\n', '\n')

    # Listes → itemize
    lines = text.split('\n')
    result = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if re.match(r'^[-*] ', stripped):
            if not in_list:
                result.append('\\begin{itemize}')
                in_list = True
            result.append(f'  \\item {stripped[2:]}')
        elif re.match(r'^\d+\. ', stripped):
            if not in_list:
                result.append('\\begin{enumerate}')
                in_list = True
            result.append(f'  \\item {re.sub(r"^\d+\.\s+", "", stripped)}')
        else:
            if in_list:
                result.append('\\end{itemize}')
                in_list = False
            result.append(stripped)
    if in_list:
        result.append('\\end{itemize}')

    return '\n'.join(result)


def generer_latex_correction(corrections: list, titre: str,
                              type_doc: str, resume: str) -> str:
    """Génère le fichier LaTeX du document corrigé."""
    type_label = TYPES_DOC.get(type_doc, "Document académique")

    from datetime import datetime
    date_str = datetime.now().strftime('%d/%m/%Y')

    titre_esc = _esc_tex(titre)
    type_esc  = _esc_tex(type_label)

    # Sections des exercices
    exercices_tex = ""
    for item in corrections:
        num   = _esc_tex(item.get('numero', ''))
        diff  = item.get('difficulte', 'moyen')
        diff_color = {
            'facile': 'green!60!black',
            'moyen':  'orange!80!black',
            'difficile': 'red!70!black',
        }.get(diff, 'black')

        enonce     = _md_to_tex_simple(item.get('enonce', ''))
        reponse    = _md_to_tex_simple(item.get('reponse', ''))
        explication = _md_to_tex_simple(item.get('explication', ''))
        conseils   = _md_to_tex_simple(item.get('conseils', ''))
        notions    = item.get('notions', [])
        notions_str = ', '.join([_esc_tex(n) for n in notions])

        exercices_tex += f"""
\\subsection*{{\\color{{maincolor}}{num}
    \\hfill\\small\\color{{{diff_color}}}[{_esc_tex(diff)}]}}

\\subsubsection*{{\\color{{subcolor}}Énoncé}}
\\begin{{mdframed}}[linecolor=gray!30,backgroundcolor=gray!5,
                   linewidth=0.5pt,innerleftmargin=8pt]
{enonce}
\\end{{mdframed}}

\\subsubsection*{{\\color{{green!60!black}}Réponse correcte}}
\\begin{{mdframed}}[linecolor=green!40,backgroundcolor=green!5,
                   linewidth=0.5pt,innerleftmargin=8pt]
{reponse}
\\end{{mdframed}}

\\subsubsection*{{\\color{{blue!60!black}}Explication détaillée}}
{explication}
"""
        if notions_str:
            exercices_tex += f"""
\\subsubsection*{{Notions clés}}
\\begin{{center}}
\\textbf{{\\textcolor{{maincolor}}{{{notions_str}}}}}
\\end{{center}}
"""
        if conseils:
            exercices_tex += f"""
\\subsubsection*{{\\color{{orange!70!black}}⚠~Conseil}}
\\begin{{mdframed}}[linecolor=orange!40,backgroundcolor=orange!5,
                   linewidth=0.5pt,innerleftmargin=8pt]
{conseils}
\\end{{mdframed}}
"""
        exercices_tex += "\n\\bigskip\\hrule\\bigskip\n"

    # Résumé pédagogique
    resume_tex = ""
    if resume:
        resume_tex = f"""
\\section*{{Synthèse pédagogique}}
\\begin{{mdframed}}[linecolor=blue!40,backgroundcolor=blue!5,
                   linewidth=1pt,innerleftmargin=10pt,innerrightmargin=10pt]
{_md_to_tex_simple(resume)}
\\end{{mdframed}}
"""

    # Préambule LaTeX statique (pas de f-string pour éviter {e} interprété)
    PREAMBULE = (
        r"\documentclass[12pt,a4paper]{article}" + "\n"
        r"\usepackage[utf8]{inputenc}" + "\n"
        r"\usepackage[T1]{fontenc}" + "\n"
        r"\usepackage[french]{babel}" + "\n"
        r"\usepackage[a4paper, margin=2.5cm]{geometry}" + "\n"
        r"\usepackage[table]{xcolor}" + "\n"
        r"\usepackage{amsmath,amssymb}" + "\n"
        r"\usepackage{listings}" + "\n"
        r"\usepackage{enumitem}" + "\n"
        r"\usepackage{mdframed}" + "\n"
        r"\usepackage{fancyhdr}" + "\n"
        r"\usepackage[hyphens]{url}" + "\n"
        r"\usepackage[colorlinks=true,linkcolor=black,urlcolor=blue]{hyperref}" + "\n"
        "\n"
        r"\definecolor{maincolor}{RGB}{180,0,0}" + "\n"
        r"\definecolor{subcolor}{RGB}{50,50,150}" + "\n"
        "\n"
        r"\lstset{" + "\n"
        r"  basicstyle=\small\ttfamily," + "\n"
        r"  backgroundcolor=\color{gray!10}," + "\n"
        r"  frame=single,breaklines=true,language=Python," + "\n"
        r"  extendedchars=true," + "\n"
        r"  literate={é}{{\'e}}1 {è}{{\`e}}1 {ê}{{\^e}}1" + "\n"
        r"           {à}{{\`a}}1 {â}{{\^a}}1 {ù}{{\`u}}1" + "\n"
        r"           {î}{{\^i}}1 {ô}{{\^o}}1 {ç}{{\c{c}}}1" + "\n"
        r"           {É}{{\'E}}1 {È}{{\`E}}1 {À}{{\`A}}1" + "\n"
        r"           {Î}{{\^I}}1," + "\n"
        r"}" + "\n"
        "\n"
    )

    PAGE_TITRE = (
        "\\pagestyle{fancy}\n"
        "\\fancyhf{}\n"
        f"\\fancyhead[L]{{\\small\\textcolor{{gray}}{{{titre_esc}}}}}\n"
        f"\\fancyhead[R]{{\\small\\textcolor{{gray}}{{Corrig\'e -- {date_str}}}}}\n"
        "\\fancyfoot[C]{\\thepage}\n"
        "\\renewcommand{\\headrulewidth}{0.4pt}\n"
        "\n"
        "\\setlength{\\parskip}{0.5em}\n"
        "\\setlength{\\parindent}{0pt}\n"
        "\n"
        "\\begin{document}\n"
        "\n"
        "\\begin{titlepage}\n"
        "\\centering\n"
        "\\vspace*{2cm}\n"
        "{\\color{maincolor}\\rule{\\textwidth}{4pt}}\\\\[0.8cm]\n"
        "{\\Huge\\bfseries\\color{maincolor} Corrig\'e}\\\\[0.5cm]\n"
        f"{{\\Large {type_esc}}}\\\\[1cm]\n"
        "\\colorbox{maincolor!10}{\\parbox{0.85\\textwidth}{\\centering\n"
        "    \\vspace{0.4cm}\n"
        f"    {{\\Large\\bfseries\\color{{maincolor}} {titre_esc}}}\\\\[0.3cm]\n"
        "    \\vspace{0.4cm}\n"
        "}}\n"
        "\\vfill\n"
        f"{{\\large Date : {date_str}}}\\\\[0.3cm]\n"
        f"{{\\large {len(corrections)} exercice(s) corrig\'e(s)}}\\\\[0.5cm]\n"
        "{\\color{maincolor}\\rule{\\textwidth}{4pt}}\n"
        "\\end{titlepage}\n"
        "\n"
        "\\tableofcontents\n"
        "\\newpage\n"
        "\n"
        "\\section*{Exercices corrig\'es}\n"
        "\\addcontentsline{toc}{section}{Exercices corrig\'es}\n"
        "\n"
    )

    FIN = (
        "\n"
        "\\end{document}\n"
    )

    return PREAMBULE + PAGE_TITRE + exercices_tex + "\n" + resume_tex + FIN


# ══════════════════════════════════════════════════════════════════════
# GÉNÉRATION DU DOCUMENT CORRIGÉ — Word (via Node.js + docx-js)
# ══════════════════════════════════════════════════════════════════════

GENERATE_CORRIGE_JS = r"""
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, LevelFormat,
  BorderStyle, WidthType, ShadingType, VerticalAlign,
  PageNumber, PageBreak, TabStopType
} = require("docx");
const fs = require("fs");

const data       = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const outputPath = process.argv[3];

const corrections = data.corrections || [];
const titre       = data.titre       || "Corrigé";
const typeDoc     = data.type_doc    || "";
const resume      = data.resume      || "";
const date        = new Date().toLocaleDateString("fr-FR");

const ROUGE  = "B40000";
const VERT   = "1A7A3A";
const BLEU   = "1A3A8A";
const ORANGE = "C05000";
const GRIS   = "555555";
const BLANC  = "FFFFFF";
const PAGE_W = 11906, PAGE_H = 16838;
const MAR    = 1440, MAR_L = 1800;
const CW     = PAGE_W - MAR_L - MAR;

const brd  = (c,s=4) => ({style:BorderStyle.SINGLE,size:s,color:c});
const bords = c => ({top:brd(c),bottom:brd(c),left:brd(c),right:brd(c)});

function run(text, o={}) {
  return new TextRun({
    text: String(text||""),
    font:   o.font   || "Calibri",
    size:   o.size   || 22,
    bold:   o.bold   || false,
    italic: o.italic || false,
    color:  o.color  || "000000",
  });
}

function para(runs, o={}) {
  const children = Array.isArray(runs) ? runs : [run(runs, o)];
  return new Paragraph({
    alignment: o.align || AlignmentType.LEFT,
    spacing:   {before: o.before??80, after: o.after??80, line: o.line||276},
    border:    o.border || undefined,
    children,
  });
}

function colorBox(children_paras, fillColor) {
  return new Table({
    width: {size: CW, type: WidthType.DXA},
    columnWidths: [CW],
    rows: [new TableRow({
      children: [new TableCell({
        borders: bords(fillColor),
        width: {size: CW, type: WidthType.DXA},
        shading: {fill: "F5F5F5", type: ShadingType.CLEAR},
        margins: {top:120, bottom:120, left:180, right:180},
        children: children_paras,
      })]
    })]
  });
}

function labelPara(text, color) {
  return para([
    run(text, {size:20, bold:true, color})
  ], {before:160, after:60});
}

function textToParagraphs(text) {
  if (!text) return [para("—")];
  const lines = String(text).replace(/\\n/g, "\n").split("\n");
  const result = [];
  for (const line of lines) {
    const stripped = line.trim();
    if (!stripped) { result.push(para("")); continue; }
    // Gras **...**
    const parts = stripped.split(/(\*\*[^*]+\*\*)/);
    const runs_arr = parts.map(p => {
      if (p.startsWith("**") && p.endsWith("**"))
        return run(p.slice(2,-2), {bold:true});
      return run(p);
    });
    result.push(para(runs_arr, {before:40, after:40}));
  }
  return result.length ? result : [para("—")];
}

const sp = (n=100) => new Paragraph({spacing:{before:0,after:n},children:[]});
const hr = () => new Paragraph({
  spacing:{before:160,after:160},
  border:{bottom:{style:BorderStyle.SINGLE,size:6,color:"CCCCCC"}},
  children:[]
});

// ── Page de titre ────────────────────────────────────────────────────────────
function buildCoverPage() {
  return [
    sp(1200),
    para([run("CORRIGÉ", {size:52,bold:true,color:ROUGE})],
         {align:AlignmentType.CENTER, before:0, after:120}),
    para([run(typeDoc, {size:28,color:GRIS})],
         {align:AlignmentType.CENTER, before:0, after:400}),
    new Table({
      width:{size:CW,type:WidthType.DXA},
      columnWidths:[CW],
      rows:[new TableRow({children:[new TableCell({
        borders:bords(ROUGE),
        width:{size:CW,type:WidthType.DXA},
        shading:{fill:"FFF5F5",type:ShadingType.CLEAR},
        margins:{top:200,bottom:200,left:300,right:300},
        children:[para([run(titre,{size:26,bold:true,color:ROUGE})],
                       {align:AlignmentType.CENTER,before:0,after:0})]
      })]})]}),
    sp(600),
    para([run(`Date : ${date}`,{size:22,color:GRIS})],
         {align:AlignmentType.CENTER,before:0,after:80}),
    para([run(`${corrections.length} exercice(s) corrigé(s)`,{size:22,color:GRIS})],
         {align:AlignmentType.CENTER,before:0,after:0}),
    sp(800),
    new Paragraph({children:[new PageBreak()],spacing:{before:0,after:0}}),
  ];
}

// ── Corps des exercices ───────────────────────────────────────────────────────
function buildBody() {
  const children = [];

  children.push(new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing:{before:0,after:240},
    children:[run("Exercices corrigés",{size:28,bold:true,color:ROUGE})]
  }));

  for (const item of corrections) {
    const diff = item.difficulte || "moyen";
    const diffColor = diff==="facile" ? VERT : diff==="difficile" ? "C00000" : ORANGE;

    // En-tête exercice
    children.push(new Paragraph({
      heading: HeadingLevel.HEADING_2,
      spacing:{before:320,after:120},
      children:[
        run(item.numero || "Exercice", {size:24,bold:true,color:ROUGE}),
        run(`  [${diff}]`, {size:18,color:diffColor,bold:true}),
      ]
    }));

    // Énoncé
    children.push(labelPara("📋 Énoncé", GRIS));
    children.push(colorBox(textToParagraphs(item.enonce), "AAAAAA"));
    children.push(sp(80));

    // Réponse
    children.push(labelPara("✅ Réponse correcte", VERT));
    children.push(colorBox(textToParagraphs(item.reponse), "1A7A3A"));
    children.push(sp(80));

    // Explication
    children.push(labelPara("💡 Explication détaillée", BLEU));
    children.push(...textToParagraphs(item.explication));
    children.push(sp(80));

    // Notions
    if (item.notions && item.notions.length) {
      children.push(labelPara("🏷 Notions clés", "666666"));
      const notionRuns = item.notions.flatMap((n,i) => [
        run(n, {size:20,bold:true,color:ROUGE}),
        ...(i < item.notions.length-1 ? [run("  •  ",{size:18,color:GRIS})] : [])
      ]);
      children.push(para(notionRuns, {before:40,after:40}));
      children.push(sp(80));
    }

    // Conseils
    if (item.conseils) {
      children.push(labelPara("⚠ Conseil", ORANGE));
      children.push(colorBox(textToParagraphs(item.conseils), "C05000"));
    }

    children.push(hr());
  }

  // Synthèse
  if (resume) {
    children.push(new Paragraph({
      heading:HeadingLevel.HEADING_1,
      spacing:{before:320,after:160},
      children:[run("Synthèse pédagogique",{size:28,bold:true,color:ROUGE})]
    }));
    children.push(colorBox(textToParagraphs(resume), "1A3A8A"));
  }

  return children;
}

// ── Document ──────────────────────────────────────────────────────────────────
const docHeader = new Header({children:[new Paragraph({
  spacing:{before:0,after:80},
  border:{bottom:{style:BorderStyle.SINGLE,size:6,color:ROUGE}},
  tabStops:[{type:TabStopType.RIGHT,position:CW}],
  children:[
    run(titre.slice(0,50)+(titre.length>50?"…":""),{size:18,italic:true,color:GRIS}),
    new TextRun({text:"\t",size:18}),
    run("Corrigé",{size:18,italic:true,color:ROUGE}),
  ],
})]});

const docFooter = new Footer({children:[new Paragraph({
  alignment:AlignmentType.CENTER,
  spacing:{before:80,after:0},
  border:{top:{style:BorderStyle.SINGLE,size:4,color:ROUGE}},
  children:[
    run("Page ",{size:18,color:GRIS}),
    new TextRun({children:[PageNumber.CURRENT],size:18,color:GRIS,font:"Calibri"}),
    run(" / ",{size:18,color:GRIS}),
    new TextRun({children:[PageNumber.TOTAL_PAGES],size:18,color:GRIS,font:"Calibri"}),
  ],
})]});

const doc = new Document({
  numbering:{config:[
    {reference:"bullets",levels:[{level:0,format:LevelFormat.BULLET,text:"\u2022",
      alignment:AlignmentType.LEFT,
      style:{run:{font:"Symbol",size:22},paragraph:{indent:{left:720,hanging:360}}}}]},
    {reference:"numbers",levels:[{level:0,format:LevelFormat.DECIMAL,text:"%1.",
      alignment:AlignmentType.LEFT,
      style:{paragraph:{indent:{left:720,hanging:360}}}}]},
  ]},
  styles:{
    default:{document:{run:{font:"Calibri",size:22}}},
    paragraphStyles:[
      {id:"Heading1",name:"Heading 1",basedOn:"Normal",next:"Normal",quickFormat:true,
        run:{size:28,bold:true,color:ROUGE,font:"Calibri"},
        paragraph:{spacing:{before:320,after:160},outlineLevel:0}},
      {id:"Heading2",name:"Heading 2",basedOn:"Normal",next:"Normal",quickFormat:true,
        run:{size:24,bold:true,color:ROUGE,font:"Calibri"},
        paragraph:{spacing:{before:240,after:120},outlineLevel:1}},
    ],
  },
  sections:[{
    properties:{page:{
      size:{width:PAGE_W,height:PAGE_H},
      margin:{top:MAR,bottom:MAR,left:MAR_L,right:MAR},
    }},
    headers:{default:docHeader},
    footers:{default:docFooter},
    children:[...buildCoverPage(), ...buildBody()],
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outputPath, buf);
  console.log("OK:" + outputPath);
}).catch(err => {
  console.error("ERR:" + err.message);
  process.exit(1);
});
"""


def _trouver_node_modules() -> str:
    """Trouve où docx est installé et retourne le répertoire de travail."""
    candidats = [
        '/app',                           # Docker standard
        '/home/maeva/allops',             # WSL direct
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # racine projet
    ]
    for cwd in candidats:
        if os.path.exists(os.path.join(cwd, 'node_modules', 'docx')):
            return cwd
    return None


def generer_word_correction(corrections: list, titre: str,
                             type_doc: str, resume: str,
                             output_path: str) -> bool:
    """Génère le fichier Word du corrigé via Node.js."""
    import uuid

    # Trouver le répertoire avec node_modules/docx
    cwd_node = _trouver_node_modules()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Si docx pas trouvé → installer dans tmpdir
        if not cwd_node:
            r_npm = subprocess.run(
                ['npm', 'install', 'docx'],
                cwd=tmpdir, capture_output=True, timeout=90
            )
            cwd_node = tmpdir

        # Écrire les fichiers dans tmpdir
        uid       = uuid.uuid4().hex[:8]
        js_path   = os.path.join(tmpdir, f'gen_{uid}.js')
        data_path = os.path.join(tmpdir, f'data_{uid}.json')

        with open(js_path, 'w', encoding='utf-8') as f:
            f.write(GENERATE_CORRIGE_JS)

        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump({
                'corrections': corrections,
                'titre':       titre,
                'type_doc':    TYPES_DOC.get(type_doc, type_doc),
                'resume':      resume,
            }, f, ensure_ascii=False)

        # Définir NODE_PATH pour que node trouve docx peu importe le cwd
        env = os.environ.copy()
        node_path = os.path.join(cwd_node, 'node_modules')
        env['NODE_PATH'] = node_path

        result = subprocess.run(
            ['node', js_path, data_path, output_path],
            capture_output=True, text=True, timeout=60,
            cwd=cwd_node, env=env
        )

        # Log pour debug si erreur
        if result.returncode != 0 or not os.path.exists(output_path):
            import logging
            logging.error(
                f"Word generation failed\n"
                f"  cwd: {cwd_node}\n"
                f"  NODE_PATH: {node_path}\n"
                f"  stdout: {result.stdout[:300]}\n"
                f"  stderr: {result.stderr[:300]}"
            )
            return False

        return True