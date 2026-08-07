import os
import json
import subprocess
import tempfile
from datetime import timezone
from flask import (Blueprint, render_template, request,
                   flash, redirect, url_for, jsonify,
                   send_file, Response)
from app.extensions import db
from app.models import SessionCER
from app.services.cer_service import (
    generer_section_cer,
    generer_latex_complet,
    extraire_texte_fichier,
    extraire_prosit_aller,
    generer_word_cer,
)
from app.services.ai_errors import IAError
import fitz

UTC = timezone.utc
cer_bp = Blueprint('cer', __name__, url_prefix='/cer')


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

    except IAError as e:
        return jsonify({'erreur': str(e)}), 503
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

    except IAError as e:
        return jsonify({'erreur': str(e)}), 503
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