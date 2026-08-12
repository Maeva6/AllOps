from app.extensions import db
from app.models import Parametre


class TestTheme:

    def test_theme_par_defaut_dark(self, client):
        r = client.get('/')
        assert r.status_code == 200
        assert 'data-theme="dark"' in r.data.decode()

    def test_changer_theme_persiste_en_base(self, client, app):
        r = client.post('/parametres/theme', json={'theme': 'light'})
        assert r.status_code == 200
        assert r.get_json()['ok'] is True

        with app.app_context():
            assert Parametre.get().theme == 'light'

    def test_theme_persiste_est_rendu_au_prochain_chargement(self, client):
        client.post('/parametres/theme', json={'theme': 'light'})
        r = client.get('/')
        assert 'data-theme="light"' in r.data.decode()

    def test_theme_invalide_rejete(self, client):
        r = client.post('/parametres/theme', json={'theme': 'bleu'})
        assert r.status_code == 400
        assert r.get_json()['ok'] is False

    def test_theme_absent_rejete(self, client):
        r = client.post('/parametres/theme', json={})
        assert r.status_code == 400

    def test_parametre_singleton_reutilise(self, app):
        with app.app_context():
            p1 = Parametre.get()
            p1.theme = 'light'
            db.session.commit()

            p2 = Parametre.get()
            assert p2.id == p1.id
            assert p2.theme == 'light'
            assert Parametre.query.count() == 1
