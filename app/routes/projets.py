from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from app.extensions import db
from app.models import Projet, Tache, ActiviteJournaliere
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

projets_bp = Blueprint('projets', __name__, url_prefix='/projets')


def _parse_date(valeur):
    valeur = (valeur or '').strip()
    if not valeur:
        return None
    try:
        return datetime.strptime(valeur, '%Y-%m-%d').date()
    except ValueError:
        return None


# ─── Liste des projets ─────────────────────────────────────────────────────
@projets_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    pagination = Projet.query.order_by(
        Projet.statut, Projet.echeance
    ).paginate(page=page, per_page=12, error_out=False)

    stats = {
        'total':     Projet.query.count(),
        'en_cours':  Projet.query.filter_by(statut='en_cours').count(),
        'termine':   Projet.query.filter_by(statut='termine').count(),
        'en_pause':  Projet.query.filter_by(statut='en_pause').count(),
    }

    return render_template('modules/projets.html',
                           title="Projets",
                           projets=pagination.items,
                           pagination=pagination,
                           pagination_endpoint='projets.index',
                           stats=stats)


# ─── Ajouter un projet ─────────────────────────────────────────────────────
@projets_bp.route('/nouveau', methods=['GET', 'POST'])
def nouveau():
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        if not nom:
            flash('Le nom du projet est requis.', 'danger')
            return redirect(url_for('projets.nouveau'))

        projet = Projet(
            nom         = nom,
            description = request.form.get('description', '').strip(),
            statut      = request.form.get('statut', 'en_cours'),
            priorite    = request.form.get('priorite', 'normale'),
            date_debut  = _parse_date(request.form.get('date_debut')),
            echeance    = _parse_date(request.form.get('echeance')),
        )
        db.session.add(projet)
        db.session.commit()
        flash(f'✅ Projet "{projet.nom}" créé !', 'success')
        return redirect(url_for('projets.voir', id=projet.id))

    return render_template('modules/projet_form.html',
                           title="Nouveau projet", projet=None)


# ─── Modifier un projet ────────────────────────────────────────────────────
@projets_bp.route('/<int:id>/modifier', methods=['GET', 'POST'])
def modifier(id):
    projet = db.session.get(Projet, id) or abort(404)

    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        if not nom:
            flash('Le nom du projet est requis.', 'danger')
            return redirect(url_for('projets.modifier', id=id))

        projet.nom         = nom
        projet.description = request.form.get('description', '').strip()
        projet.statut      = request.form.get('statut', 'en_cours')
        projet.priorite    = request.form.get('priorite', 'normale')
        projet.date_debut  = _parse_date(request.form.get('date_debut'))
        projet.echeance    = _parse_date(request.form.get('echeance'))
        projet.updated_at  = datetime.now(UTC)

        db.session.commit()
        flash(f'✅ Projet "{projet.nom}" modifié !', 'success')
        return redirect(url_for('projets.voir', id=projet.id))

    return render_template('modules/projet_form.html',
                           title="Modifier le projet", projet=projet)


# ─── Supprimer un projet ───────────────────────────────────────────────────
@projets_bp.route('/<int:id>/supprimer', methods=['POST'])
def supprimer(id):
    projet = db.session.get(Projet, id) or abort(404)
    nom = projet.nom
    db.session.delete(projet)
    db.session.commit()
    flash(f'🗑️ Projet "{nom}" supprimé.', 'warning')
    return redirect(url_for('projets.index'))


# ─── Détail / Kanban d'un projet ───────────────────────────────────────────
@projets_bp.route('/<int:id>')
def voir(id):
    projet = db.session.get(Projet, id) or abort(404)

    colonnes = {
        'a_faire':  [t for t in projet.taches if t.statut == 'a_faire'],
        'en_cours': [t for t in projet.taches if t.statut == 'en_cours'],
        'termine':  [t for t in projet.taches if t.statut == 'termine'],
    }

    return render_template('modules/projet_voir.html',
                           title=projet.nom,
                           projet=projet,
                           colonnes=colonnes)


# ─── Ajouter une tâche ──────────────────────────────────────────────────────
@projets_bp.route('/<int:id>/taches/ajouter', methods=['POST'])
def ajouter_tache(id):
    projet = db.session.get(Projet, id) or abort(404)

    titre = request.form.get('titre', '').strip()
    if titre:
        ordre_max = max([t.ordre for t in projet.taches], default=0)
        tache = Tache(
            projet_id = id,
            titre     = titre,
            echeance  = _parse_date(request.form.get('echeance')),
            ordre     = ordre_max + 1,
        )
        db.session.add(tache)
        db.session.commit()
        flash('✅ Tâche ajoutée !', 'success')

    return redirect(url_for('projets.voir', id=id))


# ─── Changer le statut d'une tâche (kanban) ────────────────────────────────
@projets_bp.route('/taches/<int:tid>/statut', methods=['POST'])
def changer_statut_tache(tid):
    tache = db.session.get(Tache, tid) or abort(404)
    nouveau_statut = request.form.get('statut')
    if nouveau_statut in ['a_faire', 'en_cours', 'termine']:
        tache.statut = nouveau_statut
        db.session.commit()

    return redirect(url_for('projets.voir', id=tache.projet_id))


# ─── Supprimer une tâche ────────────────────────────────────────────────────
@projets_bp.route('/taches/<int:tid>/supprimer', methods=['POST'])
def supprimer_tache(tid):
    tache = db.session.get(Tache, tid) or abort(404)
    projet_id = tache.projet_id
    db.session.delete(tache)
    db.session.commit()
    flash('🗑️ Tâche supprimée.', 'warning')
    return redirect(url_for('projets.voir', id=projet_id))


# ─── Journal d'activité + dashboard temps ──────────────────────────────────
@projets_bp.route('/journal')
def journal():
    aujourdhui = datetime.now(UTC).date()
    debut_semaine = aujourdhui - timedelta(days=aujourdhui.weekday())

    activites = ActiviteJournaliere.query.order_by(
        ActiviteJournaliere.date_activite.desc(),
        ActiviteJournaliere.created_at.desc()
    ).limit(50).all()

    total_jour = db.session.query(db.func.coalesce(
        db.func.sum(ActiviteJournaliere.duree_minutes), 0
    )).filter(ActiviteJournaliere.date_activite == aujourdhui).scalar()

    total_semaine = db.session.query(db.func.coalesce(
        db.func.sum(ActiviteJournaliere.duree_minutes), 0
    )).filter(ActiviteJournaliere.date_activite >= debut_semaine).scalar()

    repartition = {}
    for cat in ActiviteJournaliere.CATEGORIES:
        minutes = db.session.query(db.func.coalesce(
            db.func.sum(ActiviteJournaliere.duree_minutes), 0
        )).filter(
            ActiviteJournaliere.categorie == cat,
            ActiviteJournaliere.date_activite >= debut_semaine
        ).scalar()
        if minutes:
            repartition[cat] = minutes

    projets = Projet.query.filter(Projet.statut != 'termine').order_by(Projet.nom).all()

    return render_template('modules/journal.html',
                           title="Journal d'activité",
                           activites=activites,
                           total_jour=total_jour,
                           total_semaine=total_semaine,
                           repartition=repartition,
                           categories=ActiviteJournaliere.CATEGORIES,
                           projets=projets,
                           today=aujourdhui.strftime('%Y-%m-%d'))


@projets_bp.route('/journal/ajouter', methods=['POST'])
def ajouter_activite():
    titre = request.form.get('titre', '').strip()
    duree = request.form.get('duree_minutes', type=int)

    if not titre or not duree or duree <= 0:
        flash('Titre et durée (minutes) sont requis.', 'danger')
        return redirect(url_for('projets.journal'))

    projet_id = request.form.get('projet_id', type=int)
    if projet_id:
        projet_id = projet_id if db.session.get(Projet, projet_id) else None

    activite = ActiviteJournaliere(
        titre         = titre,
        categorie     = request.form.get('categorie', 'Autre'),
        duree_minutes = duree,
        date_activite = _parse_date(request.form.get('date_activite')) or datetime.now(UTC).date(),
        projet_id     = projet_id,
    )
    db.session.add(activite)
    db.session.commit()
    flash('✅ Activité enregistrée !', 'success')
    return redirect(url_for('projets.journal'))


@projets_bp.route('/journal/<int:id>/supprimer', methods=['POST'])
def supprimer_activite(id):
    activite = db.session.get(ActiviteJournaliere, id) or abort(404)
    db.session.delete(activite)
    db.session.commit()
    flash('🗑️ Activité supprimée.', 'warning')
    return redirect(url_for('projets.journal'))
