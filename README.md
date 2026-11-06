# API de gestion d'un atelier de couture

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-REST-009688)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2017-4169E1)
![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy%202-red)
![Alembic](https://img.shields.io/badge/Migrations-Alembic-orange)
![Docker](https://img.shields.io/badge/Container-Docker-2496ED)
![Tests](https://img.shields.io/badge/Tests-36%20passing-brightgreen)
![Status](https://img.shields.io/badge/Status-Terminé-brightgreen)

## Présentation du projet

**API de gestion d'un atelier de couture** est le backend d'une application de gestion destiné à moderniser l'atelier de confection de Mamadou à Dakar. 

L'API permet d'enregistrer les clients, de conserver l'historique complet de leurs mensurations, de suivre la confection des commandes selon un workflow rigoureux (en attente, coupe, couture, essayage, retouches, terminée, livrée), de gérer les encaissements multi-modes (Wave, Orange Money, espèces, virement, chèque), de planifier les livraisons et de fournir au patron un tableau de bord analytique en temps réel (chiffre d'affaires, impayés, retards).

Le projet est développé avec **FastAPI**, **PostgreSQL**, **SQLAlchemy 2** et **Alembic**, en appliquant strictement une architecture en couches et 24 règles de gestion métier (**RG1 à RG24**).

---

## Fonctionnalités implémentées

### 1. Authentification & Gestion des utilisateurs (RG21 à RG24)
- Authentification par jeton JWT (`/api/v1/auth/login`, `/api/v1/auth/me`).
- Mots de passe hachés avec l'algorithme sécurisé **Argon2id**.
- Contrôle d'accès basé sur les rôles (**RBAC**) : `admin` (le patron), `accueil` et `tailleur`.
- CRUD complet des utilisateurs réservé à l'administrateur avec protection contre l'auto-rétrogradation et l'auto-désactivation.

### 2. Gestion des clients & Mesures (RG1 à RG4)
- Fiche client complète avec normalisation automatique du téléphone et unicité stricte (**RG1**).
- Recherche textuelle (`q`), filtres par genre et pagination standardisée.
- Synthèse client consolidée (`/resume`) : solde global, commandes en cours et dernières mesures.
- Prise et historisation des mesures corporelles (18 mesures en cm, validation stricte `]0, 300]`, au moins une mesure requise).
- Protection contre la suppression de clients ou de mesures ayant des commandes rattachées (**RG4**).

### 3. Catalogue de confections
- Catalogue complet des prestations de couture (prix de base, délai standard de confection).
- Initialisation automatique via script de seed conforme à l'Annexe B (Boubous, Costumes, Robes, Retouches, etc.).

### 4. Commandes & Workflow de confection (RG5 à RG15)
- Numérotation séquentielle annuelle normalisée `CMD-AAAA-NNNNN` (**RG5**).
- Rattachement automatique des dernières mesures du client (**RG9**).
- Calcul serveur des montants, remises et calcul automatique de la date de livraison prévue (**RG7**, **RG8**).
- Workflow d'avancement d'état strict : `en_attente` ➔ `en_coupe` ➔ `en_couture` ➔ `essayage` ⇄ `retouches` ➔ `terminee` ➔ `livree`.
- Traçabilité et audit intégrale de chaque changement dans la table `historique_statuts` (**RG15**).
- Gestion des annulations avec motif obligatoire en cas d'acompte déjà versé (**RG14**).

### 5. Encaissements & Règlements (RG16, RG17)
- Multi-modes de paiement : Espèces, Wave, Orange Money, Virement bancaire, Chèque.
- Contrôle serveur strict : rejet des dates futures, rejet des montants négatifs, interdiction de dépasser le solde restant (**RG16**).
- Annulation administrative d'un paiement erroné par le patron avec recalcul instantané du solde (**RG17**).

### 6. Livraisons & Tournée (RG18 à RG20)
- Deux modes : retrait à l'atelier ou livraison à domicile (avec adresse obligatoire, **RG18**).
- Synchronisation automatique de la date prévue de commande lors de la planification de remise.
- Blocage de la remise si la commande n'est pas au statut `terminee` ou si le solde n'est pas réglé à 100%, avec possibilité de dérogation explicite pour le gérant (`autoriser_solde_impaye=true`, **RG19**).
- Bascule automatique au statut `livree` et création automatique d'une livraison atelier si non planifiée (**RG20**).
- Consultation du planning et de la tournée des livraisons (`/api/v1/livraisons`).

### 7. Pilotage & Statistiques (Routes 39 à 43)
- Accès exclusif patron (`admin`).
- **Tableau de bord exécutif** : Chiffre d'affaires mensuel, encaissements, commandes en retard, livraisons du jour.
- **Analyse du CA** : Évolution par période (`jour` ou `mois`).
- **Palmarès des ventes** : Volumes et CA généré par type de vêtement.
- **Top clients** : Classement par chiffre d'affaires et historique d'achats.
- **Gestion des impayés** : Commandes non soldées classées par urgence calendaire.

---

## Architecture logicielle

Le projet respecte rigoureusement la séparation des responsabilités imposée :

```text
api_couture/
│
├── alembic/                 # Schéma et versions de migrations
│   └── versions/
│
├── app/
│   ├── dependencies/        # Injection de dépendances et sécurité RBAC
│   ├── models/              # Entités SQLAlchemy 2 (Mapped, mapped_column)
│   ├── routers/             # Contrôleurs FastAPI (1 par domaine, sans logique métier)
│   ├── schemas/             # Modèles Pydantic v2 distincts (Create, Update, Read)
│   ├── services/            # Couche métier isolée hébergeant toutes les règles RG1..RG24
│   ├── config.py            # Chargement typé des variables d'environnement
│   ├── database.py          # Session SQLAlchemy et moteur PostgreSQL
│   └── seed.py              # Initialisation du patron et du catalogue Annexe B
│
├── tests/                   # Suite de tests automatisés (pytest)
│
├── .env.example             # Modèle des variables d'environnement
├── .dockerignore
├── Dockerfile               # Image de production de l'API
├── docker-compose.yaml      # Orchestration complète API + PostgreSQL 17
├── main.py                  # Point d'entrée de l'application FastAPI
└── requirements.txt         # Dépendances Python strictes du module
```

---

## Guide d'installation et de déploiement

### Prérequis
- Docker Desktop et Docker Compose **OU** Python 3.12+ avec PostgreSQL 17.

---

### Option A : Lancement conteneurisé complet (Recommandé)

Cette méthode démarre automatiquement la base de données PostgreSQL 17, applique les migrations Alembic, charge les données de seed et lance l'API.

1. **Cloner le dépôt et entrer dans le dossier :**
   ```bash
   git clone https://github.com/Abdouaziz2/api_couture.git
   cd api_couture
   ```

2. **Créer le fichier d'environnement :**
   ```bash
   cp .env.example .env
   # Sous Windows PowerShell :
   Copy-Item .env.example .env
   ```

3. **Construire et démarrer les conteneurs :**
   ```bash
   docker compose up --build -d
   ```

4. L'API est prête et accessible sur `http://localhost:8000`.

---

### Option B : Installation en environnement de développement local

1. **Créer et activer l'environnement virtuel Python 3.12 :**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Installer les dépendances requises :**
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Configurer les variables d'environnement :**
   ```powershell
   Copy-Item .env.example .env
   ```
   *Vérifier que la variable `DATABASE_URL` pointe vers votre instance locale PostgreSQL.*

4. **Démarrer le conteneur de base de données PostgreSQL :**
   ```powershell
   docker compose up -d db
   ```

5. **Appliquer les migrations Alembic :**
   ```powershell
   alembic upgrade head
   ```

6. **Charger le compte administrateur et le catalogue de base :**
   ```powershell
   python -m app.seed
   ```

7. **Démarrer le serveur de développement Uvicorn :**
   ```powershell
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## Documentation interactive de l'API

Une fois le serveur lancé, la documentation interactive Swagger UI est accessible sur :
- **Swagger UI :** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc :** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Contrôle de santé :** [http://localhost:8000/health](http://localhost:8000/health)

### Identifiants par défaut (générés par le seed)
- **Administrateur (Patron) :**
  - Email : `admin@atelier.sn`
  - Mot de passe : `Admin1234!`

---

## Exécution des tests automatisés

La suite de tests vérifie l'intégralité des 44 routes, des 24 règles de gestion ainsi que le scénario de démonstration complet de l'**Annexe A** (Étapes 1 à 8) :

```powershell
pytest -v
```

Résultat d'exécution :
```text
======================= 36 passed in 22.39s =======================
```

---

## Auteur

**Baye Abdoul Aziz Seck**  
Projet final - Module *Développement d'API avec FastAPI et PostgreSQL*
