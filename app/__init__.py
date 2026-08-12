from flask import Flask
from app.config import Config
from app.extensions import db, migrate
from app.logging_config import configure_logging
from app.routes.main import main_bp
from app.routes.files import files_bp
from app.routes.tracker import tracker_bp  
from app.routes.detente import detente_bp
from app.routes.cer import cer_bp
from app.routes.revision import revision_bp
from app.models import Certification, FileOperation, OrganisationSnapshot, Ressource, SessionRevision, QuizResult, SessionCER
from app.routes.correction import correction_bp
from app.models import SessionCorrection
from app.routes.qa import qa_bp
from app.models import SessionQA
from app.routes.recherche import recherche_bp
from app.routes.partage import partage_bp
from app.routes.projets import projets_bp
from app.models import Projet, Tache, ActiviteJournaliere
from app.routes.parametres import parametres_bp
from app.models import Parametre
from datetime import datetime, timezone

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)

    from app.models import Certification, FileOperation, OrganisationSnapshot

    app.register_blueprint(main_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(tracker_bp)
    app.register_blueprint(detente_bp)
    app.register_blueprint(revision_bp)
    app.register_blueprint(cer_bp)
    app.register_blueprint(correction_bp)
    app.register_blueprint(qa_bp)
    app.register_blueprint(recherche_bp)
    app.register_blueprint(partage_bp)
    app.register_blueprint(projets_bp)
    app.register_blueprint(parametres_bp)


    @app.context_processor
    def inject_now():
        return {'now': datetime.now(timezone.utc)}

    @app.context_processor
    def inject_theme():
        return {'theme_actuel': Parametre.get().theme}

    return app
