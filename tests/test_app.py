import pytest
from app import create_app
from app.extensions import db
from app.models import Certification, FileOperation, OrganisationSnapshot


# ─── Configuration de test ────────────────────────────────────────────────────
@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'cle-de-test'
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_cert(app):
    """Certification de test réutilisable"""
    with app.app_context():
        cert = Certification(
            nom='AWS Cloud Practitioner',
            organisme='AWS',
            categorie='Cloud',
            statut='A faire',
            niveau=1,
            niveau_vise=3,
            gratuite=False
        )
        db.session.add(cert)
        db.session.commit()
        return cert.id


# ─── Tests : Pages principales ────────────────────────────────────────────────
class TestPages:

    def test_page_accueil(self, client):
        """La page d'accueil doit répondre 200"""
        r = client.get('/')
        assert r.status_code == 200
        assert 'AllOps' in r.data.decode()

    def test_page_fichiers(self, client):
        """La page fichiers doit répondre 200"""
        r = client.get('/files/')
        assert r.status_code == 200

    def test_page_certifications(self, client):
        """La page certifications doit répondre 200"""
        r = client.get('/certifications/')
        assert r.status_code == 200

    def test_page_404(self, client):
        """Une page inexistante doit renvoyer 404"""
        r = client.get('/page-qui-nexiste-pas')
        assert r.status_code == 404


# ─── Tests : Modèle Certification ────────────────────────────────────────────
class TestModeles:

    def test_creer_certification(self, app):
        """On doit pouvoir créer une certification"""
        with app.app_context():
            cert = Certification(
                nom='Docker Foundations',
                organisme='Docker',
                categorie='DevOps',
                statut='A faire',
                niveau=1,
                niveau_vise=3,
                gratuite=True
            )
            db.session.add(cert)
            db.session.commit()

            assert cert.id is not None
            assert cert.nom == 'Docker Foundations'
            assert cert.gratuite is True

    def test_progression_calcul(self, app):
        """La progression doit être calculée correctement"""
        with app.app_context():
            cert = Certification(
                nom='Test', organisme='Test',
                categorie='Test', niveau=2, niveau_vise=4
            )
            # 2/4 = 50%
            assert cert.progression() == 50

    def test_progression_complete(self, app):
        """Niveau atteint = 100%"""
        with app.app_context():
            cert = Certification(
                nom='Test', organisme='Test',
                categorie='Test', niveau=3, niveau_vise=3
            )
            assert cert.progression() == 100

    def test_jours_restants_sans_deadline(self, app):
        """Sans deadline, jours_restants doit retourner None"""
        with app.app_context():
            cert = Certification(
                nom='Test', organisme='Test',
                categorie='Test', deadline=None
            )
            assert cert.jours_restants() is None


# ─── Tests : CRUD Certifications ─────────────────────────────────────────────
class TestCertifications:

    def test_ajouter_certification(self, client):
        """POST /certifications/ajouter doit créer une certification"""
        r = client.post('/certifications/ajouter', data={
            'nom':         'GitHub Foundations',
            'organisme':   'GitHub',
            'categorie':   'DevOps',
            'statut':      'A faire',
            'niveau':      '1',
            'niveau_vise': '3',
            'notes':       'Certification gratuite'
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'GitHub Foundations' in r.data.decode()

    def test_modifier_certification(self, client, sample_cert, app):
        """POST /certifications/modifier/<id> doit mettre à jour"""
        with app.app_context():
            r = client.post(
                f'/certifications/modifier/{sample_cert}',
                data={
                    'nom':         'AWS Cloud Practitioner CLF-C02',
                    'organisme':   'AWS',
                    'categorie':   'Cloud',
                    'statut':      'En cours',
                    'niveau':      '2',
                    'niveau_vise': '3',
                },
                follow_redirects=True
            )
            assert r.status_code == 200
            cert = Certification.query.get(sample_cert)
            assert cert.statut == 'En cours'
            assert cert.niveau == 2

    def test_supprimer_certification(self, client, sample_cert, app):
        """POST /certifications/supprimer/<id> doit supprimer"""
        with app.app_context():
            r = client.post(
                f'/certifications/supprimer/{sample_cert}',
                follow_redirects=True
            )
            assert r.status_code == 200
            cert = Certification.query.get(sample_cert)
            assert cert is None

    def test_changer_statut(self, client, sample_cert, app):
        """POST /certifications/statut/<id> doit changer le statut"""
        with app.app_context():
            r = client.post(
                f'/certifications/statut/{sample_cert}',
                data={'statut': 'Validée'},
                follow_redirects=True
            )
            assert r.status_code == 200
            cert = Certification.query.get(sample_cert)
            assert cert.statut == 'Validée'


# ─── Tests : Module Fichiers ──────────────────────────────────────────────────
class TestFichiers:

    def test_renommer_dossier_invalide(self, client):
        """Renommer avec un dossier inexistant doit afficher une erreur"""
        r = client.post('/files/renommer', data={
            'dossier':    '/dossier/qui/nexiste/pas',
            'prefixe':    'TP',
            'suffixe':    '',
            'extension':  ''
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'introuvable' in r.data.decode().lower()

    def test_organiser_dossier_invalide(self, client):
        """Organiser un dossier inexistant doit afficher une erreur"""
        r = client.post('/files/organiser', data={
            'dossier_org': '/dossier/inexistant'
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'introuvable' in r.data.decode().lower()

    def test_historique_accessible(self, client):
        """La page historique doit être accessible"""
        r = client.get('/files/historique')
        assert r.status_code == 200

    def test_explorateur_chemin_invalide(self, client):
        """L'explorateur avec un chemin non autorisé doit rediriger vers home"""
        r = client.get('/files/explorer?chemin=/etc/passwd')
        data = r.get_json()
        assert 'contenu' in data
