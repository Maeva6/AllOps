# AllOps

> Plateforme web tout-en-un pour automatiser les tâches répétitives et
> accompagner la réussite académique des étudiants en ingénierie informatique.

![CI Pipeline](https://github.com/Maeva6/AllOps/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Flask](https://img.shields.io/badge/Flask-3.1-green)
![Docker](https://img.shields.io/badge/Docker-ready-blue)

---

## Sommaire

- [Contexte](#contexte)
- [Fonctionnalités](#fonctionnalités)
- [Stack technique](#stack-technique)
- [Installation](#installation)
- [Configuration](#configuration)
- [Lancer les tests](#lancer-les-tests)
- [Structure du projet](#structure-du-projet)
- [CI/CD](#cicd)
- [Roadmap](#roadmap--améliorations-envisagées)
- [Auteure](#auteure)

---

## Contexte

Projet réalisé dans le cadre de la formation ingénierie informatique à
l'**UCAC-ICAM** (2025-2026), selon la méthodologie **PMBOK**.

**Problème résolu** : les tâches répétitives sur les fichiers (renommage,
fusion, organisation), le suivi des certifications professionnelles et la
préparation aux évaluations consomment un temps précieux sans valeur ajoutée
pour un·e étudiant·e. AllOps centralise ces besoins dans une seule
application.

---

## Fonctionnalités

### Automatisation de fichiers
- Renommage en masse selon un pattern
- Fusion de plusieurs PDFs en un seul document
- Organisation automatique par type (Images, Documents, Code...) avec rollback
- Explorateur de fichiers intégré (accès direct au système hôte depuis WSL)
- Historique complet des opérations, annulables à tout moment

### Suivi des certifications
- Dashboard avec statistiques (validées, en cours, à faire)
- CRUD complet (ajout, modification, suppression)
- Barre de progression niveau actuel → niveau visé (1 à 5)
- Alertes de deadline
- Gestion des ressources d'apprentissage liées à chaque certification

### CER (Compte-Rendu d'Étude / rapports type PROSIT)
- Extraction automatique du contenu d'un fichier source (page de garde, sections)
- Génération de sections assistée par IA
- Export en LaTeX, Word (.docx) et PDF

### Révision IA
- Génération de fiches de cours à partir d'un contenu source
- Génération de quiz de révision par niveau de difficulté
- Historique des sessions et des scores

### Correction IA
- Soumission d'un devoir et correction automatique assistée par IA
- Export du résultat en LaTeX, Word et PDF

### Questions de cours (QA)
- Assistant conversationnel pour poser des questions de cours
- Historique des échanges, consultable et supprimable

### Coin détente
- Mini-jeux : démineur, taquin, memory, quiz
- Pensé comme une pause entre deux sessions de travail

---

## Stack technique

| Domaine | Techno |
|---|---|
| Backend | Python 3.12, Flask 3.1, Flask-SQLAlchemy |
| Base de données | SQLite |
| Frontend | HTML/CSS/JS natif, icônes [Lucide](https://lucide.dev) |
| IA | Groq (Llama), Google Gemini |
| Génération de documents | python-docx, fpdf2, PyMuPDF, LaTeX (TeX Live) |
| DevOps | Docker, docker-compose, GitHub Actions |
| Tests / qualité | pytest, pytest-flask, pytest-cov, flake8 |

---

## Installation

### Prérequis
- Docker Desktop
- WSL2 (si Windows)
- Git

### Démarrage avec Docker (recommandé)

```bash
# 1. Cloner le projet
git clone https://github.com/Maeva6/AllOps.git
cd AllOps

# 2. Copier la configuration
cp .env.example .env
# → renseigner SECRET_KEY, et les clés IA si besoin (voir Configuration)

# 3. Lancer avec Docker
docker-compose up --build
```

L'application est accessible sur **http://localhost:5000**

### Démarrage en local (sans Docker)

```bash
python -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

> Les fonctionnalités d'export Word/PDF/LaTeX reposent sur LibreOffice et
> TeX Live, installés automatiquement dans l'image Docker (voir
> [Dockerfile](Dockerfile)). En local, il faut les installer soi-même pour
> profiter de ces exports.

---

## Configuration

Variables d'environnement (fichier `.env`, voir [.env.example](.env.example)) :

| Variable | Description | Obligatoire |
|---|---|---|
| `SECRET_KEY` | Clé secrète Flask (sessions, CSRF) | Oui |
| `DATABASE_URL` | URI de connexion SQLAlchemy | Non (SQLite par défaut) |
| `GROQ_API_KEY` | Clé API [Groq](https://console.groq.com) pour les modules IA | Non* |
| `GEMINI_API_KEY` | Clé API [Google Gemini](https://ai.google.dev) pour les modules IA | Non* |

\* Sans clé, l'application démarre et fonctionne normalement ; seules les
fonctionnalités IA (révision, correction, QA, génération CER) seront
indisponibles.

---

## Lancer les tests

```bash
# Depuis Docker
docker exec -it allops-web-1 pytest tests/ -v

# En local
pytest tests/ -v

# Avec rapport de couverture
pytest tests/ --cov=app --cov-report=term-missing
```

---

## Structure du projet

```
AllOps/
├── app/
│   ├── __init__.py          # Application factory
│   ├── config.py            # Configuration (variables d'env)
│   ├── extensions.py        # Extensions Flask (SQLAlchemy)
│   ├── models.py            # Modèles de base de données
│   ├── routes/
│   │   ├── main.py          # Tableau de bord
│   │   ├── files.py         # Module Fichiers
│   │   ├── tracker.py       # Module Certifications
│   │   ├── cer.py           # Module CER
│   │   ├── revision.py      # Module Révision IA
│   │   ├── correction.py    # Module Correction IA
│   │   ├── qa.py            # Module Questions de cours
│   │   └── detente.py       # Mini-jeux
│   ├── services/             # Logique métier (génération IA, exports...)
│   ├── static/                # Assets statiques
│   └── templates/             # Templates Jinja2
├── tests/                    # Tests automatisés (pytest)
├── .github/workflows/ci.yml  # Pipeline CI/CD
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── run.py
```

---

## CI/CD

Le pipeline GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml))
s'exécute sur chaque push/PR vers `main` et `develop`, en 3 jobs :

1. **Tests** — exécution de la suite pytest + rapport de couverture
2. **Qualité du code** — analyse flake8 (erreurs critiques de syntaxe/imports)
3. **Build Docker** — construction de l'image et vérification qu'elle démarre correctement

---

## Roadmap / améliorations envisagées

- [ ] Authentification multi-utilisateurs (le projet est actuellement mono-utilisateur)
- [ ] Externaliser le CSS de `base.html` (actuellement en `<style>` inline) vers un fichier statique versionné et minifiable
- [ ] Auto-héberger les icônes Lucide et la police Google Fonts pour ne plus dépendre d'un CDN externe au runtime
- [ ] Tests end-to-end sur les modules IA (CER, révision, correction, QA), aujourd'hui non couverts par `tests/`
- [ ] Gestion d'erreurs plus explicite quand une clé API IA est absente ou invalide (message utilisateur au lieu d'une erreur silencieuse)
- [ ] Migrations de base de données via Alembic/Flask-Migrate plutôt que `db.create_all()`
- [ ] Mode clair/sombre persistant côté serveur (actuellement seulement en `localStorage`)

---

## Auteure

**Maëva TOWA MAWAMBA**
Formation Informatique X2028 — UCAC-ICAM
