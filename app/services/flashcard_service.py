# app/services/flashcard_service.py
import json
import re
from app.services.ai_errors import safe_chat_completion


def generer_flashcards(cours: str, titre: str, nb: int = 12) -> list:
    """Génère des flashcards question/réponse via Groq à partir d'un cours.

    Retourne une liste de dicts {question, reponse}, filtrée pour ne garder
    que les entrées bien formées (même robustesse que generer_quiz).
    """
    prompt = f"""Tu es un professeur qui crée des flashcards de révision.

Voici un cours sur "{titre}" :
---
{cours[:6000]}
---

Génère exactement {nb} flashcards de révision (question courte / réponse courte)
qui couvrent les notions clés du cours, du plus simple au plus subtil.

RÈGLES :
1. Question concise (une phrase, orientée rappel actif — pas de QCM)
2. Réponse courte et précise (1-3 phrases max)
3. Couvre des notions différentes, pas de doublons
4. Réponds UNIQUEMENT avec un tableau JSON valide, sans texte avant/après,
   sans balises markdown

Format exact :
[
  {{"question": "Qu'est-ce que X ?", "reponse": "X est..."}}
]
"""

    response = safe_chat_completion(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Tu es un générateur de flashcards JSON. "
                    "Tu réponds UNIQUEMENT avec du JSON valide."
                )
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        max_tokens=3000,
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    raw = raw.strip()

    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if match:
        raw = match.group(0)

    cartes = json.loads(raw)

    cleaned = []
    for c in cartes:
        if (isinstance(c, dict)
                and isinstance(c.get('question'), str) and c['question'].strip()
                and isinstance(c.get('reponse'), str) and c['reponse'].strip()):
            cleaned.append({
                'question': c['question'].strip(),
                'reponse':  c['reponse'].strip(),
            })

    return cleaned
