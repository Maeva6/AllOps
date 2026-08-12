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
import logging
import threading
import time
from contextlib import contextmanager
from groq import Groq
from flask import current_app

_client = None
_fallback_logger = logging.getLogger(__name__)
_guard_lock = threading.Lock()
_active_keys = {}  # clé de ressource -> timestamp de début (time.monotonic)


class IAError(Exception):
    """Erreur métier lisible destinée à être affichée à l'utilisateur."""


def _logger():
    """Renvoie app.logger si un contexte Flask est actif, sinon un logger standard."""
    try:
        return current_app.logger
    except RuntimeError:
        return _fallback_logger


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
            _logger().warning("Appel IA refusé : GROQ_API_KEY absente.")
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
        _logger().error(
            "Appel Groq échoué (model=%s) : %s: %s",
            kwargs.get('model'), type(exc).__name__, exc
        )
        raise _translate(exc) from exc


def stream_chat_completion(**kwargs):
    """Générateur streaming équivalent de safe_chat_completion.

    Yield des fragments de texte (str) au fur et à mesure de la réponse
    Groq, pour un affichage progressif côté client plutôt que d'attendre
    la réponse complète. Toute erreur est traduite en IAError, comme
    safe_chat_completion.
    """
    client = get_groq_client()
    try:
        stream = client.chat.completions.create(stream=True, **kwargs)
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except IAError:
        raise
    except Exception as exc:
        _logger().error(
            "Appel Groq (stream) échoué (model=%s) : %s: %s",
            kwargs.get('model'), type(exc).__name__, exc
        )
        raise _translate(exc) from exc


@contextmanager
def ai_guard(key: str, max_age: float = 120.0):
    """Empêche deux générations IA concurrentes sur la même ressource.

    Protège contre le double-clic, les onglets multiples ou un script qui
    spamme un endpoint : une seconde requête sur la même `key` pendant
    qu'une première est en cours reçoit une IAError immédiate plutôt que
    de consommer un appel Groq supplémentaire. `max_age` évite qu'une
    entrée reste bloquée indéfiniment si un worker meurt sans nettoyer
    (ex: kill -9, timeout upstream).
    """
    with _guard_lock:
        now = time.monotonic()
        started = _active_keys.get(key)
        if started is not None and (now - started) < max_age:
            raise IAError(
                "Une génération IA est déjà en cours pour cet élément. "
                "Patiente qu'elle se termine avant de relancer."
            )
        _active_keys[key] = now
    try:
        yield
    finally:
        with _guard_lock:
            _active_keys.pop(key, None)


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
