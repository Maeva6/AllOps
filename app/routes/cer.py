import os
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from flask import (Blueprint, render_template, request,
                   flash, redirect, url_for, jsonify,
                   send_file, Response)
from app.extensions import db
from app.models import SessionCER
from app.services.cer_service import generer_section_cer, generer_latex_complet
import fitz

UTC = timezone.utc
cer_bp = Blueprint('cer', __name__, url_prefix='/cer')


# ══════════════════════════════════════════════════════════════════════
# EXTRACTION DU PROSIT ALLER (.docx / .md / .txt / .pdf)
# ══════════════════════════════════════════════════════════════════════

def extraire_texte_fichier(fichier) -> str:
    """Extrait le texte brut d'un fichier uploadé."""
    name      = fichier.filename.lower()
    raw_bytes = fichier.read()

    if name.endswith('.pdf'):
        doc   = fitz.open(stream=raw_bytes, filetype="pdf")
        texte = "\n".join(page.get_text() for page in doc)
        doc.close()
        return texte

    if name.endswith('.docx'):
        try:
            from docx import Document as DocxDoc
            import io
            doc = DocxDoc(io.BytesIO(raw_bytes))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            return f"[Erreur lecture docx : {e}]"

    return raw_bytes.decode('utf-8', errors='ignore')


def extraire_prosit_aller(texte: str) -> dict:
    """
    Parse le texte brut d'un prosit aller et retourne un dict
    avec les champs du formulaire CER pré-remplis.
    """
    champs = {
        'titre_prosit':     '',
        'numero_prosit':    '',
        'mots_cles':        '',
        'contexte':         '',
        'besoins':          '',
        'contraintes':      '',
        'problematique':    '',
        'pistes_solutions': '',
        'plan_action':      '',
    }

    SECTIONS = [
        ('mots_cles',        [r'mots[- ]cl[eé]s?', r'keywords?']),
        ('contexte',         [r'analyse du contexte', r'contexte', r'mise en situation', r'situation']),
        ('besoins',          [r'besoins?', r'notions? [àa] [eé]tudier', r'notions? cl[eé]s?', r'analyse des besoins']),
        ('contraintes',      [r'contraintes?']),
        ('problematique',    [r'd[eé]finition de la probl[eé]matique', r'probl[eé]matique', r'question centrale']),
        ('pistes_solutions', [r'pistes?(?: de solutions?)?', r'hypoth[eè]ses?']),
        ('plan_action',      [r"plan d[' ]action", r'plan de travail', r'[eé]tapes?']),
    ]

    all_titles = []
    for _, patterns in SECTIONS:
        all_titles.extend(patterns)
    boundary = '|'.join(all_titles)

    # Numéro et titre
    m_titre = re.search(
        r'PROSIT\s+(?:ALLER\s+)?N[°o]?\s*(\d+)\s*[:\-–—]\s*(.+)',
        texte, re.IGNORECASE
    )
    if m_titre:
        champs['numero_prosit'] = f"Prosit {m_titre.group(1)}"
        titre_brut = m_titre.group(2).strip()
        titre_brut = re.sub(
            r'\s*(cahier|cer|étudiant|pilote|co-pilote|promotion|date).*$',
            '', titre_brut, flags=re.IGNORECASE
        ).strip()
        champs['titre_prosit'] = f"Prosit N°{m_titre.group(1)} — {titre_brut}"
    else:
        for line in texte.splitlines():
            if line.strip():
                champs['titre_prosit'] = line.strip()
                break

    # Récupérer etudiant / pilote / copilote depuis le texte
    for label, key in [
        (r'[EÉ]tudiant\s*:', 'etudiant'),
        (r'Pilote\s*:', 'pilote'),
        (r'Co-pilote\s*:', 'copilote'),
        (r'Promotion\s*:', 'promotion'),
    ]:
        m = re.search(label + r'\s*(.+)', texte, re.IGNORECASE)
        if m:
            champs[key] = m.group(1).strip()

    # Extraire chaque section académique
    for champ, patterns in SECTIONS:
        for pat in patterns:
            regex = (
                r'(?:^|\n)'
                r'(?:[IVX]+\.\s*)?'
                r'(?:\d+[\.\)]\s*)?'
                r'(?:' + pat + r')\s*[:\-–]?\s*\n'
                r'(.*?)'
                r'(?=\n\s*(?:[IVX]+\.\s*)?(?:\d+[\.\)]\s*)?(?:' + boundary + r')\s*[:\-–]?\s*\n|$)'
            )
            m = re.search(regex, texte, re.IGNORECASE | re.DOTALL)
            if m:
                contenu = m.group(1).strip()
                contenu = re.sub(r'\n{3,}', '\n\n', contenu)
                champs[champ] = contenu
                break

    # Post-traitement plan_action
    if champs['plan_action']:
        lignes = []
        for ligne in champs['plan_action'].splitlines():
            ligne = ligne.strip()
            if ligne:
                ligne = re.sub(r'^[\d]+[\.\)]\s*', '', ligne)
                ligne = re.sub(r'^[-•*]\s*', '', ligne)
                if ligne:
                    lignes.append(ligne)
        champs['plan_action'] = '\n'.join(lignes)

    return champs


# ══════════════════════════════════════════════════════════════════════
# GÉNÉRATION WORD NATIVE (python-docx)
# Mise en page conforme au PDF exemple
# ══════════════════════════════════════════════════════════════════════

def generer_word_cer(cer) -> bytes:
    """
    Génère un .docx professionnel conforme à la mise en page du PDF exemple.
    Retourne les bytes du fichier.
    """
    from docx import Document
    from docx.shared import Pt, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    import io

    ROUGE = RGBColor(180, 0, 0)
    GRIS  = RGBColor(80,  80, 80)
    BLEU  = RGBColor(0,   70, 127)

    doc = Document()

    # Marges
    for sec in doc.sections:
        sec.top_margin    = Cm(2.5)
        sec.bottom_margin = Cm(2.5)
        sec.left_margin   = Cm(2.5)
        sec.right_margin  = Cm(2.5)

    # Style Normal
    doc.styles['Normal'].font.name = 'Calibri'
    doc.styles['Normal'].font.size = Pt(11)

    # ── Helpers ───────────────────────────────────────────────────────

    def set_cell_bg(cell, hex_color):
        tc   = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd  = OxmlElement('w:shd')
        shd.set(qn('w:val'),   'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'),  hex_color)
        tcPr.append(shd)

    def add_heading_rouge(text, level=1):
        h = doc.add_heading('', level=level)
        h.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = h.add_run(text)
        run.font.color.rgb = ROUGE
        run.font.bold      = True
        run.font.size      = Pt({1: 14, 2: 12}.get(level, 11))
        return h

    def add_separator():
        p   = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after  = Pt(2)
        pPr = p._p.get_or_add_pPr()
        pBdr = OxmlElement('w:pBdr')
        bot  = OxmlElement('w:bottom')
        bot.set(qn('w:val'),   'single')
        bot.set(qn('w:sz'),    '12')
        bot.set(qn('w:space'), '1')
        bot.set(qn('w:color'), 'B40000')
        pBdr.append(bot)
        pPr.append(pBdr)

    def add_problematique_box(text):
        p   = doc.add_paragraph()
        pPr = p._p.get_or_add_pPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'),   'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'),  'DCE8F8')
        pPr.append(shd)
        p.paragraph_format.left_indent   = Cm(0.5)
        p.paragraph_format.right_indent  = Cm(0.5)
        p.paragraph_format.space_before  = Pt(6)
        p.paragraph_format.space_after   = Pt(6)
        # Bordure gauche rouge
        pBdr = OxmlElement('w:pBdr')
        left = OxmlElement('w:left')
        left.set(qn('w:val'),   'single')
        left.set(qn('w:sz'),    '18')
        left.set(qn('w:space'), '4')
        left.set(qn('w:color'), 'B40000')
        pBdr.append(left)
        pPr.append(pBdr)
        run = p.add_run(text)
        run.font.italic = True
        run.font.size   = Pt(11)

    def add_code_block(lines):
        for line in (lines if lines else ['']):
            p = doc.add_paragraph()
            pPr = p._p.get_or_add_pPr()
            shd = OxmlElement('w:shd')
            shd.set(qn('w:val'),   'clear')
            shd.set(qn('w:color'), 'auto')
            shd.set(qn('w:fill'),  'F0F0F0')
            pPr.append(shd)
            run = p.add_run(line if line else ' ')
            run.font.name = 'Courier New'
            run.font.size = Pt(9)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after  = Pt(0)
            p.paragraph_format.left_indent  = Cm(0.5)

    def inline_md(paragraph, text):
        """Applique gras/italique/code inline dans un paragraphe."""
        parts = re.split(r'(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)', text)
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                r = paragraph.add_run(part[2:-2]); r.bold = True
            elif part.startswith('*') and part.endswith('*'):
                r = paragraph.add_run(part[1:-1]); r.italic = True
            elif part.startswith('`') and part.endswith('`'):
                r = paragraph.add_run(part[1:-1])
                r.font.name = 'Courier New'; r.font.size = Pt(9)
            else:
                paragraph.add_run(part)

    def parse_md(text):
        """Parse le Markdown et ajoute au document."""
        if not text:
            return
        in_code  = False
        code_buf = []
        tbl_buf  = []
        in_table = False

        def flush_table():
            rows = [l for l in tbl_buf
                    if not re.match(r'^\|[-\s|:]+\|$', l.strip())]
            if not rows:
                return
            cols = [c.strip() for c in rows[0].strip('|').split('|')]
            nb   = len(cols)
            tbl  = doc.add_table(rows=len(rows), cols=nb)
            tbl.style = 'Table Grid'
            for i, row_txt in enumerate(rows):
                cells = [c.strip() for c in row_txt.strip('|').split('|')]
                while len(cells) < nb: cells.append('')
                for j, ct in enumerate(cells[:nb]):
                    cell = tbl.rows[i].cells[j]
                    cell.text = re.sub(r'\*\*(.+?)\*\*', r'\1', ct)
                    if i == 0:
                        for r2 in cell.paragraphs[0].runs:
                            r2.bold = True; r2.font.color.rgb = RGBColor(255,255,255)
                        set_cell_bg(cell, 'B40000')
            doc.add_paragraph()

        for line in text.splitlines():
            s = line.strip()

            if s.startswith('```'):
                if in_table: flush_table(); tbl_buf = []; in_table = False
                if in_code:
                    add_code_block(code_buf); code_buf = []; in_code = False
                else:
                    in_code = True
                continue
            if in_code:
                code_buf.append(line); continue

            if s.startswith('|'):
                in_table = True; tbl_buf.append(s); continue
            elif in_table:
                flush_table(); tbl_buf = []; in_table = False

            if not s:
                doc.add_paragraph(); continue

            if s.startswith('#### '):
                add_heading_rouge(s[5:], level=4)
            elif s.startswith('### '):
                add_heading_rouge(s[4:], level=3)
            elif s.startswith('## '):
                add_heading_rouge(s[3:], level=2)
            elif s.startswith('# '):
                add_heading_rouge(s[2:], level=1)
            elif re.match(r'^[-*+] ', s):
                p = doc.add_paragraph(style='List Bullet')
                inline_md(p, s[2:])
            elif re.match(r'^\d+\. ', s):
                p = doc.add_paragraph(style='List Number')
                inline_md(p, re.sub(r'^\d+\.\s+', '', s))
            else:
                p = doc.add_paragraph()
                inline_md(p, s)

        if in_code and code_buf:
            add_code_block(code_buf)
        if in_table and tbl_buf:
            flush_table()

    plan = cer.get_plan_action()
    date_str = (cer.created_at.strftime('%d/%m/%Y')
                if cer.created_at else datetime.now().strftime('%d/%m/%Y'))

    # ══════════════════════════════════════════════════════════════════
    # PAGE DE GARDE
    # ══════════════════════════════════════════════════════════════════

    # Titre UCAC-ICAM centré rouge
    p_logo = doc.add_paragraph()
    p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_logo = p_logo.add_run("UCAC-ICAM")
    r_logo.bold = True; r_logo.font.size = Pt(20); r_logo.font.color.rgb = ROUGE

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("La Fabrique à Génie")
    r_sub.font.size = Pt(11); r_sub.font.color.rgb = GRIS

    doc.add_paragraph()

    # Trait rouge
    add_separator()
    doc.add_paragraph()

    # Titre CER centré rouge
    p_cer = doc.add_paragraph()
    p_cer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_cer = p_cer.add_run("CAHIER D'ÉTUDE ET DE RECHERCHE")
    r_cer.bold = True; r_cer.font.size = Pt(20); r_cer.font.color.rgb = ROUGE

    doc.add_paragraph()

    # Titre prosit dans encadré rouge (fond rose clair)
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pPr_t = p_tit._p.get_or_add_pPr()
    shd_t = OxmlElement('w:shd')
    shd_t.set(qn('w:val'),   'clear')
    shd_t.set(qn('w:color'), 'auto')
    shd_t.set(qn('w:fill'),  'FBEAEA')
    pPr_t.append(shd_t)
    # Bordure rouge tout autour
    pBdr_t = OxmlElement('w:pBdr')
    for side in ('top', 'left', 'bottom', 'right'):
        el = OxmlElement(f'w:{side}')
        el.set(qn('w:val'),   'single')
        el.set(qn('w:sz'),    '12')
        el.set(qn('w:space'), '4')
        el.set(qn('w:color'), 'B40000')
        pBdr_t.append(el)
    pPr_t.append(pBdr_t)
    p_tit.paragraph_format.space_before = Pt(8)
    p_tit.paragraph_format.space_after  = Pt(8)
    r_tit = p_tit.add_run(cer.titre_prosit or 'CER')
    r_tit.bold = True; r_tit.font.size = Pt(16); r_tit.font.color.rgb = ROUGE

    doc.add_paragraph()
    doc.add_paragraph()

    # Tableau infos étudiant
    info_tbl = doc.add_table(rows=0, cols=2)
    info_tbl.style = 'Table Grid'

    def add_info_row(label, value):
        if not value: return
        row = info_tbl.add_row()
        row.cells[0].text = label
        row.cells[1].text = value
        for r2 in row.cells[0].paragraphs[0].runs:
            r2.bold = True
        set_cell_bg(row.cells[0], 'F0F0F0')

    add_info_row("Étudiant",  cer.etudiant  or '')
    add_info_row("Pilote",    cer.pilote    or '')
    add_info_row("Co-pilote", cer.copilote  or '')
    add_info_row("Promotion", cer.promotion or '')
    add_info_row("Date",      date_str)

    doc.add_paragraph()
    add_separator()
    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════
    # SECTIONS
    # ══════════════════════════════════════════════════════════════════

    def section(titre, contenu_fn):
        add_heading_rouge(titre, level=1)
        add_separator()
        contenu_fn()
        doc.add_paragraph()

    # I. Contexte
    section("I. Analyse du contexte", lambda: parse_md(cer.contexte))

    # II. Besoins
    add_heading_rouge("II. Analyse des besoins", level=1)
    add_separator()
    add_heading_rouge("Besoins", level=2)
    for b in (cer.besoins or '').splitlines():
        b = b.lstrip('-•* \t').strip()
        if b:
            p = doc.add_paragraph(style='List Bullet')
            inline_md(p, b)
    add_heading_rouge("Contraintes", level=2)
    for c in (cer.contraintes or '').splitlines():
        c = c.lstrip('-•* \t').strip()
        if c:
            p = doc.add_paragraph(style='List Bullet')
            inline_md(p, c)
    add_heading_rouge("Problématique", level=2)
    if cer.problematique:
        add_problematique_box(cer.problematique)
    doc.add_paragraph()

    # III. Généralisation
    add_heading_rouge("III. Généralisation", level=1)
    add_separator()
    p_gen = doc.add_paragraph()
    p_gen.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_gen = p_gen.add_run(cer.titre_prosit or '')
    r_gen.bold = True; r_gen.font.size = Pt(13); r_gen.font.color.rgb = ROUGE
    doc.add_paragraph()

    # IV. Plan d'action
    add_heading_rouge("IV. Plan d'action", level=1)
    add_separator()
    for i, etape in enumerate(plan, 1):
        p = doc.add_paragraph(style='List Number')
        inline_md(p, etape)
    doc.add_paragraph()

    # V. Réalisation
    add_heading_rouge("V. Réalisation du plan d'action", level=1)
    add_separator()
    if cer.realisation:
        try:
            real = json.loads(cer.realisation)
            for i, etape in enumerate(plan):
                add_heading_rouge(f"V.{i+1} {etape}", level=2)
                parse_md(real.get(str(i), ''))
        except Exception:
            parse_md(cer.realisation)
    doc.add_paragraph()

    # VI. Validation
    section("VI. Validation des pistes de solutions",
            lambda: parse_md(cer.validation or ''))

    # VII. Conclusion
    section("VII. Conclusion et retours sur les objectifs",
            lambda: parse_md(cer.conclusion or ''))

    # VIII. Bilan
    section("VIII. Bilan critique du travail effectué",
            lambda: parse_md(cer.bilan or ''))

    # IX. Synthèse
    if cer.synthese:
        section("IX. Synthèse des résultats obtenus",
                lambda: parse_md(cer.synthese or ''))

    # X. Références
    add_heading_rouge("Références bibliographiques", level=1)
    add_separator()
    if cer.references:
        items = re.findall(r'\[(\d+)\]\s+(.+?)(?=\n\s*\[\d+\]|\Z)',
                           cer.references, re.DOTALL)
        if items:
            for num, content in items:
                p = doc.add_paragraph()
                p.add_run(f"[{num}] ").bold = True
                inline_md(p, content.strip().replace('\n', ' '))
        else:
            parse_md(cer.references)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


# ══════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════

@cer_bp.route('/')
def index():
    cers = SessionCER.query.order_by(SessionCER.created_at.desc()).all()
    return render_template('cer/index.html', title="CER", cers=cers)


@cer_bp.route('/extraire-prosit', methods=['POST'])
def extraire_prosit():
    fichier = request.files.get('prosit_aller')
    if not fichier or not fichier.filename:
        return jsonify({'erreur': 'Aucun fichier reçu'}), 400
    try:
        texte  = extraire_texte_fichier(fichier)
        champs = extraire_prosit_aller(texte)
        return jsonify({'ok': True, 'champs': champs})
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500


@cer_bp.route('/nouveau', methods=['GET', 'POST'])
def nouveau():
    if request.method == 'POST':
        plan_raw   = request.form.get('plan_action', '').strip()
        plan_items = [l.strip() for l in plan_raw.split('\n') if l.strip()]

        contenu_source = ""
        for fichier in request.files.getlist('fichiers'):
            if fichier and fichier.filename:
                name = fichier.filename.lower()
                if name.endswith('.pdf'):
                    raw = fichier.read()
                    d   = fitz.open(stream=raw, filetype="pdf")
                    for page in d: contenu_source += page.get_text()
                    d.close()
                elif name.endswith(('.txt', '.md', '.markdown')):
                    contenu_source += fichier.read().decode('utf-8', errors='ignore')
                elif name.endswith('.docx'):
                    try:
                        from docx import Document as DocxDoc
                        import io
                        raw = fichier.read()
                        d   = DocxDoc(io.BytesIO(raw))
                        contenu_source += "\n".join(
                            p.text for p in d.paragraphs if p.text.strip()
                        )
                    except Exception:
                        pass
                contenu_source += "\n\n"

        cer = SessionCER(
            titre_prosit  = request.form.get('titre_prosit',  '').strip(),
            numero_prosit = request.form.get('numero_prosit', '').strip(),
            etudiant      = request.form.get('etudiant',      '').strip(),
            pilote        = request.form.get('pilote',        '').strip(),
            copilote      = request.form.get('copilote',      '').strip(),
            promotion     = request.form.get('promotion',     '').strip(),
            annee         = request.form.get('annee',         '').strip(),
            contexte      = request.form.get('contexte',      '').strip(),
            besoins       = request.form.get('besoins',       '').strip(),
            contraintes   = request.form.get('contraintes',   '').strip(),
            problematique = request.form.get('problematique', '').strip(),
            plan_action   = json.dumps(plan_items),
            contenu_source= contenu_source[:8000],
            statut        = 'brouillon'
        )
        db.session.add(cer)
        db.session.commit()

        flash('✅ CER créé ! Lance la génération IA.', 'success')
        return redirect(url_for('cer.voir', id=cer.id))

    return render_template('cer/form.html', title="Nouveau CER", cer=None)


@cer_bp.route('/<int:id>')
def voir(id):
    cer = db.session.get(SessionCER, id)
    if not cer:
        flash('CER introuvable.', 'danger')
        return redirect(url_for('cer.index'))

    realisation_data = {}
    if cer.realisation:
        try: realisation_data = json.loads(cer.realisation)
        except Exception: pass

    return render_template('cer/voir.html',
                           title=cer.titre_prosit,
                           cer=cer,
                           plan=cer.get_plan_action(),
                           realisation_data=realisation_data)


@cer_bp.route('/generer-section/<int:id>', methods=['POST'])
def generer_section(id):
    cer  = db.session.get(SessionCER, id)
    if not cer:
        return jsonify({'erreur': 'CER introuvable'}), 404

    data    = request.json
    section = data.get('section', '')
    plan    = cer.get_plan_action()

    try:
        if section == 'realisation_etape':
            etape_index = int(data.get('etape_index', 0))
            etape_label = plan[etape_index] if etape_index < len(plan) else ''
            contenu = generer_section_cer(
                section='realisation_etape',
                titre_prosit=cer.titre_prosit, contexte=cer.contexte,
                besoins=cer.besoins, contraintes=cer.contraintes or '',
                problematique=cer.problematique, plan_action=plan,
                contenu_source=cer.contenu_source or '',
                etape_index=etape_index + 1, etape_label=etape_label
            )
            real = {}
            if cer.realisation:
                try: real = json.loads(cer.realisation)
                except Exception: pass
            real[str(etape_index)] = contenu
            cer.realisation = json.dumps(real)
            db.session.commit()
            return jsonify({'ok': True, 'contenu': contenu, 'etape_index': etape_index})
        else:
            contenu = generer_section_cer(
                section=section,
                titre_prosit=cer.titre_prosit, contexte=cer.contexte,
                besoins=cer.besoins, contraintes=cer.contraintes or '',
                problematique=cer.problematique, plan_action=plan,
                contenu_source=cer.contenu_source or '',
            )
            setattr(cer, section, contenu)
            db.session.commit()
            return jsonify({'ok': True, 'contenu': contenu})

    except Exception as e:
        return jsonify({'erreur': str(e)}), 500


@cer_bp.route('/generer-tout/<int:id>', methods=['POST'])
def generer_tout(id):
    cer  = db.session.get(SessionCER, id)
    if not cer:
        return jsonify({'erreur': 'CER introuvable'}), 404

    plan = cer.get_plan_action()
    try:
        real = {}
        for i, etape in enumerate(plan):
            real[str(i)] = generer_section_cer(
                section='realisation_etape',
                titre_prosit=cer.titre_prosit, contexte=cer.contexte,
                besoins=cer.besoins, contraintes=cer.contraintes or '',
                problematique=cer.problematique, plan_action=plan,
                contenu_source=cer.contenu_source or '',
                etape_index=i + 1, etape_label=etape
            )
        cer.realisation = json.dumps(real)

        for section in ['validation', 'conclusion', 'bilan', 'synthese', 'references']:
            setattr(cer, section, generer_section_cer(
                section=section,
                titre_prosit=cer.titre_prosit, contexte=cer.contexte,
                besoins=cer.besoins, contraintes=cer.contraintes or '',
                problematique=cer.problematique, plan_action=plan,
                contenu_source=cer.contenu_source or ''
            ))

        cer.statut = 'genere'
        db.session.commit()
        return jsonify({'ok': True, 'message': 'CER généré avec succès'})

    except Exception as e:
        return jsonify({'erreur': str(e)}), 500


@cer_bp.route('/export-latex/<int:id>')
def export_latex(id):
    cer = db.session.get(SessionCER, id)
    if not cer:
        flash('CER introuvable.', 'danger')
        return redirect(url_for('cer.index'))

    latex = generer_latex_complet(cer)
    cer.latex_genere = latex
    db.session.commit()

    nom = f"CER_{(cer.titre_prosit or 'cer')[:30].replace(' ', '_')}.tex"
    return Response(latex, mimetype='text/plain',
                    headers={'Content-Disposition': f'attachment; filename={nom}'})


@cer_bp.route('/export-word/<int:id>')
def export_word(id):
    cer = db.session.get(SessionCER, id)
    if not cer:
        flash('CER introuvable.', 'danger')
        return redirect(url_for('cer.index'))
    try:
        data = generer_word_cer(cer)
        nom  = f"CER_{(cer.titre_prosit or 'cer')[:30].replace(' ', '_')}.docx"
        return Response(
            data,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            headers={'Content-Disposition': f'attachment; filename="{nom}"',
                     'Content-Length': len(data)}
        )
    except Exception as e:
        flash(f'Erreur Word : {str(e)}', 'danger')
        return redirect(url_for('cer.voir', id=id))


@cer_bp.route('/export-pdf/<int:id>')
def export_pdf(id):
    cer = db.session.get(SessionCER, id)
    if not cer:
        flash('CER introuvable.', 'danger')
        return redirect(url_for('cer.index'))
    try:
        docx_bytes = generer_word_cer(cer)
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = os.path.join(tmpdir, 'cer.docx')
            pdf_path  = os.path.join(tmpdir, 'cer.pdf')
            with open(docx_path, 'wb') as f:
                f.write(docx_bytes)
            subprocess.run(
                ['libreoffice', '--headless', '--convert-to', 'pdf',
                 '--outdir', tmpdir, docx_path],
                capture_output=True, timeout=90
            )
            if not os.path.exists(pdf_path):
                flash('Erreur conversion PDF. Télécharge le .tex via Overleaf.', 'warning')
                return redirect(url_for('cer.voir', id=id))
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()

        nom = f"CER_{(cer.titre_prosit or 'cer')[:30].replace(' ', '_')}.pdf"
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{nom}"',
                     'Content-Length': len(pdf_bytes)}
        )
    except Exception as e:
        flash(f'Erreur PDF : {str(e)}', 'danger')
        return redirect(url_for('cer.voir', id=id))


@cer_bp.route('/supprimer/<int:id>', methods=['POST'])
def supprimer(id):
    cer = db.session.get(SessionCER, id)
    if cer:
        db.session.delete(cer)
        db.session.commit()
        flash('🗑️ CER supprimé.', 'warning')
    return redirect(url_for('cer.index'))