# app/routes/correction.py
import os
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from flask import (Blueprint, render_template, request,
                   flash, redirect, url_for, jsonify,
                   send_file, Response)
from app.extensions import db
from app.models import SessionCorrection
from app.services.correction_service import (
    generer_correction,
    generer_resume_notions,
    generer_latex_correction,
    generer_word_correction,
    TYPES_DOC,
)
from app.services.ai_errors import IAError
import fitz

UTC = timezone.utc
correction_bp = Blueprint('correction', __name__,
                           url_prefix='/correction')


# ─── Accueil ──────────────────────────────────────────────────────────────────
@correction_bp.route('/')
def index():
    sessions = SessionCorrection.query.order_by(
        SessionCorrection.created_at.desc()
    ).limit(20).all()
    return render_template('correction/index.html',
                           title="Correction de devoirs",
                           sessions=sessions,
                           types_doc=TYPES_DOC)


# ─── Soumettre ────────────────────────────────────────────────────────────────
@correction_bp.route('/soumettre', methods=['POST'])
def soumettre():
    titre    = request.form.get('titre', '').strip()
    type_doc = request.form.get('type_doc', 'autre')
    fichier  = request.files.get('fichier')
    texte    = request.form.get('texte', '').strip()

    if not titre:
        flash('Le titre est obligatoire.', 'danger')
        return redirect(url_for('correction.index'))

    contenu = ""
    if fichier and fichier.filename:
        name = fichier.filename.lower()
        if name.endswith('.pdf'):
            raw = fichier.read()
            doc = fitz.open(stream=raw, filetype="pdf")
            for page in doc:
                contenu += page.get_text()
            doc.close()
        elif name.endswith(('.txt', '.md')):
            contenu = fichier.read().decode('utf-8', errors='ignore')
        contenu = contenu[:8000]
    elif texte:
        contenu = texte[:8000]

    if not contenu:
        flash('Fournis un fichier ou du texte à corriger.', 'danger')
        return redirect(url_for('correction.index'))

    session_obj = SessionCorrection(
        titre=titre,
        type_doc=type_doc,
        contenu_source=contenu,
        statut='en_attente'
    )
    db.session.add(session_obj)
    db.session.commit()

    return redirect(url_for('correction.corriger', id=session_obj.id))


# ─── Générer la correction ────────────────────────────────────────────────────
@correction_bp.route('/corriger/<int:id>')
def corriger(id):
    session_obj = db.session.get(SessionCorrection, id)
    if not session_obj:
        flash('Session introuvable.', 'danger')
        return redirect(url_for('correction.index'))

    try:
        corrections = generer_correction(
            session_obj.contenu_source,
            session_obj.titre,
            session_obj.type_doc
        )

        if not corrections:
            flash('L\'IA n\'a pas pu générer de correction. Réessaie.', 'warning')
            session_obj.statut = 'erreur'
            db.session.commit()
            return redirect(url_for('correction.index'))

        resume = generer_resume_notions(corrections, session_obj.titre)

        session_obj.correction = json.dumps({
            'items':  corrections,
            'resume': resume,
        }, ensure_ascii=False)
        session_obj.statut = 'corrige'
        db.session.commit()

    except IAError as e:
        flash(str(e), 'danger')
        session_obj.statut = 'erreur'
        db.session.commit()
        return redirect(url_for('correction.index'))
    except Exception as e:
        flash(f'Erreur lors de la correction : {str(e)}', 'danger')
        session_obj.statut = 'erreur'
        db.session.commit()
        return redirect(url_for('correction.index'))

    return redirect(url_for('correction.voir', id=id))


# ─── Voir la correction ───────────────────────────────────────────────────────
@correction_bp.route('/voir/<int:id>')
def voir(id):
    session_obj = db.session.get(SessionCorrection, id)
    if not session_obj:
        flash('Session introuvable.', 'danger')
        return redirect(url_for('correction.index'))

    corrections = []
    resume = ""

    if session_obj.correction:
        try:
            data        = json.loads(session_obj.correction)
            corrections = data.get('items', [])
            resume      = data.get('resume', '')
        except Exception:
            pass

    return render_template('correction/resultat.html',
                           title=f"Correction — {session_obj.titre}",
                           session_obj=session_obj,
                           corrections=corrections,
                           resume=resume,
                           types_doc=TYPES_DOC)


# ─── Export LaTeX ─────────────────────────────────────────────────────────────
@correction_bp.route('/export/latex/<int:id>')
def export_latex(id):
    session_obj = db.session.get(SessionCorrection, id)
    if not session_obj:
        flash('Session introuvable.', 'danger')
        return redirect(url_for('correction.index'))

    try:
        data        = json.loads(session_obj.correction or '{}')
        corrections = data.get('items', [])
        resume      = data.get('resume', '')

        latex = generer_latex_correction(
            corrections,
            session_obj.titre,
            session_obj.type_doc,
            resume
        )

        nom = f"Corrige_{session_obj.titre[:30].replace(' ', '_')}.tex"
        return Response(
            latex,
            mimetype='text/plain; charset=utf-8',
            headers={
                'Content-Disposition': f'attachment; filename="{nom}"'
            }
        )
    except Exception as e:
        flash(f'Erreur export LaTeX : {str(e)}', 'danger')
        return redirect(url_for('correction.voir', id=id))


# ─── Export PDF (LaTeX → LibreOffice via Word) ────────────────────────────────
@correction_bp.route('/export/pdf/<int:id>')
def export_pdf(id):
    session_obj = db.session.get(SessionCorrection, id)
    if not session_obj:
        flash('Session introuvable.', 'danger')
        return redirect(url_for('correction.index'))

    try:
        data        = json.loads(session_obj.correction or '{}')
        corrections = data.get('items', [])
        resume      = data.get('resume', '')

        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = os.path.join(tmpdir, 'corrige.docx')
            pdf_path  = os.path.join(tmpdir, 'corrige.pdf')

            # 1. Générer Word
            ok = generer_word_correction(
                corrections,
                session_obj.titre,
                session_obj.type_doc,
                resume,
                docx_path
            )
            if not ok:
                flash('Erreur génération Word intermédiaire.', 'danger')
                return redirect(url_for('correction.voir', id=id))

            # 2. Convertir Word → PDF via LibreOffice
            subprocess.run(
                ['libreoffice', '--headless', '--convert-to', 'pdf',
                 '--outdir', tmpdir, docx_path],
                capture_output=True, timeout=90
            )

            if not os.path.exists(pdf_path):
                flash('Erreur conversion PDF. Télécharge le .tex.', 'warning')
                return redirect(url_for('correction.voir', id=id))

            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()

        nom = f"Corrige_{session_obj.titre[:30].replace(' ', '_')}.pdf"
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{nom}"',
                'Content-Length': len(pdf_bytes)
            }
        )
    except Exception as e:
        flash(f'Erreur export PDF : {str(e)}', 'danger')
        return redirect(url_for('correction.voir', id=id))


# ─── Export Word ──────────────────────────────────────────────────────────────
@correction_bp.route('/export/word/<int:id>')
def export_word(id):
    session_obj = db.session.get(SessionCorrection, id)
    if not session_obj:
        flash('Session introuvable.', 'danger')
        return redirect(url_for('correction.index'))

    try:
        data        = json.loads(session_obj.correction or '{}')
        corrections = data.get('items', [])
        resume      = data.get('resume', '')

        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = os.path.join(tmpdir, 'corrige.docx')

            ok = generer_word_correction(
                corrections,
                session_obj.titre,
                session_obj.type_doc,
                resume,
                docx_path
            )

            if not ok or not os.path.exists(docx_path):
                flash('Erreur génération Word.', 'danger')
                return redirect(url_for('correction.voir', id=id))

            with open(docx_path, 'rb') as f:
                docx_bytes = f.read()

        nom = f"Corrige_{session_obj.titre[:30].replace(' ', '_')}.docx"
        return Response(
            docx_bytes,
            mimetype='application/vnd.openxmlformats-officedocument'
                     '.wordprocessingml.document',
            headers={
                'Content-Disposition': f'attachment; filename="{nom}"',
                'Content-Length': len(docx_bytes)
            }
        )
    except Exception as e:
        flash(f'Erreur export Word : {str(e)}', 'danger')
        return redirect(url_for('correction.voir', id=id))


# ─── Supprimer ────────────────────────────────────────────────────────────────
@correction_bp.route('/supprimer/<int:id>', methods=['POST'])
def supprimer(id):
    s = db.session.get(SessionCorrection, id)
    if s:
        db.session.delete(s)
        db.session.commit()
        flash('Session supprimée.', 'warning')
    return redirect(url_for('correction.index'))