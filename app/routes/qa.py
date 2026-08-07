# app/routes/qa.py
import json
from datetime import datetime, timezone
from flask import (Blueprint, render_template, request,
                   jsonify, Response)
from app.extensions import db
from app.models import SessionQA
from app.services.ai_errors import safe_chat_completion, IAError

UTC = timezone.utc
qa_bp = Blueprint('qa', __name__, url_prefix='/qa')

MODES = {
    'direct':   'Réponse directe et concise',
    'exemple':  'Réponse + exemples concrets',
    'compare':  'Comparaison / différences',
    'resume':   'Résumé en bullet points',
    'schema':   'Réponse + schéma textuel',
}

SYSTEM_PROMPT = """Tu es un professeur assistant expert en informatique, 
mathématiques et sciences appliquées à l'UCAC-ICAM. 
Tu réponds aux questions de cours des étudiants en 3ème année d'ingénierie.

Règles STRICTES :
- Réponses claires, pédagogiques et précises
- JAMAIS trop longues : max 300 mots sauf si la question le nécessite vraiment
- Utilise des exemples concrets quand c'est demandé
- Pour les comparaisons : utilise un format clair (avant/après, différence1 vs différence2)
- Pour les schémas : utilise des caractères ASCII propres
- Réponds TOUJOURS en français
- Formules mathématiques : utilise la notation claire (ex: O(n²), f(x) = ...)
- Code : entoure-le avec des balises ```langage ... ``` 
- Ne commence JAMAIS par "Bien sûr !", "Absolument !", ou des formules creuses
- Va directement à la réponse
"""


@qa_bp.route('/')
def index():
    historique = SessionQA.query.order_by(
        SessionQA.created_at.desc()
    ).limit(30).all()
    return render_template('qa/index.html',
                           title="Questions de cours",
                           historique=historique,
                           modes=MODES)


@qa_bp.route('/poser', methods=['POST'])
def poser():
    """Répondre à une question via Groq (streaming ou normal)."""
    data     = request.json or {}
    question = data.get('question', '').strip()
    mode     = data.get('mode', 'direct')
    matiere  = data.get('matiere', '').strip()

    if not question:
        return jsonify({'erreur': 'Question vide'}), 400
    if len(question) > 1000:
        return jsonify({'erreur': 'Question trop longue (max 1000 caractères)'}), 400

    # Construire le prompt selon le mode
    mode_instructions = {
        'direct':  "Réponds directement et clairement, sans exemples superflus.",
        'exemple': "Réponds puis donne 2-3 exemples concrets et pratiques.",
        'compare': "Structure ta réponse comme une comparaison claire avec les différences clés.",
        'resume':  "Résume en 5-7 bullet points essentiels, chacun en 1 ligne max.",
        'schema':  "Fournis une explication + un schéma ASCII pour illustrer.",
    }
    instruction = mode_instructions.get(mode, mode_instructions['direct'])
    matiere_ctx = f"Matière : {matiere}\n" if matiere else ""

    user_prompt = f"""{matiere_ctx}Question : {question}

Mode de réponse : {instruction}"""

    try:
        response = safe_chat_completion(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt}
            ],
            temperature=0.4,
            max_tokens=800,
        )
        reponse = response.choices[0].message.content.strip()

        # Sauvegarder dans l'historique
        session_qa = SessionQA(
            question=question,
            reponse=reponse,
            mode=mode,
            matiere=matiere,
        )
        db.session.add(session_qa)
        db.session.commit()

        return jsonify({
            'ok':      True,
            'reponse': reponse,
            'id':      session_qa.id,
        })

    except IAError as e:
        return jsonify({'erreur': str(e)}), 503
    except Exception as e:
        return jsonify({'erreur': str(e)}), 500


@qa_bp.route('/question/<int:id>')
def detail(id):
    """Récupérer une question de l'historique."""
    qa = db.session.get(SessionQA, id)
    if not qa:
        return jsonify({'erreur': 'Introuvable'}), 404
    return jsonify({
        'question': qa.question,
        'reponse':  qa.reponse,
        'mode':     qa.mode,
        'matiere':  qa.matiere,
        'date':     qa.created_at.strftime('%d/%m/%Y %H:%M'),
    })


@qa_bp.route('/supprimer/<int:id>', methods=['POST'])
def supprimer(id):
    qa = db.session.get(SessionQA, id)
    if qa:
        db.session.delete(qa)
        db.session.commit()
    return jsonify({'ok': True})


@qa_bp.route('/vider', methods=['POST'])
def vider_historique():
    SessionQA.query.delete()
    db.session.commit()
    return jsonify({'ok': True})