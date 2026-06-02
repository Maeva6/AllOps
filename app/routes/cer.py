import os
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from flask import (Blueprint, render_template, request,
                   flash, redirect, url_for, jsonify,
                   send_file, Response)
from app.extensions import db
from app.models import SessionCER
from app.services.cer_service import (
    generer_section_cer, generer_latex_complet
)
import fitz

UTC = timezone.utc
cer_bp = Blueprint('cer', __name__, url_prefix='/cer')


# ─── Liste des CERs ───────────────────────────────────────────────────────────
@cer_bp.route('/')
def index():
    cers = SessionCER.query.order_by(
        SessionCER.created_at.desc()
    ).all()
    return render_template('cer/index.html',
                           title="CER", cers=cers)


# ─── Nouveau CER ──────────────────────────────────────────────────────────────
@cer_bp.route('/nouveau', methods=['GET', 'POST'])
def nouveau():
    if request.method == 'POST':
        # Récupérer le plan d'action (liste de lignes)
        plan_raw   = request.form.get('plan_action', '').strip()
        plan_items = [
            l.strip() for l in plan_raw.split('\n')
            if l.strip()
        ]

        # Upload corbeille/workshop
        contenu_source = ""
        for fichier in request.files.getlist('fichiers'):
            if fichier and fichier.filename:
                name = fichier.filename.lower()
                if name.endswith('.pdf'):
                    pdf_bytes = fichier.read()
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    for page in doc:
                        contenu_source += page.get_text()
                    doc.close()
                elif name.endswith(('.txt', '.md')):
                    contenu_source += fichier.read().decode(
                        'utf-8', errors='ignore'
                    )
                contenu_source += "\n\n"

        cer = SessionCER(
            titre_prosit  = request.form.get('titre_prosit', '').strip(),
            numero_prosit = request.form.get('numero_prosit', '').strip(),
            etudiant      = request.form.get('etudiant', '').strip(),
            pilote        = request.form.get('pilote', '').strip(),
            copilote      = request.form.get('copilote', '').strip(),
            promotion     = request.form.get('promotion', '').strip(),
            annee         = request.form.get('annee', '').strip(),
            contexte      = request.form.get('contexte', '').strip(),
            besoins       = request.form.get('besoins', '').strip(),
            contraintes   = request.form.get('contraintes', '').strip(),
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


# ─── Voir / éditer un CER ─────────────────────────────────────────────────────
@cer_bp.route('/<int:id>')
def voir(id):
    cer = db.session.get(SessionCER, id)
    if not cer:
        flash('CER introuvable.', 'danger')
        return redirect(url_for('cer.index'))

    realisation_data = {}
    if cer.realisation:
        try:
            realisation_data = json.loads(cer.realisation)
        except Exception:
            pass

    return render_template('cer/voir.html',
                           title=cer.titre_prosit,
                           cer=cer,
                           plan=cer.get_plan_action(),
                           realisation_data=realisation_data)


# ─── Générer une section via AJAX ─────────────────────────────────────────────
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
                section       = 'realisation_etape',
                titre_prosit  = cer.titre_prosit,
                contexte      = cer.contexte,
                besoins       = cer.besoins,
                contraintes   = cer.contraintes or '',
                problematique = cer.problematique,
                plan_action   = plan,
                contenu_source= cer.contenu_source or '',
                etape_index   = etape_index + 1,
                etape_label   = etape_label
            )

            # Sauvegarder dans le JSON de réalisation
            real = {}
            if cer.realisation:
                try:
                    real = json.loads(cer.realisation)
                except Exception:
                    pass
            real[str(etape_index)] = contenu
            cer.realisation = json.dumps(real)
            db.session.commit()

            return jsonify({'ok': True, 'contenu': contenu,
                            'etape_index': etape_index})

        else:
            contenu = generer_section_cer(
                section       = section,
                titre_prosit  = cer.titre_prosit,
                contexte      = cer.contexte,
                besoins       = cer.besoins,
                contraintes   = cer.contraintes or '',
                problematique = cer.problematique,
                plan_action   = plan,
                contenu_source= cer.contenu_source or '',
            )

            setattr(cer, section, contenu)
            db.session.commit()

            return jsonify({'ok': True, 'contenu': contenu})

    except Exception as e:
        return jsonify({'erreur': str(e)}), 500


# ─── Générer tout le CER d'un coup ───────────────────────────────────────────
@cer_bp.route('/generer-tout/<int:id>', methods=['POST'])
def generer_tout(id):
    cer  = db.session.get(SessionCER, id)
    if not cer:
        return jsonify({'erreur': 'CER introuvable'}), 404

    plan    = cer.get_plan_action()
    erreurs = []

    try:
        # 1. Réalisation — chaque étape du plan d'action
        real = {}
        for i, etape in enumerate(plan):
            contenu = generer_section_cer(
                section       = 'realisation_etape',
                titre_prosit  = cer.titre_prosit,
                contexte      = cer.contexte,
                besoins       = cer.besoins,
                contraintes   = cer.contraintes or '',
                problematique = cer.problematique,
                plan_action   = plan,
                contenu_source= cer.contenu_source or '',
                etape_index   = i + 1,
                etape_label   = etape
            )
            real[str(i)] = contenu
        cer.realisation = json.dumps(real)

        # 2. Validation
        cer.validation = generer_section_cer(
            section='validation', titre_prosit=cer.titre_prosit,
            contexte=cer.contexte, besoins=cer.besoins,
            contraintes=cer.contraintes or '',
            problematique=cer.problematique, plan_action=plan,
            contenu_source=cer.contenu_source or ''
        )

        # 3. Conclusion
        cer.conclusion = generer_section_cer(
            section='conclusion', titre_prosit=cer.titre_prosit,
            contexte=cer.contexte, besoins=cer.besoins,
            contraintes=cer.contraintes or '',
            problematique=cer.problematique, plan_action=plan
        )

        # 4. Bilan
        cer.bilan = generer_section_cer(
            section='bilan', titre_prosit=cer.titre_prosit,
            contexte=cer.contexte, besoins=cer.besoins,
            contraintes=cer.contraintes or '',
            problematique=cer.problematique, plan_action=plan
        )

        # 5. Synthèse
        cer.synthese = generer_section_cer(
            section='synthese', titre_prosit=cer.titre_prosit,
            contexte=cer.contexte, besoins=cer.besoins,
            contraintes=cer.contraintes or '',
            problematique=cer.problematique, plan_action=plan
        )

        # 6. Références
        cer.references = generer_section_cer(
            section='references', titre_prosit=cer.titre_prosit,
            contexte=cer.contexte, besoins=cer.besoins,
            contraintes=cer.contraintes or '',
            problematique=cer.problematique, plan_action=plan
        )

        cer.statut = 'genere'
        db.session.commit()

        return jsonify({'ok': True, 'message': 'CER généré avec succès'})

    except Exception as e:
        return jsonify({'erreur': str(e)}), 500


# ─── Exporter en LaTeX ────────────────────────────────────────────────────────
@cer_bp.route('/export-latex/<int:id>')
def export_latex(id):
    cer = db.session.get(SessionCER, id)
    if not cer:
        flash('CER introuvable.', 'danger')
        return redirect(url_for('cer.index'))

    latex = generer_latex_complet(cer)
    cer.latex_genere = latex
    db.session.commit()

    nom = f"CER_{cer.titre_prosit[:30].replace(' ', '_')}.tex"
    return Response(
        latex,
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename={nom}'}
    )


# ─── Exporter en PDF via LaTeX ────────────────────────────────────────────────
# @cer_bp.route('/export-pdf/<int:id>')
# def export_pdf(id):
#     cer = db.session.get(SessionCER, id)
#     if not cer:
#         flash('CER introuvable.', 'danger')
#         return redirect(url_for('cer.index'))

#     latex = generer_latex_complet(cer)

#     # Compiler avec pdflatex dans un dossier temporaire
#     with tempfile.TemporaryDirectory() as tmpdir:
#         tex_path = os.path.join(tmpdir, 'cer.tex')
#         pdf_path = os.path.join(tmpdir, 'cer.pdf')

#         with open(tex_path, 'w', encoding='utf-8') as f:
#             f.write(latex)

#         # Compiler 2 fois pour la table des matières
#         for _ in range(2):
#             result = subprocess.run(
#                 ['pdflatex', '-interaction=nonstopmode',
#                  '-output-directory', tmpdir, tex_path],
#                 capture_output=True, text=True, timeout=60
#             )

#         if os.path.exists(pdf_path):
#             nom = f"CER_{cer.titre_prosit[:30].replace(' ', '_')}.pdf"
#             return send_file(
#                 pdf_path,
#                 as_attachment=True,
#                 download_name=nom,
#                 mimetype='application/pdf'
#             )
#         else:
#             flash(
#                 'Erreur de compilation LaTeX. '
#                 'Télécharge le .tex et compile sur Overleaf.',
#                 'warning'
#             )
#             return redirect(url_for('cer.voir', id=id))
@cer_bp.route('/export-pdf/<int:id>')
def export_pdf(id):
    cer = db.session.get(SessionCER, id)
    if not cer:
        flash('CER introuvable.', 'danger')
        return redirect(url_for('cer.index'))

    try:
        import subprocess, tempfile, json as json_lib

        # 1. Générer le Word d'abord
        realisation_data = {}
        if cer.realisation:
            try: realisation_data = json_lib.loads(cer.realisation)
            except: pass

        cer_data = {
            "titre_prosit":  cer.titre_prosit,
            "etudiant":      cer.etudiant or "",
            "pilote":        cer.pilote or "",
            "copilote":      cer.copilote or "",
            "promotion":     cer.promotion or "",
            "annee":         cer.annee or "",
            "contexte":      cer.contexte or "",
            "besoins":       cer.besoins or "",
            "contraintes":   cer.contraintes or "",
            "problematique": cer.problematique or "",
            "plan":          cer.get_plan_action(),
            "realisation":   realisation_data,
            "validation":    cer.validation or "",
            "conclusion":    cer.conclusion or "",
            "bilan":         cer.bilan or "",
            "synthese":      cer.synthese or "",
            "references":    cer.references or "",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            data_path   = os.path.join(tmpdir, 'cer_data.json')
            docx_path   = os.path.join(tmpdir, 'cer.docx')
            script_path = '/app/generate_cer.js'

            with open(data_path, 'w', encoding='utf-8') as f:
                json_lib.dump(cer_data, f, ensure_ascii=False)

            # 2. Générer le Word via Node.js
            r1 = subprocess.run(
                ['node', script_path, data_path, docx_path],
                capture_output=True, text=True, timeout=60
            )
            if r1.returncode != 0:
                flash(f'Erreur Word : {r1.stderr[:200]}', 'danger')
                return redirect(url_for('cer.voir', id=id))

            # 3. Convertir Word → PDF via LibreOffice
            r2 = subprocess.run(
                ['libreoffice', '--headless', '--convert-to', 'pdf',
                 '--outdir', tmpdir, docx_path],
                capture_output=True, text=True, timeout=90
            )

            pdf_path = os.path.join(tmpdir, 'cer.pdf')
            if not os.path.exists(pdf_path):
                flash('Erreur conversion PDF. Télécharge le Word.', 'warning')
                return redirect(url_for('cer.voir', id=id))

            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()

            nom = f"CER_{cer.titre_prosit[:30].replace(' ', '_')}.pdf"
            return Response(
                pdf_bytes,
                mimetype='application/pdf',
                headers={
                    'Content-Disposition': f'attachment; filename="{nom}"',
                    'Content-Length': len(pdf_bytes)
                }
            )
    except Exception as e:
        flash(f'Erreur : {str(e)}', 'danger')
        return redirect(url_for('cer.voir', id=id))
# ─── Exporter en Word ─────────────────────────────────────────────────────────
@cer_bp.route('/export-word/<int:id>')
def export_word(id):
    cer = db.session.get(SessionCER, id)
    if not cer:
        flash('CER introuvable.', 'danger')
        return redirect(url_for('cer.index'))

    try:
        import subprocess, tempfile, json as json_lib

        realisation_data = {}
        if cer.realisation:
            try: realisation_data = json_lib.loads(cer.realisation)
            except: pass

        cer_data = {
            "titre_prosit":  cer.titre_prosit,
            "etudiant":      cer.etudiant or "",
            "pilote":        cer.pilote or "",
            "copilote":      cer.copilote or "",
            "promotion":     cer.promotion or "",
            "annee":         cer.annee or "",
            "contexte":      cer.contexte or "",
            "besoins":       cer.besoins or "",
            "contraintes":   cer.contraintes or "",
            "problematique": cer.problematique or "",
            "plan":          cer.get_plan_action(),
            "realisation":   realisation_data,
            "validation":    cer.validation or "",
            "conclusion":    cer.conclusion or "",
            "bilan":         cer.bilan or "",
            "synthese":      cer.synthese or "",
            "references":    cer.references or "",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            data_path   = os.path.join(tmpdir, 'cer_data.json')
            output_path = os.path.join(tmpdir, 'cer_output.docx')

            with open(data_path, 'w', encoding='utf-8') as f:
                json_lib.dump(cer_data, f, ensure_ascii=False)

            result = subprocess.run(
                ['node', '/app/generate_cer.js', data_path, output_path],
                capture_output=True, text=True, timeout=60
            )

            if result.returncode != 0 or not os.path.exists(output_path):
                flash(f'Erreur : {result.stderr[:200]}', 'danger')
                return redirect(url_for('cer.voir', id=id))

            with open(output_path, 'rb') as f:
                docx_bytes = f.read()

            nom = f"CER_{cer.titre_prosit[:30].replace(' ', '_')}.docx"
            return Response(
                docx_bytes,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                headers={
                    'Content-Disposition': f'attachment; filename="{nom}"',
                    'Content-Length': len(docx_bytes)
                }
            )
    except Exception as e:
        flash(f'Erreur : {str(e)}', 'danger')
        return redirect(url_for('cer.voir', id=id))

# @cer_bp.route('/export-word/<int:id>')
# def export_word(id):
#     cer = db.session.get(SessionCER, id)
#     if not cer:
#         flash('CER introuvable.', 'danger')
#         return redirect(url_for('cer.index'))

#     try:
#         from docx import Document as DocxDocument
#         from docx.shared import Pt, RGBColor, Inches
#         from docx.enum.text import WD_ALIGN_PARAGRAPH
#         import markdown as md_lib
#         import re

#         doc = DocxDocument()

#         # Style général
#         style = doc.styles['Normal']
#         style.font.name  = 'Calibri'
#         style.font.size  = Pt(12)

#         # ── Page de garde ──────────────────────────────────────────────────
#         p = doc.add_paragraph()
#         p.alignment = WD_ALIGN_PARAGRAPH.CENTER
#         run = p.add_run(cer.titre_prosit.upper())
#         run.bold      = True
#         run.font.size = Pt(20)
#         run.font.color.rgb = RGBColor(180, 0, 0)

#         doc.add_paragraph()
#         p2 = doc.add_paragraph()
#         p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
#         r2 = p2.add_run("Cahier d'Étude et de Recherche")
#         r2.bold = True
#         r2.font.size = Pt(18)

#         doc.add_paragraph()
#         for label, val in [
#             ("Étudiant", cer.etudiant),
#             ("Pilote", cer.pilote),
#             ("Co-pilote", cer.copilote),
#             ("Promotion", cer.promotion),
#             ("Date", cer.created_at.strftime('%d/%m/%Y')),
#         ]:
#             if val:
#                 p3 = doc.add_paragraph()
#                 p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
#                 p3.add_run(f"{label} : ").bold = True
#                 p3.add_run(val)

#         doc.add_page_break()

#         def add_section(title, content, level=1):
#             """Ajoute une section avec son contenu Markdown converti."""
#             if level == 1:
#                 h = doc.add_heading(title, level=1)
#                 h.runs[0].font.color.rgb = RGBColor(180, 0, 0)
#             else:
#                 doc.add_heading(title, level=level)

#             if not content:
#                 return

#             # Parser le Markdown simplement
#             lines = content.split('\n')
#             in_code = False
#             in_list = False

#             for line in lines:
#                 stripped = line.strip()

#                 if stripped.startswith('```'):
#                     in_code = not in_code
#                     continue

#                 if in_code:
#                     p = doc.add_paragraph(stripped, style='No Spacing')
#                     for run in p.runs:
#                         run.font.name = 'Courier New'
#                         run.font.size = Pt(10)
#                     continue

#                 if stripped.startswith('### '):
#                     doc.add_heading(stripped[4:], level=3)
#                 elif stripped.startswith('## '):
#                     doc.add_heading(stripped[3:], level=2)
#                 elif stripped.startswith('# '):
#                     doc.add_heading(stripped[2:], level=2)
#                 elif re.match(r'^[-*+] ', stripped):
#                     p = doc.add_paragraph(
#                         stripped[2:], style='List Bullet'
#                     )
#                 elif re.match(r'^\d+\. ', stripped):
#                     p = doc.add_paragraph(
#                         re.sub(r'^\d+\.\s+', '', stripped),
#                         style='List Number'
#                     )
#                 elif stripped.startswith('|'):
#                     # Tableau : ignorer pour l'instant
#                     pass
#                 elif stripped:
#                     # Texte normal avec gras/italique
#                     p = doc.add_paragraph()
#                     parts = re.split(r'(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)', stripped)
#                     for part in parts:
#                         if part.startswith('**') and part.endswith('**'):
#                             run = p.add_run(part[2:-2])
#                             run.bold = True
#                         elif part.startswith('*') and part.endswith('*'):
#                             run = p.add_run(part[1:-1])
#                             run.italic = True
#                         elif part.startswith('`') and part.endswith('`'):
#                             run = p.add_run(part[1:-1])
#                             run.font.name = 'Courier New'
#                             run.font.size = Pt(10)
#                         else:
#                             p.add_run(part)

#         plan = cer.get_plan_action()

#         # I. Contexte
#         add_section("I. Analyse du contexte", cer.contexte)

#         # II. Besoins
#         add_section("II. Analyse des besoins", "")
#         add_section("Besoins", cer.besoins, level=2)
#         if cer.contraintes:
#             add_section("Contraintes", cer.contraintes, level=2)

#         # III. Problématique
#         add_section("III. Définition de la problématique", cer.problematique)

#         # IV. Plan d'action
#         add_section("IV. Plan d'action", "")
#         for i, etape in enumerate(plan):
#             p = doc.add_paragraph(f"{i+1}. {etape}", style='List Number')

#         # V. Réalisation
#         add_section("V. Réalisation du plan d'action", "")
#         if cer.realisation:
#             try:
#                 real = json.loads(cer.realisation)
#                 for i, etape in enumerate(plan):
#                     contenu = real.get(str(i), '')
#                     add_section(f"V.{i+1} {etape}", contenu, level=2)
#             except Exception:
#                 add_section("", cer.realisation, level=2)

#         # VI. Validation
#         add_section("VI. Validation des pistes de solutions",
#                     cer.validation or '')

#         # VII. Conclusion
#         add_section("VII. Conclusion et retours sur les objectifs",
#                     cer.conclusion or '')

#         # VIII. Bilan
#         add_section("VIII. Bilan critique du travail effectué",
#                     cer.bilan or '')

#         # IX. Synthèse
#         add_section("IX. Synthèse des résultats obtenus",
#                     cer.synthese or '')

#         # X. Références
#         add_section("X. Références bibliographiques",
#                     cer.references or '')

#         # Sauvegarder
#         tmp = tempfile.NamedTemporaryFile(
#             suffix='.docx', delete=False
#         )
#         doc.save(tmp.name)
#         tmp.close()

#         nom = f"CER_{cer.titre_prosit[:30].replace(' ', '_')}.docx"
#         return send_file(
#             tmp.name,
#             as_attachment=True,
#             download_name=nom,
#             mimetype='application/vnd.openxmlformats-officedocument'
#                      '.wordprocessingml.document'
#         )

#     except Exception as e:
#         flash(f'Erreur génération Word : {str(e)}', 'danger')
#         return redirect(url_for('cer.voir', id=id))


# ─── Supprimer un CER ─────────────────────────────────────────────────────────
@cer_bp.route('/supprimer/<int:id>', methods=['POST'])
def supprimer(id):
    cer = db.session.get(SessionCER, id)
    if cer:
        db.session.delete(cer)
        db.session.commit()
        flash('🗑️ CER supprimé.', 'warning')
    return redirect(url_for('cer.index'))