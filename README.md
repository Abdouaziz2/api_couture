# API de gestion d'un atelier de couture

![Python](https://img.shields.io/badge/Python-3.x-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-REST-009688)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-4169E1)
![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy-red)
![Docker](https://img.shields.io/badge/Container-Docker-2496ED)
![Status](https://img.shields.io/badge/Status-En%20cours-orange)

## Présentation du projet

**API de gestion d'un atelier de couture** est un projet de développement d'une API REST destiné à moderniser la gestion quotidienne d'un atelier de couture.

L'application permettra au tailleur de gérer ses clients, conserver l'historique de leurs mesures, enregistrer les commandes, suivre leur production, encaisser les paiements et organiser les livraisons.

Elle permettra également au responsable de l'atelier de consulter les statistiques financières, les commandes en retard et les impayés.

Le projet est réalisé dans le cadre du module **Développement d'API avec FastAPI et PostgreSQL**.

## Objectifs

* Centraliser les informations des clients.
* Conserver l'historique des mesures.
* Gérer les commandes et leur avancement.
* Suivre les acomptes, paiements et soldes.
* Planifier et confirmer les livraisons.
* Contrôler les retards et les impayés.
* Consulter les statistiques de l'atelier.
* Sécuriser l'accès selon les rôles des utilisateurs.

## Technologies utilisées

| Technologie    | Utilisation                                 |
| -------------- | ------------------------------------------- |
| Python         | Langage de programmation                    |
| FastAPI        | Développement de l'API REST                 |
| Pydantic       | Validation des données                      |
| PostgreSQL     | Base de données relationnelle               |
| SQLAlchemy 2   | Mapping objet-relationnel                   |
| Alembic        | Gestion des migrations                      |
| JWT            | Authentification                            |
| Argon2         | Hachage des mots de passe                   |
| Pytest         | Tests automatisés                           |
| Docker         | Conteneurisation                            |
| Git et GitHub  | Gestion du code source                      |
| GitHub Actions | Intégration et déploiement continus (CI/CD) |

## Fonctionnalités prévues

### 1. Authentification et utilisateurs

* Connexion sécurisée avec JWT.
* Gestion des utilisateurs.
* Gestion des rôles : administrateur, accueil et tailleur.
* Contrôle des permissions.

### 2. Gestion des clients

* Création et modification des clients.
* Recherche et pagination.
* Vérification de l'unicité des numéros de téléphone.
* Consultation de l'historique des commandes.

### 3. Gestion des mesures

* Enregistrement des prises de mesures.
* Conservation de l'historique.
* Consultation des dernières mesures.
* Correction des mesures.

### 4. Gestion du catalogue

* Gestion des prestations de couture.
* Définition des prix et délais.
* Activation et désactivation des prestations.

### 5. Gestion des commandes

* Création des commandes.
* Gestion des lignes de commande.
* Calcul automatique des montants.
* Suivi des statuts de production.
* Historique des changements de statut.

### 6. Gestion des paiements

* Enregistrement des acomptes et soldes.
* Paiements en espèces, Wave, Orange Money, virement et chèque.
* Calcul automatique du montant restant.
* Annulation administrative des paiements erronés.

### 7. Gestion des livraisons

* Planification et replanification.
* Livraison à domicile ou retrait à l'atelier.
* Confirmation de livraison.
* Contrôle des soldes impayés.

### 8. Statistiques

* Chiffre d'affaires.
* Encaissements.
* Reste à encaisser.
* Commandes en retard.
* Meilleurs clients.
* Prestations les plus vendues.

## Architecture du projet

```text
api_couture/
│
├── alembic/
│   └── versions/
│
├── app/
│   ├── dependencies/
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   ├── __init__.py
│   ├── config.py
│   └── database.py
│
├── tests/
│
├── .env
├── .env.example
├── .gitignore
├── alembic.ini
├── docker-compose.yaml
├── Dockerfile
├── main.py
├── requirements.txt
└── README.md
```

### Rôle des principaux répertoires

* `app/models/` : modèles des tables SQLAlchemy.
* `app/schemas/` : schémas Pydantic pour les entrées et sorties.
* `app/routers/` : définition des routes HTTP.
* `app/services/` : règles de gestion et logique métier.
* `app/dependencies/` : dépendances communes, authentification et permissions.
* `alembic/` : migrations de la base de données.
* `tests/` : tests automatisés.

## Installation et configuration

### Prérequis

* Python.
* Git.
* Docker Desktop.
* Docker Compose.

### 1. Cloner le projet

```bash
git clone URL_DU_DEPOT
cd api_couture
```

### 2. Créer l'environnement virtuel

Sous Windows :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Installer les dépendances

```powershell
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

Créer une copie du fichier d'exemple :

```powershell
Copy-Item .env.example .env
```

Renseigner les informations de connexion PostgreSQL et générer une clé JWT secrète.

Ne jamais publier le fichier `.env` sur GitHub.

### 5. Démarrer PostgreSQL

```powershell
docker compose --env-file .env up -d db
```

### 6. Exécuter les migrations

Une fois les migrations configurées :

```powershell
alembic upgrade head
```

### 7. Lancer l'API

La commande de lancement sera documentée après la configuration complète de l'application FastAPI.

## Documentation de l'API

La documentation interactive sera accessible à l'adresse :

```text
http://localhost:8000/docs
```

Documentation alternative :

```text
http://localhost:8000/redoc
```

## Tests

Les tests seront exécutés avec :

```powershell
pytest
```

## Conteneurisation et CI/CD

Le projet prévoit :

* Un conteneur Docker pour l'API.
* Un conteneur PostgreSQL.
* Une orchestration avec Docker Compose.
* Une intégration continue avec GitHub Actions.
* L'exécution automatique des tests lors des modifications du dépôt.

## Sécurité

* Authentification par JWT.
* Mots de passe hachés avec Argon2.
* Gestion des permissions par rôle.
* Variables sensibles stockées dans `.env`.
* Fichier `.env` exclu du dépôt Git.

## État du développement

Projet en cours de réalisation.

Les fonctionnalités seront développées progressivement en respectant les trois paliers du cahier des charges :

* **Palier 1 :** authentification, utilisateurs, clients et catalogue.
* **Palier 2 :** mesures, commandes, statuts et paiements.
* **Palier 3 :** livraisons, statistiques, tests, Docker et CI/CD.

## Auteur

**Baye Abdoul Aziz Seck**
