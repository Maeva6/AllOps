"""Tests des modules assistés par IA : CER, Révision, Correction, QA.

Les appels réels à Groq sont mockés via `safe_chat_completion` (voir
app/services/ai_errors.py), point de passage unique de tous les appels IA.
Aucune clé API n'est nécessaire pour exécuter ces tests.
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from app.extensions import db
from app.models import SessionCER, SessionRevision, SessionCorrection, SessionQA
from app.services.ai_errors import IAError


def fake_completion(content: str):
    """Construit une fausse réponse Groq (choices[0].message.content)."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    return response


# ══════════════════════════════════════════════════════════════════════
# CER
# ══════════════════════════════════════════════════════════════════════

class TestCER:

    @pytest.fixture
    def sample_cer(self, app):
        with app.app_context():
            cer = SessionCER(
                titre_prosit='Prosit N°1 — Test',
                etudiant='Jean Dupont',
                contexte='Contexte de test',
                besoins='Besoin 1',
                problematique='Comment tester ?',
                plan_action=json.dumps(['Étape 1', 'Étape 2']),
                statut='brouillon',
            )
            db.session.add(cer)
            db.session.commit()
            return cer.id

    def test_index_vide(self, client):
        response = client.get('/cer/')
        assert response.status_code == 200

    def test_nouveau_creation(self, client):
        response = client.post('/cer/nouveau', data={
            'titre_prosit': 'Prosit N°2 — Test',
            'etudiant': 'Jean Dupont',
            'contexte': 'Contexte',
            'besoins': 'Besoins',
            'problematique': 'Problématique',
            'plan_action': 'Étape 1\nÉtape 2',
        }, follow_redirects=False)
        assert response.status_code == 302
        assert SessionCER.query.count() == 1

    def test_voir_introuvable(self, client):
        response = client.get('/cer/9999', follow_redirects=True)
        assert response.status_code == 200
        assert b'introuvable' in response.data.lower() or b'CER' in response.data

    @patch('app.services.cer_service.safe_chat_completion')
    def test_generer_section_success(self, mock_completion, client, sample_cer):
        mock_completion.return_value = fake_completion('## Validation générée')
        response = client.post(
            f'/cer/generer-section/{sample_cer}',
            json={'section': 'validation'}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert 'Validation générée' in data['contenu']

    @patch('app.services.cer_service.safe_chat_completion')
    def test_generer_section_erreur_ia(self, mock_completion, client, sample_cer):
        mock_completion.side_effect = IAError("Clé API Groq manquante.")
        response = client.post(
            f'/cer/generer-section/{sample_cer}',
            json={'section': 'validation'}
        )
        assert response.status_code == 503
        assert 'Clé API' in response.get_json()['erreur']

    def test_generer_section_session_introuvable(self, client):
        response = client.post('/cer/generer-section/9999', json={'section': 'validation'})
        assert response.status_code == 404

    def test_supprimer(self, client, sample_cer):
        response = client.post(f'/cer/supprimer/{sample_cer}', follow_redirects=False)
        assert response.status_code == 302
        assert db.session.get(SessionCER, sample_cer) is None


# ══════════════════════════════════════════════════════════════════════
# RÉVISION IA
# ══════════════════════════════════════════════════════════════════════

class TestRevisionIA:

    @pytest.fixture
    def sample_session(self, app):
        with app.app_context():
            s = SessionRevision(
                titre='Les listes chaînées',
                domaine='informatique',
                cours_genere='## Introduction\nContenu du cours.',
            )
            db.session.add(s)
            db.session.commit()
            return s.id

    def test_index(self, client):
        response = client.get('/revision/')
        assert response.status_code == 200

    def test_generer_sans_titre(self, client):
        response = client.post('/revision/generer', data={}, follow_redirects=True)
        assert response.status_code == 200
        assert SessionRevision.query.count() == 0

    @patch('app.services.groq_service.safe_chat_completion')
    def test_generer_success(self, mock_completion, client):
        mock_completion.return_value = fake_completion('## Cours généré\nContenu.')
        response = client.post('/revision/generer', data={
            'titre': 'Les arbres binaires',
            'domaine': 'informatique',
        }, follow_redirects=False)
        assert response.status_code == 302
        session_obj = SessionRevision.query.filter_by(titre='Les arbres binaires').first()
        assert session_obj is not None
        assert 'Cours généré' in session_obj.cours_genere

    @patch('app.services.groq_service.safe_chat_completion')
    def test_generer_erreur_ia(self, mock_completion, client):
        mock_completion.side_effect = IAError("Le service IA n'est pas configuré.")
        response = client.post('/revision/generer', data={
            'titre': 'Les arbres binaires',
            'domaine': 'informatique',
        }, follow_redirects=True)
        assert response.status_code == 200
        assert 'pas configuré' in response.get_data(as_text=True)

    @patch('app.services.gemini_service.safe_chat_completion')
    def test_generer_quiz_success(self, mock_completion, client, sample_session):
        quiz_json = json.dumps([
            {
                'question': 'Qu\'est-ce qu\'une liste chaînée ?',
                'choices': ['A', 'B', 'C', 'D'],
                'correct': 0,
                'explanation': 'Parce que.',
            }
        ])
        mock_completion.return_value = fake_completion(quiz_json)
        response = client.post(
            f'/revision/generer-quiz/{sample_session}',
            json={'niveau': 3}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert len(data['questions']) == 1

    def test_generer_quiz_session_introuvable(self, client):
        response = client.post('/revision/generer-quiz/9999', json={'niveau': 1})
        assert response.status_code == 404


# ══════════════════════════════════════════════════════════════════════
# CORRECTION IA
# ══════════════════════════════════════════════════════════════════════

class TestCorrectionIA:

    @pytest.fixture
    def sample_session(self, app):
        with app.app_context():
            s = SessionCorrection(
                titre='TP Réseaux',
                type_doc='tp',
                contenu_source='Exercice 1 : expliquer TCP/IP.',
                statut='en_attente',
            )
            db.session.add(s)
            db.session.commit()
            return s.id

    def test_index(self, client):
        response = client.get('/correction/')
        assert response.status_code == 200

    def test_soumettre_sans_titre(self, client):
        response = client.post('/correction/soumettre', data={
            'texte': 'Contenu quelconque'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert SessionCorrection.query.count() == 0

    @patch('app.services.correction_service.safe_chat_completion')
    def test_corriger_success(self, mock_completion, client, sample_session):
        corrections_json = json.dumps([
            {
                'numero': 'Exercice 1',
                'enonce': 'Expliquer TCP/IP.',
                'reponse': 'TCP/IP est...',
                'explication': 'Car...',
                'notions': ['réseaux', 'protocoles'],
                'conseils': 'Revoir le cours.',
                'difficulte': 'moyen',
            }
        ])
        # generer_correction() puis generer_resume_notions() : 2 appels successifs
        mock_completion.side_effect = [
            fake_completion(corrections_json),
            fake_completion('Résumé pédagogique des notions abordées.'),
        ]
        response = client.get(f'/correction/corriger/{sample_session}', follow_redirects=False)
        assert response.status_code == 302

        session_obj = db.session.get(SessionCorrection, sample_session)
        assert session_obj.statut == 'corrige'
        assert 'TCP/IP' in session_obj.correction

    @patch('app.services.correction_service.safe_chat_completion')
    def test_corriger_erreur_ia(self, mock_completion, client, sample_session):
        mock_completion.side_effect = IAError("Quota Groq atteint.")
        response = client.get(f'/correction/corriger/{sample_session}', follow_redirects=True)
        assert response.status_code == 200

        session_obj = db.session.get(SessionCorrection, sample_session)
        assert session_obj.statut == 'erreur'


# ══════════════════════════════════════════════════════════════════════
# QUESTIONS DE COURS (QA)
# ══════════════════════════════════════════════════════════════════════

class TestQA:

    def test_index(self, client):
        response = client.get('/qa/')
        assert response.status_code == 200

    def test_poser_question_vide(self, client):
        response = client.post('/qa/poser', json={'question': ''})
        assert response.status_code == 400

    @patch('app.routes.qa.safe_chat_completion')
    def test_poser_success(self, mock_completion, client):
        mock_completion.return_value = fake_completion('La complexité de O(n) est linéaire.')
        response = client.post('/qa/poser', json={
            'question': "Qu'est-ce que la complexité O(n) ?",
            'mode': 'direct',
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert SessionQA.query.count() == 1

    @patch('app.routes.qa.safe_chat_completion')
    def test_poser_erreur_ia(self, mock_completion, client):
        mock_completion.side_effect = IAError("La clé GROQ_API_KEY est invalide.")
        response = client.post('/qa/poser', json={
            'question': "Qu'est-ce que la complexité O(n) ?",
        })
        assert response.status_code == 503
        assert 'invalide' in response.get_json()['erreur']

    def test_supprimer_et_vider(self, client, app):
        with app.app_context():
            qa = SessionQA(question='Q ?', reponse='R.', mode='direct')
            db.session.add(qa)
            db.session.commit()
            qa_id = qa.id

        response = client.post(f'/qa/supprimer/{qa_id}')
        assert response.status_code == 200
        assert SessionQA.query.count() == 0

        response = client.post('/qa/vider')
        assert response.status_code == 200
