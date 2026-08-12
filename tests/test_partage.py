"""Tests du partage en lecture seule (app/routes/partage.py)."""
import json
from app.extensions import db
from app.models import SessionCER, SessionRevision


class TestPartageCER:

    def sample_cer(self, app):
        with app.app_context():
            cer = SessionCER(
                titre_prosit='Prosit N°1 — Test', etudiant='Jean Dupont',
                contexte='Contexte', besoins='Besoin', problematique='Question ?',
                plan_action=json.dumps(['Étape 1']),
                validation='## Validation\nOK',
            )
            db.session.add(cer)
            db.session.commit()
            return cer.id

    def test_token_absent_404(self, client):
        response = client.get('/partage/cer/un-token-qui-nexiste-pas')
        assert response.status_code == 404

    def test_generer_lien_puis_le_consulter(self, client, app):
        cer_id = self.sample_cer(app)

        response = client.post(f'/cer/{cer_id}/partager')
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        token = data['url'].rsplit('/', 1)[-1]

        page = client.get(f'/partage/cer/{token}')
        assert page.status_code == 200
        text = page.get_data(as_text=True)
        assert 'Prosit N°1' in text
        assert 'Validation' in text

    def test_lien_idempotent(self, client, app):
        cer_id = self.sample_cer(app)
        r1 = client.post(f'/cer/{cer_id}/partager').get_json()
        r2 = client.post(f'/cer/{cer_id}/partager').get_json()
        assert r1['url'] == r2['url']

    def test_partager_session_introuvable(self, client):
        response = client.post('/cer/9999/partager')
        assert response.status_code == 404


class TestPartageRevision:

    def sample_session(self, app):
        with app.app_context():
            s = SessionRevision(
                titre='Les listes chaînées', domaine='informatique',
                cours_genere='## Introduction\nContenu du cours.',
            )
            db.session.add(s)
            db.session.commit()
            return s.id

    def test_token_absent_404(self, client):
        response = client.get('/partage/cours/un-token-qui-nexiste-pas')
        assert response.status_code == 404

    def test_generer_lien_puis_le_consulter(self, client, app):
        session_id = self.sample_session(app)

        response = client.post(f'/revision/{session_id}/partager')
        assert response.status_code == 200
        data = response.get_json()
        token = data['url'].rsplit('/', 1)[-1]

        page = client.get(f'/partage/cours/{token}')
        assert page.status_code == 200
        assert 'Les listes chaînées' in page.get_data(as_text=True)
