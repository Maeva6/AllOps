from flask import Blueprint, render_template, jsonify, request
from app.data.quiz_questions import get_questions_for_level

detente_bp = Blueprint('detente', __name__, url_prefix='/detente')

@detente_bp.route('/')
def index():
    return render_template('detente/index.html', title="Coin Détente")

@detente_bp.route('/memory')
def memory():
    return render_template('detente/memory.html', title="Memory")

@detente_bp.route('/taquin')
def taquin():
    return render_template('detente/taquin.html', title="Taquin")

@detente_bp.route('/quiz')
def quiz():
    return render_template('detente/quiz.html', title="Quiz DevOps")

@detente_bp.route('/demineur')
def demineur():
    return render_template('detente/demineur.html', title="Démineur")

@detente_bp.route('/quiz/questions/<int:level>')
def quiz_questions(level):
    level = max(1, min(15, level))
    return jsonify(get_questions_for_level(level))