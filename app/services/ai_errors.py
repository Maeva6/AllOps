# app/services/ai_errors.py
"""
Gestion centralisée des erreurs des services IA (Groq).

Toutes les erreurs remontées par le SDK (clé absente, quota dépassé,
réseau, JSON invalide...) sont converties en IAError avec un message
en français compréhensible par un·e étudiant·e, plutôt que la trace
brute de l'exception d'origine.
"""
import os
import json
from groq import Groq

_client = None


class IAError(Exception):
    """Erreur métier lisible destinée à être affichée à l'utilisateur."""


def get_groq_client() -> Groq:
    """Retourne le client Groq partagé, initialisé une seule fois.

    Lève IAError immédiatement si GROQ_API_KEY n'est pas configurée,
    plutôt que de laisser l'appel API échouer plus tard avec un
    message opaque.
    """
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise IAError(
                "Le service IA n'est pas configuré : la variable "
                "GROQ_API_KEY est manquante. Ajoute-la dans le fichier .env "
                "puis redémarre l'application."
            )
        _client = Groq(api_key=api_key)
    return _client


def safe_chat_completion(**kwargs):
    """Appelle client.chat.completions.create en traduisant les erreurs.

    Centralise le try/except pour tous les appels Groq de l'application :
    une seule implémentation à maintenir, un seul format de message d'erreur.
    """
    client = get_groq_client()
    try:
        return client.chat.completions.create(**kwargs)
    except IAError:
        raise
    except Exception as exc:
        raise _translate(exc) from exc


def _translate(exc: Exception) -> IAError:
    name = type(exc).__name__
    text = str(exc).lower()

    if 'authenticationerror' in name.lower() or '401' in text or 'invalid api key' in text:
        return IAError(
            "La clé GROQ_API_KEY est invalide ou expirée. "
            "Vérifie sa valeur dans le fichier .env."
        )
    if 'ratelimit' in name.lower() or '429' in text:
        return IAError(
            "Le service IA a atteint sa limite de requêtes (quota Groq). "
            "Réessaie dans quelques instants."
        )
    if 'connectionerror' in name.lower() or 'timeout' in name.lower() or 'connect' in text:
        return IAError(
            "Impossible de joindre le service IA (problème réseau). "
            "Réessaie plus tard."
        )
    if isinstance(exc, json.JSONDecodeError):
        return IAError(
            "La réponse de l'IA n'a pas pu être interprétée (format invalide). "
            "Réessaie."
        )
    return IAError(f"Le service IA a rencontré une erreur inattendue : {exc}")
