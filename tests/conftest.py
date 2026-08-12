import pytest
from app import create_app
from app.extensions import db
from app.config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'cle-de-test'


@pytest.fixture
def app():
    # La config de test doit être passée à create_app() AVANT db.init_app() :
    # Flask-SQLAlchemy résout et met en cache le moteur dès l'initialisation,
    # donc un app.config.update() après coup n'a aucun effet — les tests
    # continueraient de pointer vers la vraie base (DATABASE_URL du .env).
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
