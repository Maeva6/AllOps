"""Tests du suivi de progression Révision (app/routes/revision.py:progression)."""
from app.extensions import db
from app.models import SessionRevision, QuizResult


class TestProgression:

    def test_page_vide(self, client):
        response = client.get('/revision/progression')
        assert response.status_code == 200
        assert 'Pas encore de quiz' in response.get_data(as_text=True)

    def test_page_avec_resultats(self, client, app):
        with app.app_context():
            s = SessionRevision(titre='Les arbres binaires', domaine='informatique')
            db.session.add(s)
            db.session.commit()
            db.session.add(QuizResult(session_id=s.id, score=8, total=10))
            db.session.add(QuizResult(session_id=s.id, score=5, total=10))
            db.session.commit()

        response = client.get('/revision/progression')
        assert response.status_code == 200
        text = response.get_data(as_text=True)
        assert 'Les arbres binaires' in text
        assert '65.0%' in text  # moyenne (80 + 50) / 2

    def test_quiz_total_zero_ne_plante_pas(self, client, app):
        with app.app_context():
            s = SessionRevision(titre='Cas limite', domaine='autre')
            db.session.add(s)
            db.session.commit()
            db.session.add(QuizResult(session_id=s.id, score=0, total=0))
            db.session.commit()

        response = client.get('/revision/progression')
        assert response.status_code == 200
