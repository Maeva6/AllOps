# app/routes/recherche.py
from datetime import datetime
from flask import Blueprint, render_template, request, url_for
from sqlalchemy import or_
from app.models import (
    Certification, SessionCER, SessionRevision,
    SessionCorrection, SessionQA,
)

recherche_bp = Blueprint('recherche', __name__, url_prefix='/recherche')


@recherche_bp.route('/')
def index():
    q = request.args.get('q', '').strip()
    resultats = []

    if q and len(q) >= 2:
        motif = f'%{q}%'

        for cert in Certification.query.filter(
            or_(Certification.nom.ilike(motif),
                Certification.organisme.ilike(motif),
                Certification.categorie.ilike(motif))
        ).limit(10).all():
            resultats.append({
                'type': 'Certification', 'icon': 'award',
                'titre': cert.nom,
                'sous_titre': f'{cert.organisme} · {cert.statut}',
                'url': url_for('tracker.modifier', id=cert.id),
                'date': cert.created_at,
            })

        for cer in SessionCER.query.filter(
            or_(SessionCER.titre_prosit.ilike(motif),
                SessionCER.etudiant.ilike(motif))
        ).limit(10).all():
            resultats.append({
                'type': 'CER', 'icon': 'file-text',
                'titre': cer.titre_prosit,
                'sous_titre': cer.etudiant,
                'url': url_for('cer.voir', id=cer.id),
                'date': cer.created_at,
            })

        for rev in SessionRevision.query.filter(
            SessionRevision.titre.ilike(motif)
        ).limit(10).all():
            resultats.append({
                'type': 'Révision', 'icon': 'brain',
                'titre': rev.titre,
                'sous_titre': rev.domaine,
                'url': url_for('revision.voir_cours', id=rev.id),
                'date': rev.created_at,
            })

        for corr in SessionCorrection.query.filter(
            SessionCorrection.titre.ilike(motif)
        ).limit(10).all():
            resultats.append({
                'type': 'Correction', 'icon': 'check-square',
                'titre': corr.titre,
                'sous_titre': corr.type_doc,
                'url': url_for('correction.voir', id=corr.id),
                'date': corr.created_at,
            })

        for qa in SessionQA.query.filter(
            SessionQA.question.ilike(motif)
        ).limit(10).all():
            resultats.append({
                'type': 'Question de cours', 'icon': 'message-circle',
                'titre': qa.question,
                'sous_titre': qa.matiere or '',
                'url': url_for('qa.index') + f'#question-{qa.id}',
                'date': qa.created_at,
            })

        resultats.sort(key=lambda r: r['date'] or datetime.min, reverse=True)

    return render_template('recherche.html',
                           title="Recherche",
                           q=q,
                           resultats=resultats)
