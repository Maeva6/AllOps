from flask import Flask
from app.config import Config
from app.extensions import db
from app.routes.main import main_bp
from app.routes.files import files_bp
from app.routes.tracker import tracker_bp  
from app.models import Certification, FileOperation, OrganisationSnapshot, Ressource

from datetime import datetime, timezone

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    from app.models import Certification, FileOperation, OrganisationSnapshot

    app.register_blueprint(main_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(tracker_bp)


    @app.context_processor
    def inject_now():
        return {'now': datetime.now(timezone.utc)}

    with app.app_context():
        db.create_all()

    return app
