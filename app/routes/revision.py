import os
import json
import uuid
import fitz  # PyMuPDF pour extraire le texte des PDFs
from datetime import datetime, timezone
from flask import (Blueprint, render_template, request,
                   flash, redirect, url_for, jsonify,
                   Response, stream_with_context,
                   session as flask_session)
from app.extensions import db
from app.models import SessionRevision, QuizResult, Flashcard
from app.services.groq_service       import generer_cours_stream, DOMAINES
from app.services.gemini_service     import generer_quiz,     QUIZ_CONFIG
from app.services.flashcard_service  import generer_flashcards
from app.services.ai_errors          import IAError, ai_guard

UTC = timezone.utc
revision_bp = Blueprint('revision', __name__, url_prefix='/revision')
REV_META_MARKER = '\x00__REV_META__'

UPLOAD_FOLDER = '/tmp/allops_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ─── Page d'accueil ───────────────────────────────────────────────────────────
@revision_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    pagination = SessionRevision.query.order_by(
        SessionRevision.created_at.desc()
    ).paginate(page=page, per_page=10, error_out=False)
    return render_template('revision/index.html',
                           title="Révision IA",
                           sessions=pagination.items,
                           pagination=pagination,
                           pagination_endpoint='revision.index',
                           domaines=DOMAINES)


# ─── Générer un cours (streaming) ─────────────────────────────────────────────
@revision_bp.route('/generer', methods=['POST'])
def generer():
    """Génère un cours en streamant le texte au fur et à mesure.

    Même protocole que qa.poser()/cer.generer_section : le flux se termine
    par REV_META_MARKER suivi d'un JSON {ok, id} ou {ok:false, erreur}.
    """
    titre   = request.form.get('titre', '').strip()
    domaine = request.form.get('domaine', 'autre')
    fichier = request.files.get('fichier')

    if not titre:
        return jsonify({'erreur': 'Le titre du cours est obligatoire.'}), 400

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

    guard = ai_guard(f'revision-generer:{request.remote_addr}')
    try:
        guard.__enter__()
    except IAError as e:
        return jsonify({'erreur': str(e)}), 503

    def generate():
        fragments = []
        try:
            for delta in generer_cours_stream(titre, domaine, contenu_source):
                fragments.append(delta)
                yield delta

            cours = ''.join(fragments)
            session_obj = SessionRevision(
                titre          = titre,
                domaine        = domaine,
                contenu_source = contenu_source,
                cours_genere   = cours,
            )
            db.session.add(session_obj)
            db.session.commit()
            yield REV_META_MARKER + json.dumps({'ok': True, 'id': session_obj.id})

        except IAError as e:
            yield REV_META_MARKER + json.dumps({'ok': False, 'erreur': str(e)})
        except Exception as e:
            yield REV_META_MARKER + json.dumps({'ok': False, 'erreur': str(e)})
        finally:
            guard.__exit__(None, None, None)

    return Response(stream_with_context(generate()),
                    mimetype='text/plain; charset=utf-8')


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


@revision_bp.route('/<int:id>/partager', methods=['POST'])
def partager(id):
    session_obj = db.session.get(SessionRevision, id)
    if not session_obj:
        return jsonify({'erreur': 'Session introuvable'}), 404

    if not session_obj.share_token:
        session_obj.share_token = uuid.uuid4().hex
        db.session.commit()

    return jsonify({
        'ok':  True,
        'url': url_for('partage.cours_public',
                       token=session_obj.share_token, _external=True),
    })


# ─── Générer un quiz (AJAX) ───────────────────────────────────────────────────
@revision_bp.route('/generer-quiz/<int:id>', methods=['POST'])
def generer_quiz_route(id):
    session_obj = db.session.get(SessionRevision, id)
    if not session_obj:
        return jsonify({'erreur': 'Session introuvable'}), 404

    niveau = int(request.json.get('niveau', 1))
    niveau = max(1, min(10, niveau))

    try:
        with ai_guard(f'revision-quiz:{id}'):
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
    except IAError as e:
        return jsonify({'erreur': str(e)}), 503
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


# ─── Suivi de progression (scores de quiz dans le temps) ─────────────────────
@revision_bp.route('/progression')
def progression():
    resultats = (
        QuizResult.query
        .join(SessionRevision)
        .order_by(QuizResult.created_at.asc())
        .all()
    )

    points = []
    for r in resultats:
        pct = round((r.score / r.total) * 100, 1) if r.total else 0
        points.append({
            'date': r.created_at,
            'pct': pct,
            'titre': r.session.titre,
            'domaine': r.session.domaine,
            'niveau': r.session.niveau_quiz,
        })

    # Coordonnées SVG précalculées (viewBox 0..100 x 0..100, trait non mis à l'échelle)
    n = len(points)
    for i, p in enumerate(points):
        p['x'] = round((i / (n - 1)) * 100, 2) if n > 1 else 50.0
        p['y'] = round(100 - p['pct'], 2)  # inversé : 0% en bas, 100% en haut

    polyline = ' '.join(f"{p['x']},{p['y']}" for p in points)

    # Statistiques agrégées
    moyenne_globale = round(sum(p['pct'] for p in points) / n, 1) if n else 0
    par_domaine = {}
    for p in points:
        par_domaine.setdefault(p['domaine'], []).append(p['pct'])
    moyenne_par_domaine = {
        dom: round(sum(vals) / len(vals), 1)
        for dom, vals in par_domaine.items()
    }

    return render_template('revision/progression.html',
                           title="Progression",
                           points=points,
                           polyline=polyline,
                           moyenne_globale=moyenne_globale,
                           moyenne_par_domaine=moyenne_par_domaine,
                           domaines=DOMAINES,
                           nb_quiz=n)


# ─── Flashcards (révision espacée, système de Leitner) ───────────────────────
@revision_bp.route('/<int:id>/flashcards/generer', methods=['POST'])
def flashcards_generer(id):
    session_obj = db.session.get(SessionRevision, id)
    if not session_obj:
        return jsonify({'erreur': 'Session introuvable'}), 404

    if Flashcard.query.filter_by(session_id=id).count() > 0:
        return jsonify({'erreur': 'Des flashcards existent déjà pour ce cours.'}), 400

    try:
        with ai_guard(f'revision-flashcards:{id}'):
            cartes = generer_flashcards(session_obj.cours_genere, session_obj.titre)

            if not cartes:
                return jsonify({'erreur': "L'IA n'a pas pu générer de flashcards. Réessaie."}), 500

            for c in cartes:
                db.session.add(Flashcard(
                    session_id=id,
                    question=c['question'],
                    reponse=c['reponse'],
                ))
            db.session.commit()

            return jsonify({'ok': True, 'nb': len(cartes)})

    except IAError as e:
        return jsonify({'erreur': str(e)}), 503
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500


@revision_bp.route('/<int:id>/flashcards')
def flashcards_reviser(id):
    session_obj = db.session.get(SessionRevision, id)
    if not session_obj:
        flash('Session introuvable.', 'danger')
        return redirect(url_for('revision.index'))

    today = datetime.now(UTC).date()
    total = Flashcard.query.filter_by(session_id=id).count()
    a_revoir = (
        Flashcard.query
        .filter(Flashcard.session_id == id, Flashcard.prochaine_revision <= today)
        .order_by(Flashcard.prochaine_revision)
        .all()
    )

    return render_template('revision/flashcards.html',
                           title=f"Flashcards — {session_obj.titre}",
                           session_obj=session_obj,
                           total=total,
                           a_revoir=a_revoir)


@revision_bp.route('/flashcards/<int:fid>/repondre', methods=['POST'])
def flashcards_repondre(fid):
    carte = db.session.get(Flashcard, fid)
    if not carte:
        return jsonify({'erreur': 'Carte introuvable'}), 404

    connu = bool((request.json or {}).get('connu'))
    carte.repondre(connu)
    db.session.commit()

    return jsonify({
        'ok':    True,
        'boite': carte.boite,
        'prochaine_revision': carte.prochaine_revision.strftime('%d/%m/%Y'),
    })