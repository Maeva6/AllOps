import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'cle-temporaire-a-changer'
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or 'sqlite:///../instance/allops.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
