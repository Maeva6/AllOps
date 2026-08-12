"""Tests de la recherche globale (app/routes/recherche.py)."""
from app.extensions import db
from app.models import Certification, SessionCER, SessionQA
import json


class TestRecherche:

    def test_page_vide_sans_q(self, client):
        response = client.get('/recherche/')
        assert response.status_code == 200

    def test_q_trop_courte(self, client):
        response = client.get('/recherche/?q=a')
        assert response.status_code == 200
        assert 'au moins 2' in response.get_data(as_text=True)

    def test_recherche_certification(self, client, app):
        with app.app_context():
            db.session.add(Certification(
                nom='AWS Cloud Practitioner', organisme='AWS',
                categorie='Cloud', statut='A faire'
            ))
            db.session.commit()

        response = client.get('/recherche/?q=aws')
        text = response.get_data(as_text=True)
        assert 'AWS Cloud Practitioner' in text

    def test_recherche_cer(self, client, app):
        with app.app_context():
            db.session.add(SessionCER(
                titre_prosit='Prosit N°3 — Réseaux', etudiant='Jean Dupont',
                contexte='c', besoins='b', problematique='p',
                plan_action=json.dumps(['Étape 1']),
            ))
            db.session.commit()

        response = client.get('/recherche/?q=réseaux')
        assert 'Prosit N°3' in response.get_data(as_text=True)

    def test_recherche_sans_resultat(self, client):
        response = client.get('/recherche/?q=zzzznotfound')
        assert response.status_code == 200
        assert 'Aucun résultat' in response.get_data(as_text=True)

    def test_recherche_insensible_a_la_casse(self, client, app):
        with app.app_context():
            db.session.add(Certification(
                nom='Docker Foundations', organisme='Docker',
                categorie='DevOps', statut='A faire'
            ))
            db.session.commit()

        response = client.get('/recherche/?q=DOCKER')
        assert 'Docker Foundations' in response.get_data(as_text=True)
