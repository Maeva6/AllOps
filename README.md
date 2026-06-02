# AllOps 🚀

> Plateforme d'automatisation des tâches quotidiennes et de suivi
> des certifications pour étudiants en ingénierie informatique.

![CI Pipeline](https://github.com/Maeva6/AllOps/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Flask](https://img.shields.io/badge/Flask-3.1-green)
![Docker](https://img.shields.io/badge/Docker-ready-blue)
![Tests](https://img.shields.io/badge/Tests-16%20passed-brightgreen)

---

## 📋 Contexte

Projet réalisé dans le cadre de la formation ingénierie informatique
à l'**UCAC-ICAM** (2025-2026), selon la méthodologie **PMBOK**.

**Problème résolu** : les tâches répétitives sur les fichiers
(renommage, conversion, organisation) et le suivi des certifications
professionnelles consomment un temps précieux sans valeur ajoutée.

---

## ✨ Fonctionnalités

### 📁 Module Automatisation de Fichiers
| Fonctionnalité | Description |
|---|---|
| Renommage en masse | Renomme tous les fichiers d'un dossier selon un pattern |
| Fusion de PDFs | Fusionne plusieurs PDFs en un seul fichier |
| Organisation automatique | Classe les fichiers par type (Images, Documents, Code...) |
| Rollback | Annule n'importe quelle organisation d'un clic |

### 🎯 Module Suivi des Certifications
| Fonctionnalité | Description |
|---|---|
| Dashboard | Vue d'ensemble avec statistiques |
| CRUD complet | Ajouter, modifier, supprimer une certification |
| Barre de progression | Niveau actuel → niveau visé (1 à 5) |
| Statuts | À faire / En cours / Validée |
| Deadlines | Alerte quand la date approche |

### 🗂️ Explorateur de fichiers intégré
- Navigation visuelle dans les dossiers
- Accès direct au Bureau Windows depuis WSL
- Raccourcis rapides (Bureau, Documents, Téléchargements)

---

## 🛠️ Stack Technique
Améliorer une présentation PowerPoint avec des iconesParfait ! Le pipeline CI/CD est opérationnel. Faisons le point sur ce qu'on a accompli :
✅ Phase 1 — Démarrage
✅ Phase 2 — Planification (WBS + Gantt)
✅ Phase 3 — Développement
   ✅ Architecture Flask
   ✅ Module Fichiers (renommage, fusion PDF, organisation + rollback)
   ✅ Module Certifications (CRUD, progression, statuts)
   ✅ Docker + docker-compose
   ✅ CI/CD GitHub Actions
✅ 16 tests passent

🚀 On attaque Phase 4 — Tests & Clôture
Il reste selon notre Gantt :
4.1 Tests fonctionnels complets
4.2 Tests utilisateurs (tes camarades)
4.3 Corrections bugs
4.4 Documentation README
4.5 Livraison finale

📝 Commençons par le README
C'est le premier fichier que tout le monde voit sur GitHub. Ouvre README.md et remplace son contenu :
markdown# AllOps 🚀

> Plateforme d'automatisation des tâches quotidiennes et de suivi
> des certifications pour étudiants en ingénierie informatique.

![CI Pipeline](https://github.com/Maeva6/AllOps/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Flask](https://img.shields.io/badge/Flask-3.1-green)
![Docker](https://img.shields.io/badge/Docker-ready-blue)
![Tests](https://img.shields.io/badge/Tests-16%20passed-brightgreen)

---

## 📋 Contexte

Projet réalisé dans le cadre de la formation ingénierie informatique
à l'**UCAC-ICAM** (2025-2026), selon la méthodologie **PMBOK**.

**Problème résolu** : les tâches répétitives sur les fichiers
(renommage, conversion, organisation) et le suivi des certifications
professionnelles consomment un temps précieux sans valeur ajoutée.

---

## ✨ Fonctionnalités

### 📁 Module Automatisation de Fichiers
| Fonctionnalité | Description |
|---|---|
| Renommage en masse | Renomme tous les fichiers d'un dossier selon un pattern |
| Fusion de PDFs | Fusionne plusieurs PDFs en un seul fichier |
| Organisation automatique | Classe les fichiers par type (Images, Documents, Code...) |
| Rollback | Annule n'importe quelle organisation d'un clic |

### 🎯 Module Suivi des Certifications
| Fonctionnalité | Description |
|---|---|
| Dashboard | Vue d'ensemble avec statistiques |
| CRUD complet | Ajouter, modifier, supprimer une certification |
| Barre de progression | Niveau actuel → niveau visé (1 à 5) |
| Statuts | À faire / En cours / Validée |
| Deadlines | Alerte quand la date approche |

### 🗂️ Explorateur de fichiers intégré
- Navigation visuelle dans les dossiers
- Accès direct au Bureau Windows depuis WSL
- Raccourcis rapides (Bureau, Documents, Téléchargements)

---

## 🛠️ Stack Technique
Backend  : Python 3.12 + Flask 3.1
Base de données : SQLite (via SQLAlchemy)
Frontend : Bootstrap 5 + JavaScript vanilla
DevOps   : Docker + docker-compose + GitHub Actions
Tests    : pytest + pytest-flask + pytest-cov

---

## 🚀 Installation et Démarrage

### Prérequis
- Docker Desktop installé
- WSL2 (si Windows)
- Git

### Démarrage en 3 commandes
```bash
# 1. Cloner le projet
git clone https://github.com/Maeva6/AllOps.git
cd AllOps

# 2. Copier la configuration
cp .env.example .env

# 3. Lancer avec Docker
docker-compose up --build
```

L'application est accessible sur **http://localhost:5000**

---

## 🧪 Lancer les tests
```bash
# Depuis Docker
docker exec -it allops-web-1 pytest tests/ -v

# Avec rapport de couverture
docker exec -it allops-web-1 pytest tests/ --cov=app --cov-report=term-missing
```

---

## 📁 Structure du projet
AllOps/
├── app/
│   ├── init.py          # Application Factory
│   ├── config.py            # Configuration
│   ├── extensions.py        # Extensions Flask (SQLAlchemy)
│   ├── models.py            # Modèles de base de données
│   ├── routes/
│   │   ├── main.py          # Route principale
│   │   ├── files.py         # Module Fichiers
│   │   └── tracker.py       # Module Certifications
│   └── templates/
│       ├── base.html        # Template de base
│       └── modules/
│           ├── files.html       # Interface fichiers
│           ├── tracker.html     # Dashboard certifications
│           ├── tracker_form.html # Formulaire certification
│           └── historique.html  # Historique organisations
├── tests/
│   └── test_app.py          # 16 tests automatisés
├── .github/
│   └── workflows/
│       └── ci.yml           # Pipeline CI/CD
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md

---

## 📊 Gestion de Projet

Ce projet a été conduit selon la méthodologie **PMBOK 7e édition** :

| Document | Description |
|---|---|
| Charte de Projet | Définition officielle du projet |
| WBS | Décomposition de toutes les tâches |
| Gantt | Planning détaillé (24 Mars → 15 Avril 2026) |

---

## 👩‍💻 Auteure

**Maëva TOWA MAWAMBA**
Formation Informatique X2028 — UCAC-ICAM
Stage FGCL 2025-2026

---

## 📄 Licence

Projet académique — UCAC-ICAM 2025-2026