from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.extensions import db
from app.models import Certification
from datetime import datetime, date, timezone

UTC = timezone.utc

tracker_bp = Blueprint('tracker', __name__, url_prefix='/certifications')


# ─── Dashboard principal ──────────────────────────────────────────────────────
@tracker_bp.route('/')
def index():
    certifications = Certification.query.order_by(
        Certification.statut, Certification.deadline
    ).all()

    # Statistiques pour les cartes du haut
    stats = {
        'total':    Certification.query.count(),
        'validees': Certification.query.filter_by(statut='Validée').count(),
        'en_cours': Certification.query.filter_by(statut='En cours').count(),
        'a_faire':  Certification.query.filter_by(statut='A faire').count(),
        'gratuites':Certification.query.filter_by(gratuite=True).count(),
    }

    return render_template('modules/tracker.html',
                           title="Suivi des Certifications",
                           certifications=certifications,
                           stats=stats)


# ─── Ajouter une certification ────────────────────────────────────────────────
@tracker_bp.route('/ajouter', methods=['GET', 'POST'])
def ajouter():
    if request.method == 'POST':
        deadline_str = request.form.get('deadline', '').strip()
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Format de date invalide. Utilisez AAAA-MM-JJ.', 'danger')
                return redirect(url_for('tracker.ajouter'))

        cert = Certification(
            nom         = request.form.get('nom', '').strip(),
            organisme   = request.form.get('organisme', '').strip(),
            categorie   = request.form.get('categorie', '').strip(),
            statut      = request.form.get('statut', 'A faire'),
            niveau      = int(request.form.get('niveau', 1)),
            niveau_vise = int(request.form.get('niveau_vise', 3)),
            deadline    = deadline,
            notes       = request.form.get('notes', '').strip(),
            gratuite    = 'gratuite' in request.form,
        )

        db.session.add(cert)
        db.session.commit()

        flash(f'✅ Certification "{cert.nom}" ajoutée !', 'success')
        return redirect(url_for('tracker.index'))

    return render_template('modules/tracker_form.html',
                           title="Ajouter une certification",
                           cert=None)


# ─── Modifier une certification ───────────────────────────────────────────────
@tracker_bp.route('/modifier/<int:id>', methods=['GET', 'POST'])
def modifier(id):
    cert = Certification.query.get_or_404(id)

    if request.method == 'POST':
        deadline_str = request.form.get('deadline', '').strip()
        if deadline_str:
            try:
                cert.deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Format de date invalide.', 'danger')
                return redirect(url_for('tracker.modifier', id=id))
        else:
            cert.deadline = None

        cert.nom         = request.form.get('nom', '').strip()
        cert.organisme   = request.form.get('organisme', '').strip()
        cert.categorie   = request.form.get('categorie', '').strip()
        cert.statut      = request.form.get('statut', 'A faire')
        cert.niveau      = int(request.form.get('niveau', 1))
        cert.niveau_vise = int(request.form.get('niveau_vise', 3))
        cert.notes       = request.form.get('notes', '').strip()
        cert.gratuite    = 'gratuite' in request.form
        cert.updated_at  = datetime.now(UTC)

        db.session.commit()
        flash(f'✅ Certification "{cert.nom}" modifiée !', 'success')
        return redirect(url_for('tracker.index'))

    return render_template('modules/tracker_form.html',
                           title="Modifier une certification",
                           cert=cert)


# ─── Supprimer une certification ──────────────────────────────────────────────
@tracker_bp.route('/supprimer/<int:id>', methods=['POST'])
def supprimer(id):
    cert = Certification.query.get_or_404(id)
    nom = cert.nom
    db.session.delete(cert)
    db.session.commit()
    flash(f'🗑️ Certification "{nom}" supprimée.', 'warning')
    return redirect(url_for('tracker.index'))


# ─── Changer le statut rapidement ────────────────────────────────────────────
@tracker_bp.route('/statut/<int:id>', methods=['POST'])
def changer_statut(id):
    cert = Certification.query.get_or_404(id)
    nouveau_statut = request.form.get('statut')
    if nouveau_statut in ['A faire', 'En cours', 'Validée']:
        cert.statut = nouveau_statut
        cert.updated_at = datetime.now(UTC)
        db.session.commit()
        flash(f'✅ Statut mis à jour : {nouveau_statut}', 'success')
    return redirect(url_for('tracker.index'))