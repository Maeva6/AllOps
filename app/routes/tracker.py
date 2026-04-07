from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.extensions import db
from app.models import Certification, Ressource
from datetime import datetime, date, timezone
from app.data.ressources_suggestions import get_suggestions

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


# ─── Ressources d'une certification ──────────────────────────────────────────
@tracker_bp.route('/<int:id>/ressources')
def ressources(id):
    cert        = db.session.get(Certification, id) or abort(404)
    suggestions = get_suggestions(cert.nom, cert.organisme)

    # Filtrer les suggestions pas encore ajoutées
    urls_existantes = {r.url for r in cert.ressources}
    suggestions = [
        s for s in suggestions
        if s['url'] not in urls_existantes
    ]

    return render_template(
        'modules/ressources.html',
        title=f"Ressources – {cert.nom}",
        cert=cert,
        suggestions=suggestions
    )


@tracker_bp.route('/<int:id>/ressources/ajouter', methods=['POST'])
def ajouter_ressource(id):
    cert = db.session.get(Certification, id) or abort(404)

    ressource = Ressource(
        certification_id = id,
        titre            = request.form.get('titre', '').strip(),
        url              = request.form.get('url', '').strip(),
        type_ressource   = request.form.get('type_ressource', 'cours'),
        gratuit          = 'gratuit' in request.form,
    )
    db.session.add(ressource)
    db.session.commit()
    flash('✅ Ressource ajoutée !', 'success')
    return redirect(url_for('tracker.ressources', id=id))


@tracker_bp.route('/ressources/supprimer/<int:rid>', methods=['POST'])
def supprimer_ressource(rid):
    r    = db.session.get(Ressource, rid) or abort(404)
    cert_id = r.certification_id
    db.session.delete(r)
    db.session.commit()
    flash('🗑️ Ressource supprimée.', 'warning')
    return redirect(url_for('tracker.ressources', id=cert_id))


@tracker_bp.route('/<int:id>/ressources/importer', methods=['POST'])
def importer_suggestion(id):
    """Importer une suggestion en un clic"""
    cert = db.session.get(Certification, id) or abort(404)

    ressource = Ressource(
        certification_id = id,
        titre            = request.form.get('titre', '').strip(),
        url              = request.form.get('url', '').strip(),
        type_ressource   = request.form.get('type_ressource', 'cours'),
        gratuit          = request.form.get('gratuit') == 'true',
    )
    db.session.add(ressource)
    db.session.commit()
    flash(f'✅ "{ressource.titre}" ajoutée à tes ressources !', 'success')
    return redirect(url_for('tracker.ressources', id=id))