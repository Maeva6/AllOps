# from flask import Blueprint, render_template
# from app.extensions import db
# from app.models import Certification, FileOperation, OrganisationSnapshot

# main_bp = Blueprint('main', __name__, url_prefix='/')

# @main_bp.route('/')
# def index():
#     # Statistiques certifications
#     stats_certs = {
#         'total':     Certification.query.count(),
#         'validees':  Certification.query.filter_by(statut='Validée').count(),
#         'en_cours':  Certification.query.filter_by(statut='En cours').count(),
#         'a_faire':   Certification.query.filter_by(statut='A faire').count(),
#     }

#     # Progression globale
#     if stats_certs['total'] > 0:
#         stats_certs['progression'] = int(
#             (stats_certs['validees'] / stats_certs['total']) * 100
#         )
#     else:
#         stats_certs['progression'] = 0

#     # Certifications urgentes (deadline dans moins de 30 jours)
#     from datetime import date, timedelta
#     dans_30_jours = date.today() + timedelta(days=30)
#     certs_urgentes = Certification.query.filter(
#         Certification.deadline <= dans_30_jours,
#         Certification.deadline >= date.today(),
#         Certification.statut != 'Validée'
#     ).order_by(Certification.deadline).limit(3).all()

#     # Dernières opérations fichiers
#     dernieres_ops = FileOperation.query.order_by(
#         FileOperation.created_at.desc()
#     ).limit(5).all()

#     # Stats fichiers
#     stats_files = {
#         'total_ops':   FileOperation.query.count(),
#         'rename':      FileOperation.query.filter_by(type_op='rename').count(),
#         'merge_pdf':   FileOperation.query.filter_by(type_op='merge_pdf').count(),
#         'organize':    FileOperation.query.filter_by(type_op='organize').count(),
#     }

#     return render_template('index.html',
#                            title="AllOps - Dashboard",
#                            stats_certs=stats_certs,
#                            stats_files=stats_files,
#                            certs_urgentes=certs_urgentes,
#                            dernieres_ops=dernieres_ops)

from flask import Blueprint, render_template
from app.extensions import db
from app.models import Certification, FileOperation

main_bp = Blueprint('main', __name__, url_prefix='/')

@main_bp.route('/')
def index():
    stats = {
        'certs_total':    Certification.query.count(),
        'certs_validees': Certification.query.filter_by(statut='Validée').count(),
        'certs_en_cours': Certification.query.filter_by(statut='En cours').count(),
        'ops_total':      FileOperation.query.count(),
        'ops_today':      FileOperation.query.filter(
            db.func.date(FileOperation.created_at) == db.func.date('now')
        ).count(),
    }
    recent_ops   = FileOperation.query.order_by(
        FileOperation.created_at.desc()
    ).limit(5).all()
    recent_certs = Certification.query.filter_by(
        statut='En cours'
    ).limit(4).all()

    return render_template('index.html',
                           title="Tableau de bord",
                           stats=stats,
                           recent_ops=recent_ops,
                           recent_certs=recent_certs)