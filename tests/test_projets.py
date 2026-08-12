import json
import pytest
from app.extensions import db
from app.models import Projet, Tache, ActiviteJournaliere, Certification, SessionCER


@pytest.fixture
def sample_projet(app):
    """Projet de test réutilisable"""
    with app.app_context():
        projet = Projet(
            nom='PROSIT n°4',
            description='Automatisation industrielle',
            statut='en_cours',
            priorite='normale',
        )
        db.session.add(projet)
        db.session.commit()
        return projet.id


@pytest.fixture
def sample_certification(app):
    with app.app_context():
        cert = Certification(nom='AWS Cloud Practitioner', organisme='AWS', categorie='Cloud')
        db.session.add(cert)
        db.session.commit()
        return cert.id


@pytest.fixture
def sample_cer_session(app):
    with app.app_context():
        cer = SessionCER(
            titre_prosit='Prosit Test — Liaison',
            etudiant='Jean Dupont',
            contexte='Contexte', besoins='Besoins', problematique='Problématique',
            plan_action=json.dumps(['Étape 1']),
        )
        db.session.add(cer)
        db.session.commit()
        return cer.id


# ─── Tests : CRUD Projets ──────────────────────────────────────────────────
class TestProjets:

    def test_page_liste_projets(self, client):
        r = client.get('/projets/')
        assert r.status_code == 200
        assert 'Projets' in r.data.decode()

    def test_creer_projet(self, client):
        r = client.post('/projets/nouveau', data={
            'nom': 'Robot suiveur de ligne',
            'description': 'Projet de robotique',
            'statut': 'en_cours',
            'priorite': 'haute',
            'echeance': '2026-12-01',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert 'Robot suiveur de ligne' in r.data.decode()

    def test_creer_projet_sans_nom(self, client):
        r = client.post('/projets/nouveau', data={
            'nom': '',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert Projet.query.count() == 0

    def test_modifier_projet(self, client, sample_projet, app):
        r = client.post(f'/projets/{sample_projet}/modifier', data={
            'nom': 'PROSIT n°4 — révisé',
            'statut': 'termine',
            'priorite': 'basse',
        }, follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            projet = db.session.get(Projet, sample_projet)
            assert projet.nom == 'PROSIT n°4 — révisé'
            assert projet.statut == 'termine'

    def test_supprimer_projet(self, client, sample_projet, app):
        r = client.post(f'/projets/{sample_projet}/supprimer', follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            assert db.session.get(Projet, sample_projet) is None

    def test_supprimer_projet_detache_les_activites(self, client, sample_projet, app):
        with app.app_context():
            activite = ActiviteJournaliere(
                titre='Travail sur le PROSIT', duree_minutes=60,
                categorie='Projet', projet_id=sample_projet,
            )
            db.session.add(activite)
            db.session.commit()
            activite_id = activite.id

        client.post(f'/projets/{sample_projet}/supprimer', follow_redirects=True)

        with app.app_context():
            activite = db.session.get(ActiviteJournaliere, activite_id)
            assert activite is not None
            assert activite.projet_id is None

    def test_voir_projet_404(self, client):
        r = client.get('/projets/9999')
        assert r.status_code == 404


# ─── Tests : Tâches (kanban) ────────────────────────────────────────────────
class TestTaches:

    def test_ajouter_tache(self, client, sample_projet, app):
        r = client.post(f'/projets/{sample_projet}/taches/ajouter', data={
            'titre': 'Rédiger la synthèse',
        }, follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            projet = db.session.get(Projet, sample_projet)
            assert len(projet.taches) == 1
            assert projet.taches[0].titre == 'Rédiger la synthèse'

    def test_changer_statut_tache(self, client, sample_projet, app):
        with app.app_context():
            tache = Tache(projet_id=sample_projet, titre='Etape 1', statut='a_faire')
            db.session.add(tache)
            db.session.commit()
            tache_id = tache.id

        r = client.post(f'/projets/taches/{tache_id}/statut', data={
            'statut': 'termine',
        }, follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            assert db.session.get(Tache, tache_id).statut == 'termine'

    def test_supprimer_tache(self, client, sample_projet, app):
        with app.app_context():
            tache = Tache(projet_id=sample_projet, titre='Etape à supprimer')
            db.session.add(tache)
            db.session.commit()
            tache_id = tache.id

        r = client.post(f'/projets/taches/{tache_id}/supprimer', follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            assert db.session.get(Tache, tache_id) is None

    def test_progression_projet(self, client, sample_projet, app):
        with app.app_context():
            db.session.add_all([
                Tache(projet_id=sample_projet, titre='T1', statut='termine'),
                Tache(projet_id=sample_projet, titre='T2', statut='a_faire'),
            ])
            db.session.commit()
            projet = db.session.get(Projet, sample_projet)
            assert projet.progression() == 50

    def test_tache_jours_restants(self, app, sample_projet):
        from datetime import timedelta, datetime, timezone
        with app.app_context():
            tache = Tache(
                projet_id=sample_projet, titre='Avec échéance',
                echeance=(datetime.now(timezone.utc).date() + timedelta(days=4)),
            )
            db.session.add(tache)
            db.session.commit()
            assert tache.jours_restants() == 4

    def test_tache_jours_restants_sans_echeance(self, app, sample_projet):
        with app.app_context():
            tache = Tache(projet_id=sample_projet, titre='Sans échéance')
            db.session.add(tache)
            db.session.commit()
            assert tache.jours_restants() is None


# ─── Tests : Journal d'activité ─────────────────────────────────────────────
class TestJournal:

    def test_page_journal(self, client):
        r = client.get('/projets/journal')
        assert r.status_code == 200
        assert "Journal d'activité" in r.data.decode()

    def test_ajouter_activite(self, client):
        r = client.post('/projets/journal/ajouter', data={
            'titre': 'Révision thermodynamique',
            'duree_minutes': '45',
            'categorie': 'Cours',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert ActiviteJournaliere.query.count() == 1
        assert ActiviteJournaliere.query.first().duree_minutes == 45

    def test_ajouter_activite_liee_a_un_projet(self, client, sample_projet):
        r = client.post('/projets/journal/ajouter', data={
            'titre': 'Avancement PROSIT',
            'duree_minutes': '30',
            'categorie': 'Projet',
            'projet_id': str(sample_projet),
        }, follow_redirects=True)
        assert r.status_code == 200
        activite = ActiviteJournaliere.query.first()
        assert activite.projet_id == sample_projet

    def test_ajouter_activite_sans_titre(self, client):
        r = client.post('/projets/journal/ajouter', data={
            'titre': '',
            'duree_minutes': '30',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert ActiviteJournaliere.query.count() == 0

    def test_ajouter_activite_duree_invalide(self, client):
        r = client.post('/projets/journal/ajouter', data={
            'titre': 'Sans durée',
            'duree_minutes': '0',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert ActiviteJournaliere.query.count() == 0

    def test_supprimer_activite(self, client, app):
        with app.app_context():
            activite = ActiviteJournaliere(titre='À supprimer', duree_minutes=15)
            db.session.add(activite)
            db.session.commit()
            activite_id = activite.id

        r = client.post(f'/projets/journal/{activite_id}/supprimer', follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            assert db.session.get(ActiviteJournaliere, activite_id) is None

    def test_totaux_dashboard(self, client, app):
        with app.app_context():
            from datetime import datetime, timezone
            db.session.add(ActiviteJournaliere(
                titre='Aujourd\'hui', duree_minutes=90,
                date_activite=datetime.now(timezone.utc).date(),
            ))
            db.session.commit()

        r = client.get('/projets/journal')
        assert r.status_code == 200
        assert '1h30' in r.data.decode()


# ─── Tests : liaison des tâches aux Certifications / CER ───────────────────
class TestLiaisonTachesCertificationsCER:

    def test_ajouter_tache_liee_a_une_certification(self, client, sample_projet,
                                                      sample_certification, app):
        r = client.post(f'/projets/{sample_projet}/taches/ajouter', data={
            'titre': 'Réviser pour AWS',
            'certification_id': str(sample_certification),
        }, follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            tache = Tache.query.filter_by(projet_id=sample_projet).first()
            assert tache.certification_id == sample_certification
            assert tache.certification.nom == 'AWS Cloud Practitioner'

    def test_ajouter_tache_liee_a_un_cer(self, client, sample_projet,
                                          sample_cer_session, app):
        r = client.post(f'/projets/{sample_projet}/taches/ajouter', data={
            'titre': 'Finaliser le CER',
            'cer_id': str(sample_cer_session),
        }, follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            tache = Tache.query.filter_by(projet_id=sample_projet).first()
            assert tache.cer_id == sample_cer_session
            assert tache.cer.titre_prosit == 'Prosit Test — Liaison'

    def test_ajouter_tache_certification_invalide_ignoree(self, client, sample_projet, app):
        r = client.post(f'/projets/{sample_projet}/taches/ajouter', data={
            'titre': 'Tâche sans lien valide',
            'certification_id': '9999',
        }, follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            tache = Tache.query.filter_by(projet_id=sample_projet).first()
            assert tache.certification_id is None

    def test_ajouter_tache_sans_lien(self, client, sample_projet, app):
        r = client.post(f'/projets/{sample_projet}/taches/ajouter', data={
            'titre': 'Tâche libre',
        }, follow_redirects=True)
        assert r.status_code == 200
        with app.app_context():
            tache = Tache.query.filter_by(projet_id=sample_projet).first()
            assert tache.certification_id is None
            assert tache.cer_id is None

    def test_page_projet_propose_les_certifications_et_cer(self, client, sample_projet,
                                                             sample_certification,
                                                             sample_cer_session):
        r = client.get(f'/projets/{sample_projet}')
        assert r.status_code == 200
        html = r.data.decode()
        assert 'AWS Cloud Practitioner' in html
        assert 'Prosit Test — Liaison' in html

    def test_kanban_affiche_le_lien_certification(self, client, sample_projet,
                                                    sample_certification, app):
        client.post(f'/projets/{sample_projet}/taches/ajouter', data={
            'titre': 'Réviser pour AWS',
            'certification_id': str(sample_certification),
        })
        r = client.get(f'/projets/{sample_projet}')
        assert 'AWS Cloud Practitioner' in r.data.decode()
