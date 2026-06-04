# # app/services/gemini_service.py
# import os
# import json
# import re
# import google.generativeai as genai

# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# model = genai.GenerativeModel("gemini-2.0-flash")

# # Config par niveau de quiz
# QUIZ_CONFIG = {
#     1:  {"nb": 5,  "diff": "très facile, questions de compréhension de base"},
#     2:  {"nb": 5,  "diff": "facile, questions directes sur les définitions"},
#     3:  {"nb": 8,  "diff": "facile-moyen, questions de compréhension"},
#     4:  {"nb": 8,  "diff": "moyen, questions d'application"},
#     5:  {"nb": 10, "diff": "moyen, questions d'analyse"},
#     6:  {"nb": 10, "diff": "moyen-difficile, questions d'analyse approfondie"},
#     7:  {"nb": 12, "diff": "difficile, questions de synthèse"},
#     8:  {"nb": 12, "diff": "difficile, questions de cas pratiques"},
#     9:  {"nb": 15, "diff": "très difficile, questions d'évaluation critique"},
#     10: {"nb": 15, "diff": "expert, questions d'expertise avancée"},
# }


# def generer_quiz(cours: str, titre: str,
#                  niveau: int = 1) -> list:
#     """
#     Génère un quiz QCM structuré depuis le cours via Gemini.
#     Retourne une liste de questions JSON.
#     """
#     cfg = QUIZ_CONFIG.get(niveau, QUIZ_CONFIG[5])

#     prompt = f"""Tu es un expert en création de quiz pédagogiques.

# Voici un cours sur le sujet "{titre}" :

# ---
# {cours[:8000]}
# ---

# Génère exactement {cfg['nb']} questions QCM de niveau : {cfg['diff']}.

# RÈGLES ABSOLUES :
# 1. Chaque question doit avoir exactement 4 réponses
# 2. Une seule réponse correcte par question
# 3. Les mauvaises réponses doivent être plausibles (pas trop faciles à éliminer)
# 4. Les questions doivent couvrir différentes parties du cours
# 5. Inclure une explication courte (2 phrases max) pour la bonne réponse

# Réponds UNIQUEMENT avec un JSON valide, sans texte avant ni après,
# sans balises markdown, sans ```json :

# [
#   {{
#     "question": "La question ici ?",
#     "choices": ["Réponse A", "Réponse B", "Réponse C", "Réponse D"],
#     "correct": 0,
#     "explanation": "Explication courte de la bonne réponse."
#   }}
# ]

# Le champ "correct" est l'INDEX (0-3) de la bonne réponse dans "choices".
# """

#     response = model.generate_content(prompt)
#     raw      = response.text.strip()

#     # Nettoyage robuste du JSON
#     raw = re.sub(r'^```(?:json)?\s*', '', raw)
#     raw = re.sub(r'\s*```$',         '', raw)
#     raw = raw.strip()

#     # Trouver le tableau JSON
#     match = re.search(r'\[.*\]', raw, re.DOTALL)
#     if match:
#         raw = match.group(0)

#     questions = json.loads(raw)

#     # Validation et nettoyage
#     cleaned = []
#     for q in questions:
#         if (isinstance(q.get('question'), str) and
#             isinstance(q.get('choices'), list) and
#             len(q['choices']) == 4 and
#             isinstance(q.get('correct'), int) and
#             0 <= q['correct'] <= 3):
#             cleaned.append({
#                 'question':    q['question'],
#                 'choices':     q['choices'][:4],
#                 'correct':     q['correct'],
#                 'explanation': q.get('explanation', '')
#             })

#     return cleaned

# app/services/gemini_service.py
import os
import json
import re
from groq import Groq
import random

# On utilise Groq à la place de Gemini pour éviter les quotas
_client = None

def get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client

QUIZ_CONFIG = {
    1:  {"nb": 5,  "diff": "très facile, questions de compréhension de base"},
    2:  {"nb": 5,  "diff": "facile, questions directes sur les définitions"},
    3:  {"nb": 8,  "diff": "facile-moyen, questions de compréhension"},
    4:  {"nb": 8,  "diff": "moyen, questions d'application"},
    5:  {"nb": 10, "diff": "moyen, questions d'analyse"},
    6:  {"nb": 10, "diff": "moyen-difficile, questions d'analyse approfondie"},
    7:  {"nb": 12, "diff": "difficile, questions de synthèse"},
    8:  {"nb": 12, "diff": "difficile, questions de cas pratiques"},
    9:  {"nb": 15, "diff": "très difficile, questions d'évaluation critique"},
    10: {"nb": 15, "diff": "expert, questions d'expertise avancée"},
}


def generer_quiz(cours: str, titre: str, niveau: int = 1) -> list:
    cfg = QUIZ_CONFIG.get(niveau, QUIZ_CONFIG[5])
    
    seed = random.randint(1000, 9999)
    angle = random.choice([
        "Concentre-toi sur les définitions et concepts théoriques.",
        "Concentre-toi sur les applications pratiques et exemples concrets.",
        "Concentre-toi sur les comparaisons entre concepts.",
        "Concentre-toi sur les algorithmes et leur fonctionnement pas à pas.",
        "Concentre-toi sur les cas d'usage et erreurs classiques.",
    ])

    prompt = f"""[Session #{seed}] Tu génères un quiz pédagogique.
Angle pour ce quiz : {angle}
...
{cours[:6000]}
---

Génère exactement {cfg['nb']} questions QCM de niveau : {cfg['diff']}.

RÈGLES ABSOLUES :
1. Chaque question doit avoir exactement 4 réponses
2. Une seule réponse correcte par question
3. Les mauvaises réponses doivent être plausibles
4. Les questions doivent couvrir différentes parties du cours
5. Inclure une explication courte (2 phrases max) pour la bonne réponse

Réponds UNIQUEMENT avec un tableau JSON valide.
Ne mets AUCUN texte avant ou après.
Ne mets PAS de balises ```json```.
Le format exact attendu est :

[
  {{
    "question": "La question ici ?",
    "choices": ["Réponse A", "Réponse B", "Réponse C", "Réponse D"],
    "correct": 0,
    "explanation": "Explication courte de la bonne réponse."
  }}
]

Le champ "correct" est l'INDEX (0-3) de la bonne réponse dans "choices".
Génère exactement {cfg['nb']} questions, pas plus, pas moins.
"""

    response = get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Tu es un générateur de quiz JSON. "
                    "Tu réponds UNIQUEMENT avec du JSON valide, "
                    "jamais avec du texte ou du markdown."
                )
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        max_tokens=4000,
    )

    raw = response.choices[0].message.content.strip()

    # Nettoyage robuste
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$',          '', raw)
    raw = raw.strip()

    # Trouver le tableau JSON
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if match:
        raw = match.group(0)

    questions = json.loads(raw)

    # Validation et nettoyage
    cleaned = []
    for q in questions:
        if (isinstance(q.get('question'), str) and
            isinstance(q.get('choices'), list) and
            len(q['choices']) == 4 and
            isinstance(q.get('correct'), int) and
            0 <= q['correct'] <= 3):
            cleaned.append({
                'question':    q['question'],
                'choices':     q['choices'][:4],
                'correct':     q['correct'],
                'explanation': q.get('explanation', '')
            })

    return cleaned