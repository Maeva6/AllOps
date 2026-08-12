from datetime import date, timedelta
from flask import url_for
from app.models import Certification, Tache, Projet

SEUIL_JOURS = 30


def get_elements_urgents():
    """Renvoie les certifications, tâches et projets dont l'échéance
    approche (≤ SEUIL_JOURS jours, pas encore terminés), sous forme de
    dicts sérialisables en JSON pour le contrôle des notifications
    navigateur côté client (voir base.html)."""
    aujourdhui = date.today()
    limite = aujourdhui + timedelta(days=SEUIL_JOURS)
    elements = []

    certifications = Certification.query.filter(
        Certification.deadline.isnot(None),
        Certification.deadline <= limite,
        Certification.deadline >= aujourdhui,
        Certification.statut != 'Validée',
    ).all()
    for c in certifications:
        elements.append({
            'type': 'certification',
            'id': c.id,
            'titre': c.nom,
            'jours_restants': c.jours_restants(),
            'url': url_for('tracker.modifier', id=c.id),
        })

    taches = Tache.query.filter(
        Tache.echeance.isnot(None),
        Tache.echeance <= limite,
        Tache.echeance >= aujourdhui,
        Tache.statut != 'termine',
    ).all()
    for t in taches:
        elements.append({
            'type': 'tache',
            'id': t.id,
            'titre': t.titre,
            'jours_restants': t.jours_restants(),
            'url': url_for('projets.voir', id=t.projet_id),
        })

    projets = Projet.query.filter(
        Projet.echeance.isnot(None),
        Projet.echeance <= limite,
        Projet.echeance >= aujourdhui,
        Projet.statut != 'termine',
    ).all()
    for p in projets:
        elements.append({
            'type': 'projet',
            'id': p.id,
            'titre': p.nom,
            'jours_restants': p.jours_restants(),
            'url': url_for('projets.voir', id=p.id),
        })

    return elements
