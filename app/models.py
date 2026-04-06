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
    type_op      = db.Column(db.String(50),  nullable=False)  # rename / convert / organize
    nb_fichiers  = db.Column(db.Integer,     default=0)
    details      = db.Column(db.Text,        nullable=True)   # description de l'opération
    statut       = db.Column(db.String(20),  default='success') # success / error
    created_at   = db.Column(db.DateTime,    default=datetime.utcnow)

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