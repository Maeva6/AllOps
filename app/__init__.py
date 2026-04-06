from flask import Flask
from app.config import Config
from app.extensions import db
from app.routes.main import main_bp
from app.routes.files import files_bp
from app.routes.tracker import tracker_bp  
from app.models import Certification, FileOperation, OrganisationSnapshot


# Import des blueprints
from app.routes.main import main_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialisation des extensions
    db.init_app(app)

    # Enregistrement des blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(tracker_bp)

    # Création des tables
    with app.app_context():
        db.create_all()

    return app
