import json
from datetime import date, timedelta
import pytest
from app.extensions import db
from app.models import Certification, Tache, Projet, SessionCER
from app.services.notifications import get_elements_urgents


@pytest.fixture
def sample_projet(app):
    with app.app_context():
        projet = Projet(nom='Projet urgences', statut='en_cours')
        db.session.add(projet)
        db.session.commit()
        return projet.id


class TestGetElementsUrgents:

    def test_aucun_element_urgent(self, app):
        with app.test_request_context():
            assert get_elements_urgents() == []

    def test_certification_proche_incluse(self, app):
        with app.app_context():
            cert = Certification(
                nom='AWS Cloud Practitioner', organisme='AWS', categorie='Cloud',
                statut='En cours', deadline=date.today() + timedelta(days=5),
            )
            db.session.add(cert)
            db.session.commit()

        with app.test_request_context():
            elements = get_elements_urgents()
            assert len(elements) == 1
            assert elements[0]['type'] == 'certification'
            assert elements[0]['titre'] == 'AWS Cloud Practitioner'
            assert elements[0]['jours_restants'] == 5
            assert '/certifications/modifier/' in elements[0]['url']

    def test_certification_validee_exclue(self, app):
        with app.app_context():
            cert = Certification(
                nom='Cert validée', organisme='X', categorie='Y',
                statut='Validée', deadline=date.today() + timedelta(days=2),
            )
            db.session.add(cert)
            db.session.commit()

        with app.test_request_context():
            assert get_elements_urgents() == []

    def test_certification_trop_lointaine_exclue(self, app):
        with app.app_context():
            cert = Certification(
                nom='Cert lointaine', organisme='X', categorie='Y',
                statut='A faire', deadline=date.today() + timedelta(days=60),
            )
            db.session.add(cert)
            db.session.commit()

        with app.test_request_context():
            assert get_elements_urgents() == []

    def test_certification_deadline_passee_exclue(self, app):
        with app.app_context():
            cert = Certification(
                nom='Cert dépassée', organisme='X', categorie='Y',
                statut='A faire', deadline=date.today() - timedelta(days=2),
            )
            db.session.add(cert)
            db.session.commit()

        with app.test_request_context():
            assert get_elements_urgents() == []

    def test_tache_proche_incluse(self, app, sample_projet):
        with app.app_context():
            tache = Tache(
                projet_id=sample_projet, titre='Finaliser le rapport',
                statut='a_faire', echeance=date.today() + timedelta(days=1),
            )
            db.session.add(tache)
            db.session.commit()

        with app.test_request_context():
            elements = get_elements_urgents()
            assert len(elements) == 1
            assert elements[0]['type'] == 'tache'
            assert elements[0]['titre'] == 'Finaliser le rapport'
            assert elements[0]['jours_restants'] == 1

    def test_tache_terminee_exclue(self, app, sample_projet):
        with app.app_context():
            tache = Tache(
                projet_id=sample_projet, titre='Déjà fait',
                statut='termine', echeance=date.today() + timedelta(days=1),
            )
            db.session.add(tache)
            db.session.commit()

        with app.test_request_context():
            assert get_elements_urgents() == []

    def test_projet_proche_inclus(self, app):
        with app.app_context():
            projet = Projet(
                nom='Projet à rendre', statut='en_cours',
                echeance=date.today() + timedelta(days=3),
            )
            db.session.add(projet)
            db.session.commit()

        with app.test_request_context():
            elements = get_elements_urgents()
            assert len(elements) == 1
            assert elements[0]['type'] == 'projet'
            assert elements[0]['titre'] == 'Projet à rendre'
            assert elements[0]['jours_restants'] == 3

    def test_projet_termine_exclu(self, app):
        with app.app_context():
            projet = Projet(
                nom='Projet fini', statut='termine',
                echeance=date.today() + timedelta(days=3),
            )
            db.session.add(projet)
            db.session.commit()

        with app.test_request_context():
            assert get_elements_urgents() == []

    def test_melange_des_trois_types(self, app, sample_projet):
        with app.app_context():
            db.session.add(Certification(
                nom='Cert', organisme='X', categorie='Y', statut='A faire',
                deadline=date.today() + timedelta(days=2),
            ))
            db.session.add(Tache(
                projet_id=sample_projet, titre='Tâche', statut='a_faire',
                echeance=date.today() + timedelta(days=2),
            ))
            db.session.add(Projet(
                nom='Autre projet', statut='en_cours',
                echeance=date.today() + timedelta(days=2),
            ))
            db.session.commit()

        with app.test_request_context():
            elements = get_elements_urgents()
            types = {e['type'] for e in elements}
            assert types == {'certification', 'tache', 'projet'}


class TestPageIntegreLesElementsUrgents:

    def test_dashboard_embarque_le_json_des_elements_urgents(self, client, app):
        with app.app_context():
            db.session.add(Certification(
                nom='Cert Notif Test', organisme='X', categorie='Y',
                statut='A faire', deadline=date.today() + timedelta(days=1),
            ))
            db.session.commit()

        r = client.get('/')
        assert r.status_code == 200
        html = r.data.decode()
        assert 'Cert Notif Test' in html
        assert 'elementsUrgents' in html
