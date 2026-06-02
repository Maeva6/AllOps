from app.extensions import db
from datetime import datetime, timezone
import json

UTC = timezone.utc

# ─── Modèle : Certification ───────────────────────────────────────────────────
class Certification(db.Model):
    __tablename__ = 'certifications'

    id          = db.Column(db.Integer, primary_key=True)
    nom         = db.Column(db.String(200), nullable=False)
    organisme   = db.Column(db.String(100), nullable=False)   # AWS, Docker, Linux Foundation...
    categorie   = db.Column(db.String(100), nullable=False)   # Cloud, DevOps, Sécurité...
    statut      = db.Column(db.String(50),  default='A faire') # A faire / En cours / Validée
    niveau      = db.Column(db.Integer,     default=1)         # 1 à 5
    niveau_vise = db.Column(db.Integer,     default=3)         # 1 à 5
    deadline    = db.Column(db.Date,        nullable=True)
    notes       = db.Column(db.Text,        nullable=True)
    gratuite    = db.Column(db.Boolean,     default=False)
    created_at  = db.Column(db.DateTime,    default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime,    default=datetime.utcnow,
                            onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Certification {self.nom}>'

    def progression(self):
        """Retourne le pourcentage de progression vers le niveau visé"""
        if self.niveau_vise <= 1:
            return 100
        return min(100, int((self.niveau / self.niveau_vise) * 100))

    def jours_restants(self):
        """Retourne le nombre de jours avant la deadline"""
        if not self.deadline:
            return None
        delta = self.deadline - datetime.now(UTC).date()
        return delta.days


# ─── Modèle : Opération Fichier ───────────────────────────────────────────────
class FileOperation(db.Model):
    __tablename__ = 'file_operations'

    id           = db.Column(db.Integer, primary_key=True)
    type_op      = db.Column(db.String(50),  nullable=False)
    nb_fichiers  = db.Column(db.Integer,     default=0)
    details      = db.Column(db.Text,        nullable=True)
    statut       = db.Column(db.String(20),  default='success')
    annule       = db.Column(db.Boolean,     default=False)
    # Données pour le rollback (JSON)
    rollback_data = db.Column(db.Text,       nullable=True)
    created_at   = db.Column(db.DateTime,
                              default=lambda: datetime.now(UTC))

    def get_rollback_data(self):
        if self.rollback_data:
            return json.loads(self.rollback_data)
        return None

    def __repr__(self):
        return f'<FileOperation {self.type_op} - {self.created_at}>'
        
class OrganisationSnapshot(db.Model):
    __tablename__ = 'organisation_snapshots'

    id          = db.Column(db.Integer, primary_key=True)
    dossier     = db.Column(db.String(500), nullable=False)
    mouvements  = db.Column(db.Text, nullable=False)  # JSON
    nb_fichiers = db.Column(db.Integer, default=0)
    annule      = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def get_mouvements(self):
        return json.loads(self.mouvements)

    def __repr__(self):
        return f'<Snapshot {self.dossier} - {self.created_at}>'

class Ressource(db.Model):
    __tablename__ = 'ressources'

    id               = db.Column(db.Integer, primary_key=True)
    certification_id = db.Column(db.Integer,
                                  db.ForeignKey('certifications.id'),
                                  nullable=False)
    titre            = db.Column(db.String(200), nullable=False)
    url              = db.Column(db.String(500), nullable=False)
    type_ressource   = db.Column(db.String(50),  nullable=False)
    # cours / video / doc / pratique / livre
    gratuit          = db.Column(db.Boolean, default=True)
    created_at       = db.Column(db.DateTime,
                                  default=lambda: datetime.now(UTC))

    # Relation avec Certification
    certification = db.relationship(
        'Certification',
        backref=db.backref('ressources', lazy=True, cascade='all, delete-orphan')
    )

    def __repr__(self):
        return f'<Ressource {self.titre}>'

class SessionRevision(db.Model):
    __tablename__ = 'sessions_revision'

    id             = db.Column(db.Integer, primary_key=True)
    titre          = db.Column(db.String(200), nullable=False)
    domaine        = db.Column(db.String(100), nullable=False)
    contenu_source = db.Column(db.Text,        nullable=True)
    cours_genere   = db.Column(db.Text,        nullable=True)
    niveau_quiz    = db.Column(db.Integer,     default=1)
    created_at     = db.Column(db.DateTime,
                                default=lambda: datetime.now(UTC))

    # Relation avec les quiz
    quiz_results = db.relationship(
        'QuizResult', backref='session',
        lazy=True, cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<SessionRevision {self.titre}>'


class QuizResult(db.Model):
    __tablename__ = 'quiz_results'

    id            = db.Column(db.Integer,  primary_key=True)
    session_id    = db.Column(db.Integer,
                               db.ForeignKey('sessions_revision.id'),
                               nullable=False)
    score         = db.Column(db.Integer,  default=0)
    total         = db.Column(db.Integer,  default=0)
    temps_sec     = db.Column(db.Integer,  default=0)
    details       = db.Column(db.Text,     nullable=True) # JSON
    created_at    = db.Column(db.DateTime,
                               default=lambda: datetime.now(UTC))

    def get_details(self):
        if self.details:
            return json.loads(self.details)
        return []

class SessionCER(db.Model):
    __tablename__ = 'sessions_cer'

    id              = db.Column(db.Integer, primary_key=True)
    # Infos page de garde
    titre_prosit    = db.Column(db.String(300), nullable=False)
    numero_prosit   = db.Column(db.String(50),  nullable=True)
    etudiant        = db.Column(db.String(200),  nullable=False)
    pilote          = db.Column(db.String(200),  nullable=True)
    copilote        = db.Column(db.String(200),  nullable=True)
    promotion       = db.Column(db.String(100),  nullable=True)
    annee           = db.Column(db.String(20),   nullable=True)

    # Sections saisies manuellement
    contexte        = db.Column(db.Text, nullable=False)
    besoins         = db.Column(db.Text, nullable=False)
    contraintes     = db.Column(db.Text, nullable=True)
    problematique   = db.Column(db.Text, nullable=False)
    plan_action     = db.Column(db.Text, nullable=False)  # JSON liste

    # Sections IA
    realisation     = db.Column(db.Text, nullable=True)   # Markdown généré
    validation      = db.Column(db.Text, nullable=True)
    conclusion      = db.Column(db.Text, nullable=True)
    bilan           = db.Column(db.Text, nullable=True)
    synthese        = db.Column(db.Text, nullable=True)
    references      = db.Column(db.Text, nullable=True)

    # Fichiers sources (corbeille / workshop)
    contenu_source  = db.Column(db.Text, nullable=True)

    # LaTeX généré
    latex_genere    = db.Column(db.Text, nullable=True)

    statut          = db.Column(db.String(50), default='brouillon')
    # brouillon / genere / complet

    created_at      = db.Column(db.DateTime,
                                 default=lambda: datetime.now(UTC))
    updated_at      = db.Column(db.DateTime,
                                 default=lambda: datetime.now(UTC),
                                 onupdate=lambda: datetime.now(UTC))

    def get_plan_action(self):
        if self.plan_action:
            return json.loads(self.plan_action)
        return []

    def __repr__(self):
        return f'<SessionCER {self.titre_prosit}>'
class SessionCorrection(db.Model):
    __tablename__ = 'sessions_correction'

    id             = db.Column(db.Integer, primary_key=True)
    titre          = db.Column(db.String(200), nullable=False)
    type_doc       = db.Column(db.String(50),  nullable=False)
    # tp / td / corbeille / workshop / exam / autre
    contenu_source = db.Column(db.Text,        nullable=True)
    correction     = db.Column(db.Text,        nullable=True)
    # JSON : liste de {question, reponse, explication, points}
    statut         = db.Column(db.String(20),  default='en_attente')
    created_at     = db.Column(db.DateTime,
                                default=lambda: datetime.now(UTC))

    def get_correction(self):
        if self.correction:
            try:
                return json.loads(self.correction)
            except Exception:
                return []
        return []

    def __repr__(self):
        return f'<SessionCorrection {self.titre}>'
class SessionQA(db.Model):
    __tablename__ = 'sessions_qa'

    id         = db.Column(db.Integer,      primary_key=True)
    question   = db.Column(db.Text,         nullable=False)
    reponse    = db.Column(db.Text,         nullable=True)
    mode       = db.Column(db.String(20),   default='direct')
    matiere    = db.Column(db.String(100),  nullable=True)
    created_at = db.Column(db.DateTime,
                            default=lambda: datetime.now(UTC))

    def __repr__(self):
        return f'<SessionQA {self.question[:40]}>'