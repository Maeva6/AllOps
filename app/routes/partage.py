# app/routes/partage.py
"""Pages publiques en lecture seule, accessibles via un lien à token.

Aucune authentification n'existe dans l'application (mono-utilisateur) :
ces routes servent surtout à donner un lien stable et non devinable
(UUID) à partager avec un camarade ou un pilote, plutôt que l'ID
séquentiel interne.
"""
import json
from flask import Blueprint, render_template, abort
from app.models import SessionCER, SessionRevision

partage_bp = Blueprint('partage', __name__, url_prefix='/partage')


def _md(text):
    import markdown as md
    return md.markdown(text or '', extensions=['extra', 'codehilite'])


@partage_bp.route('/cer/<token>')
def cer_public(token):
    cer = SessionCER.query.filter_by(share_token=token).first()
    if not cer:
        abort(404)

    plan = cer.get_plan_action()
    realisation = {}
    if cer.realisation:
        try:
            realisation = json.loads(cer.realisation)
        except Exception:
            pass

    sections_html = {
        'contexte':      _md(cer.contexte),
        'validation':    _md(cer.validation),
        'conclusion':    _md(cer.conclusion),
        'bilan':         _md(cer.bilan),
        'synthese':      _md(cer.synthese),
        'references':    _md(cer.references),
    }
    realisation_html = {k: _md(v) for k, v in realisation.items()}

    return render_template('partage/cer.html',
                           title=cer.titre_prosit,
                           cer=cer,
                           plan=plan,
                           sections_html=sections_html,
                           realisation_html=realisation_html)


@partage_bp.route('/cours/<token>')
def cours_public(token):
    session_obj = SessionRevision.query.filter_by(share_token=token).first()
    if not session_obj:
        abort(404)

    import markdown as md
    cours_html = md.markdown(
        session_obj.cours_genere or '',
        extensions=['extra', 'codehilite', 'toc']
    )
    return render_template('partage/cours.html',
                           title=session_obj.titre,
                           session_obj=session_obj,
                           cours_html=cours_html)
