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

### Tableau de bord
- Vue d'ensemble de l'activité (certifications, CER, révisions...)
- Bannière de rappel pour les certifications dont la deadline approche (≤ 30 jours)
- Recherche globale (`/recherche`) sur les certifications, CER, révisions, corrections et questions de cours

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

### Projets — planification & journal d'activité
- Suivi de projets avec statut, priorité et échéance
- Tableau **Kanban** par projet (À faire / En cours / Terminé)
- **Journal d'activité** : enregistrement du temps passé (titre, durée, catégorie), avec ou sans lien vers un projet
- Dashboard temps : total du jour/de la semaine, répartition par catégorie

### CER (Compte-Rendu d'Étude / rapports type PROSIT)
- Extraction automatique du contenu d'un fichier source (page de garde, sections)
- Génération de sections assistée par IA, en **streaming** (réponse affichée au fil de la génération)
- Export en LaTeX, Word (.docx) et PDF
- Partage d'un lien public en lecture seule

### Révision IA
- Génération de fiches de cours à partir d'un contenu source, en streaming
- **Flashcards** avec répétition espacée (système de Leitner, 5 boîtes)
- Génération de quiz de révision par niveau de difficulté
- Suivi de progression : évolution des scores, moyenne par domaine
- Historique des sessions et des scores
- Partage d'un lien public en lecture seule

### Correction IA
- Soumission d'un devoir et correction automatique assistée par IA
- Export du résultat en LaTeX, Word et PDF

### Questions de cours (QA)
- Assistant conversationnel pour poser des questions de cours, réponses en streaming
- Historique des échanges, consultable et supprimable

### Coin détente
- Mini-jeux : démineur, taquin, memory, quiz
- Pensé comme une pause entre deux sessions de travail

---

## Stack technique

| Domaine | Techno |
|---|---|
| Backend | Python 3.12, Flask 3.1, Flask-SQLAlchemy |
| Base de données | SQLite, migrations via Flask-Migrate (Alembic) |
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

### Base de données et migrations

Le schéma est géré par [Flask-Migrate](https://flask-migrate.readthedocs.io)
(Alembic). Avec Docker, `flask db upgrade` s'exécute automatiquement au
démarrage du conteneur (voir le `CMD` du [Dockerfile](Dockerfile)) : rien à
faire de plus.

En local, après l'installation :

```bash
flask db upgrade
```

Après toute modification d'un modèle dans `app/models.py`, génère une
nouvelle migration puis applique-la :

```bash
flask db migrate -m "Description du changement"
flask db upgrade
```

> Si tu avais déjà une base `instance/allops.db` créée avant l'introduction
> des migrations (schéma créé via `db.create_all()`), il faut d'abord la
> faire adopter par Alembic sans rejouer les créations de table :
> `flask db stamp head`. Ensuite seulement, les futures migrations
> s'appliqueront normalement avec `flask db upgrade`.

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
│   ├── extensions.py        # Extensions Flask (SQLAlchemy, Migrate)
│   ├── logging_config.py    # Configuration des logs (fichier + stdout)
│   ├── models.py            # Modèles de base de données
│   ├── routes/
│   │   ├── main.py          # Tableau de bord
│   │   ├── files.py         # Module Fichiers
│   │   ├── tracker.py       # Module Certifications
│   │   ├── projets.py       # Module Projets (kanban + journal d'activité)
│   │   ├── cer.py           # Module CER
│   │   ├── revision.py      # Module Révision IA (+ flashcards, progression)
│   │   ├── correction.py    # Module Correction IA
│   │   ├── qa.py            # Module Questions de cours
│   │   ├── recherche.py     # Recherche globale
│   │   ├── partage.py       # Liens de partage publics (CER, révision)
│   │   └── detente.py       # Mini-jeux
│   ├── services/             # Logique métier (génération IA, exports, extraction...)
│   ├── static/                # Assets statiques (CSS, JS, polices, Lucide)
│   └── templates/             # Templates Jinja2
├── migrations/                # Migrations Alembic (Flask-Migrate)
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
s'exécute sur chaque push/PR vers `main` et `develop`, en 4 jobs :

1. **Tests** — exécution de la suite pytest + rapport de couverture
2. **Qualité du code** — analyse flake8 (erreurs critiques de syntaxe/imports)
3. **Migrations DB** — applique les migrations sur une base neuve puis `flask db check`, pour détecter tout modèle modifié sans migration associée
4. **Build Docker** — construction de l'image et vérification qu'elle démarre correctement

---

## Roadmap / améliorations envisagées

- [ ] Authentification multi-utilisateurs (le projet est actuellement mono-utilisateur)
- [ ] Mode clair/sombre persistant côté serveur (actuellement seulement en `localStorage`)
- [ ] Étendre la couverture de tests IA (CER, révision, correction, QA) aux cas d'erreur réseau/quota réels, au-delà des mocks
- [ ] Minuteur start/stop pour le journal d'activité (actuellement saisie manuelle de la durée)
- [ ] Lier les tâches de projet aux Certifications / CER existants

Déjà fait :
- [x] CSS externalisé (`app/static/css/app.css`) plutôt qu'un `<style>` inline dans `base.html`
- [x] Icônes Lucide et polices Google Fonts auto-hébergées (`app/static/js`, `app/static/fonts`) — plus de dépendance CDN au runtime
- [x] Erreurs IA (Groq) traduites en messages lisibles via `app/services/ai_errors.py`, au lieu de traces brutes
- [x] Migrations de base de données via Flask-Migrate (`migrations/`) plutôt que `db.create_all()`
- [x] Tests pour les modules IA (CER, révision, correction, QA), appels externes mockés
- [x] `routes/cer.py` allégé : logique d'extraction/génération Word déplacée vers `services/cer_service.py`
- [x] Réponses IA en streaming (CER, révision, QA) plutôt qu'une attente bloquante
- [x] Anti-spam / garde de concurrence sur les appels IA (`ai_guard`)
- [x] Pagination réelle sur les listes (certifications, CER, révisions, corrections, historique fichiers)
- [x] Logs structurés (fichier + stdout) via `app/logging_config.py`
- [x] Job CI dédié à la vérification des migrations (`flask db check`)
- [x] Rappels de deadlines sur le tableau de bord
- [x] Flashcards à répétition espacée (système de Leitner)
- [x] Recherche globale multi-modules
- [x] Partage de CER et de fiches de révision via lien public en lecture seule
- [x] Suivi de progression des quiz de révision (graphique, moyenne par domaine)
- [x] Module Projets : suivi kanban + journal d'activité avec durée

---

## Auteure

**Maëva TOWA MAWAMBA**
Formation Informatique X2028 — UCAC-ICAM
