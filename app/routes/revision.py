import os
import json
import fitz  # PyMuPDF pour extraire le texte des PDFs
from datetime import datetime, timezone
from flask import (Blueprint, render_template, request,
                   flash, redirect, url_for, jsonify,
                   session as flask_session)
from app.extensions import db
from app.models import SessionRevision, QuizResult
from app.services.groq_service   import generer_cours,   DOMAINES
from app.services.gemini_service import generer_quiz,     QUIZ_CONFIG

UTC = timezone.utc
revision_bp = Blueprint('revision', __name__, url_prefix='/revision')

UPLOAD_FOLDER = '/tmp/allops_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ─── Page d'accueil ───────────────────────────────────────────────────────────
@revision_bp.route('/')
def index():
    sessions = SessionRevision.query.order_by(
        SessionRevision.created_at.desc()
    ).limit(10).all()
    return render_template('revision/index.html',
                           title="Révision IA",
                           sessions=sessions,
                           domaines=DOMAINES)


# ─── Générer un cours ─────────────────────────────────────────────────────────
@revision_bp.route('/generer', methods=['POST'])
def generer():
    titre   = request.form.get('titre', '').strip()
    domaine = request.form.get('domaine', 'autre')
    fichier = request.files.get('fichier')

    if not titre:
        flash('Le titre du cours est obligatoire.', 'danger')
        return redirect(url_for('revision.index'))

    # Extraire le contenu du fichier si fourni
    contenu_source = ""
    if fichier and fichier.filename:
        filename = fichier.filename.lower()

        if filename.endswith('.pdf'):
            # Extraction PDF avec PyMuPDF
            pdf_bytes = fichier.read()
            doc       = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                contenu_source += page.get_text()
            doc.close()

        elif filename.endswith(('.txt', '.md')):
            contenu_source = fichier.read().decode('utf-8', errors='ignore')

        # Limiter à 6000 caractères
        contenu_source = contenu_source[:6000]

    try:
        # Générer le cours avec Groq
        cours = generer_cours(titre, domaine, contenu_source)

        # Sauvegarder en base
        session_obj = SessionRevision(
            titre          = titre,
            domaine        = domaine,
            contenu_source = contenu_source,
            cours_genere   = cours,
        )
        db.session.add(session_obj)
        db.session.commit()

        return redirect(url_for('revision.voir_cours',
                                id=session_obj.id))

    except Exception as e:
        flash(f'Erreur lors de la génération : {str(e)}', 'danger')
        return redirect(url_for('revision.index'))


# ─── Voir un cours ────────────────────────────────────────────────────────────
@revision_bp.route('/cours/<int:id>')
def voir_cours(id):
    session_obj = db.session.get(SessionRevision, id)
    if not session_obj:
        flash('Session introuvable.', 'danger')
        return redirect(url_for('revision.index'))

    # Convertir Markdown → HTML
    import markdown as md
    cours_html = md.markdown(
        session_obj.cours_genere or '',
        extensions=['extra', 'codehilite', 'toc']
    )

    return render_template('revision/cours.html',
                           title=session_obj.titre,
                           session_obj=session_obj,
                           cours_html=cours_html,
                           quiz_config=QUIZ_CONFIG)


# ─── Générer un quiz (AJAX) ───────────────────────────────────────────────────
# @revision_bp.route('/generer-quiz/<int:id>', methods=['POST'])
# def generer_quiz_route(id):
#     session_obj = db.session.get(SessionRevision, id)
#     if not session_obj:
#         return jsonify({'erreur': 'Session introuvable'}), 404

#     niveau = int(request.json.get('niveau', 1))
#     niveau = max(1, min(10, niveau))

#     try:
#         questions = generer_quiz(
#             session_obj.cours_genere,
#             session_obj.titre,
#             niveau
#         )

#         # Mettre à jour le niveau
#         session_obj.niveau_quiz = niveau
#         db.session.commit()

#         return jsonify({
#             'ok':        True,
#             'questions': questions,
#             'niveau':    niveau,
#             'titre':     session_obj.titre
#         })

#     except Exception as e:
#         return jsonify({'erreur': str(e)}), 500
@revision_bp.route('/generer-quiz/<int:id>', methods=['POST'])
def generer_quiz_route(id):
    session_obj = db.session.get(SessionRevision, id)
    if not session_obj:
        return jsonify({'erreur': 'Session introuvable'}), 404

    niveau = int(request.json.get('niveau', 1))
    niveau = max(1, min(10, niveau))

    try:
        questions = generer_quiz(
            session_obj.cours_genere,
            session_obj.titre,
            niveau
        )

        if not questions:
            return jsonify({
                'erreur': 'Le modèle n\'a pas pu générer de questions valides. '
                          'Réessaie.'
            }), 500

        session_obj.niveau_quiz = niveau
        db.session.commit()

        return jsonify({
            'ok':        True,
            'questions': questions,
            'niveau':    niveau,
            'titre':     session_obj.titre
        })

    except json.JSONDecodeError:
        return jsonify({
            'erreur': 'Erreur de parsing JSON. Réessaie dans quelques secondes.'
        }), 500
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500


# ─── Sauvegarder le résultat du quiz ─────────────────────────────────────────
@revision_bp.route('/sauvegarder-quiz/<int:id>', methods=['POST'])
def sauvegarder_quiz(id):
    data = request.json

    result = QuizResult(
        session_id = id,
        score      = data.get('score', 0),
        total      = data.get('total', 0),
        temps_sec  = data.get('temps', 0),
        details    = json.dumps(data.get('details', []))
    )
    db.session.add(result)
    db.session.commit()

    return jsonify({'ok': True, 'id': result.id})


# ─── Supprimer une session ────────────────────────────────────────────────────
@revision_bp.route('/supprimer/<int:id>', methods=['POST'])
def supprimer(id):
    session_obj = db.session.get(SessionRevision, id)
    if session_obj:
        db.session.delete(session_obj)
        db.session.commit()
        flash('Session supprimée.', 'warning')
    return redirect(url_for('revision.index'))