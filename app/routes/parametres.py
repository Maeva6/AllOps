from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Parametre

parametres_bp = Blueprint('parametres', __name__, url_prefix='/parametres')


@parametres_bp.route('/theme', methods=['POST'])
def theme():
    data = request.get_json(silent=True) or request.form
    valeur = (data.get('theme') or '').strip()

    if valeur not in ('dark', 'light'):
        return jsonify({'ok': False, 'erreur': 'Thème invalide.'}), 400

    parametre = Parametre.get()
    parametre.theme = valeur
    db.session.commit()

    return jsonify({'ok': True, 'theme': parametre.theme})
