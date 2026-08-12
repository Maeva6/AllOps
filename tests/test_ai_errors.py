"""Tests de app/services/ai_errors.py utilisant de vraies classes
d'exception du SDK Groq (AuthenticationError, RateLimitError,
APIConnectionError, APITimeoutError...) plutôt que des IAError
pré-fabriquées, pour vérifier que la traduction des erreurs réseau/quota
réelles produit bien le message attendu — pas seulement le comportement
des routes qui mockent déjà `safe_chat_completion`/`stream_chat_completion`.
"""
import json
import httpx
import groq
import pytest
from unittest.mock import patch, MagicMock

from app.services import ai_errors
from app.services.ai_errors import (
    IAError, get_groq_client, safe_chat_completion,
    stream_chat_completion, _translate,
)


def _requete():
    return httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions')


def _reponse(status_code, message):
    return httpx.Response(
        status_code, request=_requete(), json={'error': {'message': message}}
    )


@pytest.fixture(autouse=True)
def _reset_client_singleton():
    """Le client Groq est mis en cache dans une variable globale du module :
    on la réinitialise avant/après chaque test pour éviter toute pollution
    entre tests (clé API différente, mock résiduel...)."""
    ai_errors._client = None
    yield
    ai_errors._client = None


# ══════════════════════════════════════════════════════════════════════
# get_groq_client
# ══════════════════════════════════════════════════════════════════════

class TestGetGroqClient:

    def test_sans_cle_api_leve_iaerror(self, monkeypatch):
        monkeypatch.delenv('GROQ_API_KEY', raising=False)
        with pytest.raises(IAError, match='GROQ_API_KEY'):
            get_groq_client()

    def test_cle_api_vide_leve_iaerror(self, monkeypatch):
        monkeypatch.setenv('GROQ_API_KEY', '   ')
        with pytest.raises(IAError, match='GROQ_API_KEY'):
            get_groq_client()

    def test_avec_cle_api_renvoie_un_client_groq(self, monkeypatch):
        monkeypatch.setenv('GROQ_API_KEY', 'gsk_test_fake_key')
        client = get_groq_client()
        assert isinstance(client, groq.Groq)

    def test_client_reutilise_le_singleton(self, monkeypatch):
        monkeypatch.setenv('GROQ_API_KEY', 'gsk_test_fake_key')
        assert get_groq_client() is get_groq_client()


# ══════════════════════════════════════════════════════════════════════
# _translate — vraies exceptions du SDK Groq
# ══════════════════════════════════════════════════════════════════════

class TestTranslate:

    def test_authentication_error(self):
        exc = groq.AuthenticationError(
            'Invalid API Key', response=_reponse(401, 'Invalid API Key'), body=None
        )
        erreur = _translate(exc)
        assert isinstance(erreur, IAError)
        assert 'GROQ_API_KEY' in str(erreur)
        assert 'invalide' in str(erreur).lower()

    def test_rate_limit_error(self):
        exc = groq.RateLimitError(
            'Rate limit exceeded', response=_reponse(429, 'Rate limit exceeded'), body=None
        )
        erreur = _translate(exc)
        assert 'quota' in str(erreur).lower()

    def test_api_connection_error(self):
        exc = groq.APIConnectionError(request=_requete())
        erreur = _translate(exc)
        assert 'réseau' in str(erreur).lower()

    def test_api_timeout_error(self):
        exc = groq.APITimeoutError(request=_requete())
        erreur = _translate(exc)
        assert 'réseau' in str(erreur).lower()

    def test_json_decode_error(self):
        exc = json.JSONDecodeError('Expecting value', '{invalide}', 0)
        erreur = _translate(exc)
        assert 'format invalide' in str(erreur).lower()

    def test_erreur_inattendue_fallback(self):
        exc = groq.InternalServerError(
            'Service indisponible', response=_reponse(500, 'Service indisponible'), body=None
        )
        erreur = _translate(exc)
        assert 'erreur inattendue' in str(erreur).lower()


# ══════════════════════════════════════════════════════════════════════
# safe_chat_completion / stream_chat_completion — bout en bout
# ══════════════════════════════════════════════════════════════════════

class TestSafeChatCompletionErreursReelles:

    @patch('app.services.ai_errors.get_groq_client')
    def test_authentification_propage_message_traduit(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = groq.AuthenticationError(
            'Invalid API Key', response=_reponse(401, 'Invalid API Key'), body=None
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(IAError, match='GROQ_API_KEY'):
            safe_chat_completion(model='llama-3.1-8b-instant', messages=[])

    @patch('app.services.ai_errors.get_groq_client')
    def test_rate_limit_propage_message_traduit(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = groq.RateLimitError(
            'Rate limit exceeded', response=_reponse(429, 'Rate limit exceeded'), body=None
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(IAError, match='quota'):
            safe_chat_completion(model='llama-3.1-8b-instant', messages=[])

    @patch('app.services.ai_errors.get_groq_client')
    def test_connexion_propage_message_traduit(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = groq.APIConnectionError(
            request=_requete()
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(IAError, match='réseau'):
            safe_chat_completion(model='llama-3.1-8b-instant', messages=[])


class TestStreamChatCompletionErreursReelles:

    @patch('app.services.ai_errors.get_groq_client')
    def test_timeout_avant_le_premier_chunk(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = groq.APITimeoutError(
            request=_requete()
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(IAError, match='réseau'):
            list(stream_chat_completion(model='llama-3.1-8b-instant', messages=[]))

    @patch('app.services.ai_errors.get_groq_client')
    def test_rate_limit_interrompt_le_stream_en_cours(self, mock_get_client):
        def chunk(texte):
            c = MagicMock()
            c.choices = [MagicMock()]
            c.choices[0].delta.content = texte
            return c

        def stream_qui_plante():
            yield chunk('Début de réponse... ')
            raise groq.RateLimitError(
                'Rate limit exceeded', response=_reponse(429, 'Rate limit exceeded'), body=None
            )

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = stream_qui_plante()
        mock_get_client.return_value = mock_client

        fragments = []
        with pytest.raises(IAError, match='quota'):
            for fragment in stream_chat_completion(model='llama-3.1-8b-instant', messages=[]):
                fragments.append(fragment)

        assert fragments == ['Début de réponse... ']
