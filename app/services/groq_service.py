# app/services/groq_service.py
from app.services.ai_errors import safe_chat_completion, stream_chat_completion

# Domaines disponibles avec contexte
DOMAINES = {
    "informatique":  "informatique, programmation et développement logiciel",
    "devops":        "DevOps, CI/CD, Docker, Kubernetes et automatisation",
    "mathematiques": "mathématiques (algèbre, analyse, probabilités)",
    "physique":      "physique (mécanique, électricité, thermodynamique)",
    "reseaux":       "réseaux informatiques et protocoles",
    "securite":      "cybersécurité et sécurité informatique",
    "cloud":         "cloud computing (AWS, GCP, Azure)",
    "python":        "programmation Python avancée",
    "autre":         "enseignement général",
}


def _construire_prompt_cours(titre: str, domaine: str, contenu_source: str = "") -> str:
    contexte_domaine = DOMAINES.get(domaine, DOMAINES["autre"])

    if contenu_source:
        prompt = f"""Tu es un professeur expert en {contexte_domaine}.
Un étudiant t'a fourni ce contenu de cours :

---
{contenu_source[:6000]}
---

À partir de ce contenu, génère un cours complet, détaillé et structuré
sur le sujet "{titre}".

Le cours doit :
1. Commencer par un résumé exécutif (3-4 phrases)
2. Être organisé en sections claires avec des titres (## Section)
3. Inclure des exemples concrets et pratiques
4. Expliquer les concepts difficiles avec des analogies simples
5. Terminer par un résumé des points clés à retenir
6. Être rédigé en français, de façon claire et pédagogique
7. Faire entre 800 et 1200 mots

Utilise le format Markdown avec :
- ## pour les sections principales
- ### pour les sous-sections
- **gras** pour les termes importants
- `code` pour les exemples de code ou commandes
- > pour les notes importantes
"""
    else:
        prompt = f"""Tu es un professeur expert en {contexte_domaine}.

Génère un cours complet, détaillé et structuré sur le sujet : "{titre}"

Le cours doit :
1. Commencer par un résumé exécutif (3-4 phrases)
2. Être organisé en sections claires avec des titres (## Section)
3. Inclure des exemples concrets et pratiques
4. Expliquer les concepts difficiles avec des analogies simples
5. Terminer par un résumé des points clés à retenir
6. Être rédigé en français, de façon claire et pédagogique
7. Faire entre 800 et 1200 mots

Utilise le format Markdown avec :
- ## pour les sections principales
- ### pour les sous-sections
- **gras** pour les termes importants
- `code` pour les exemples de code ou commandes
- > pour les notes importantes
"""

    return prompt


def generer_cours(titre: str, domaine: str,
                  contenu_source: str = "") -> str:
    """
    Génère un cours détaillé et structuré via Groq (llama3-70b).
    Retourne du Markdown.
    """
    prompt = _construire_prompt_cours(titre, domaine, contenu_source)

    response = safe_chat_completion(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=3000,
    )

    return response.choices[0].message.content


def generer_cours_stream(titre: str, domaine: str, contenu_source: str = ""):
    """Variante streaming de generer_cours : yield des fragments de texte."""
    prompt = _construire_prompt_cours(titre, domaine, contenu_source)

    yield from stream_chat_completion(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=3000,
    )