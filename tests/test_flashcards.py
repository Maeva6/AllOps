"""Tests des flashcards / révision espacée (système de Leitner)."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import date, timedelta

from app.extensions import db
from app.models import SessionRevision, Flashcard
from app.services.ai_errors import IAError


def fake_completion(content: str):
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    return response


class TestFlashcards:

    @pytest.fixture
    def sample_session(self, app):
        with app.app_context():
            s = SessionRevision(
                titre='Les listes chaînées', domaine='informatique',
                cours_genere='## Intro\nContenu du cours sur les listes chaînées.',
            )
            db.session.add(s)
            db.session.commit()
            return s.id

    def test_page_sans_flashcards(self, client, sample_session):
        response = client.get(f'/revision/{sample_session}/flashcards')
        assert response.status_code == 200
        assert 'Générer les flashcards' in response.get_data(as_text=True)

    def test_page_session_introuvable(self, client):
        response = client.get('/revision/9999/flashcards', follow_redirects=True)
        assert response.status_code == 200

    @patch('app.services.flashcard_service.safe_chat_completion')
    def test_generer_flashcards(self, mock_completion, client, sample_session):
        mock_completion.return_value = fake_completion(
            '[{"question":"Qu\'est-ce qu\'un maillon ?","reponse":"Un élément de la liste."},'
            ' {"question":"Complexité insertion ?","reponse":"O(1) en tête."}]'
        )
        response = client.post(f'/revision/{sample_session}/flashcards/generer')
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert data['nb'] == 2
        assert Flashcard.query.filter_by(session_id=sample_session).count() == 2

    @patch('app.services.flashcard_service.safe_chat_completion')
    def test_regenerer_deja_existant_refuse(self, mock_completion, client, sample_session, app):
        with app.app_context():
            db.session.add(Flashcard(session_id=sample_session, question='Q', reponse='R'))
            db.session.commit()

        response = client.post(f'/revision/{sample_session}/flashcards/generer')
        assert response.status_code == 400
        mock_completion.assert_not_called()

    @patch('app.services.flashcard_service.safe_chat_completion')
    def test_generer_erreur_ia(self, mock_completion, client, sample_session):
        mock_completion.side_effect = IAError("Clé API manquante.")
        response = client.post(f'/revision/{sample_session}/flashcards/generer')
        assert response.status_code == 503

    def test_repondre_fait_avancer_la_boite(self, client, app, sample_session):
        with app.app_context():
            carte = Flashcard(session_id=sample_session, question='Q', reponse='R')
            db.session.add(carte)
            db.session.commit()
            fid = carte.id

        r1 = client.post(f'/revision/flashcards/{fid}/repondre', json={'connu': True})
        data1 = r1.get_json()
        assert data1['boite'] == 2

        r2 = client.post(f'/revision/flashcards/{fid}/repondre', json={'connu': True})
        assert r2.get_json()['boite'] == 3

    def test_repondre_faux_remet_a_la_boite_1(self, client, app, sample_session):
        with app.app_context():
            carte = Flashcard(session_id=sample_session, question='Q', reponse='R', boite=4)
            db.session.add(carte)
            db.session.commit()
            fid = carte.id

        response = client.post(f'/revision/flashcards/{fid}/repondre', json={'connu': False})
        assert response.get_json()['boite'] == 1

    def test_repondre_carte_introuvable(self, client):
        response = client.post('/revision/flashcards/9999/repondre', json={'connu': True})
        assert response.status_code == 404

    def test_carte_maitrisee_pas_dans_a_revoir(self, client, app, sample_session):
        with app.app_context():
            db.session.add(Flashcard(
                session_id=sample_session, question='Q future', reponse='R',
                prochaine_revision=date.today() + timedelta(days=10)
            ))
            db.session.add(Flashcard(
                session_id=sample_session, question='Q due', reponse='R',
                prochaine_revision=date.today()
            ))
            db.session.commit()

        response = client.get(f'/revision/{sample_session}/flashcards')
        text = response.get_data(as_text=True)
        assert 'Q due' in text
        assert 'Q future' not in text
