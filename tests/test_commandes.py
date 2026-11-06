import random
import uuid
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient


def fake_phone(prefix: str = "77") -> str:
    """Génère un numéro valide composé de chiffres."""
    return prefix + "".join(str(random.randint(0, 9)) for _ in range(7))


@pytest.fixture
def auth_headers(client: TestClient):
    """Génère un token d'administrateur pour les requêtes authentifiées."""
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@atelier.sn", "password": "Admin1234!"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def accueil_headers(client: TestClient, auth_headers):
    """Crée et connecte un utilisateur Accueil."""
    unique_id = uuid.uuid4().hex[:6]
    email = f"accueil_{unique_id}@atelier.sn"
    password = "AccueilPass123!"

    client.post(
        "/api/v1/utilisateurs",
        headers=auth_headers,
        json={
            "email": email,
            "nom_complet": "Awa Accueil",
            "mot_de_passe": password,
            "role": "accueil",
        },
    )

    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def tailleur_headers(client: TestClient, auth_headers):
    """Crée et connecte un utilisateur Tailleur."""
    unique_id = uuid.uuid4().hex[:6]
    email = f"tailleur_{unique_id}@atelier.sn"
    password = "TailleurPass123!"

    client.post(
        "/api/v1/utilisateurs",
        headers=auth_headers,
        json={
            "email": email,
            "nom_complet": "Modou Tailleur",
            "mot_de_passe": password,
            "role": "tailleur",
        },
    )

    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def donnees_base(client: TestClient, auth_headers, accueil_headers, tailleur_headers):
    """Crée une cliente Fatou avec des mesures et récupère les prestations du catalogue."""
    # 1. Création client Fatou
    fatou = client.post(
        "/api/v1/clients",
        headers=accueil_headers,
        json={
            "nom": "Diop",
            "prenom": "Fatou",
            "telephone": fake_phone(prefix="77"),
            "genre": "femme",
        },
    ).json()

    # 2. Prise de mesures par le tailleur
    mesure = client.post(
        f"/api/v1/clients/{fatou['id']}/mesures",
        headers=tailleur_headers,
        json={"tour_poitrine": 94.0, "tour_taille": 76.0, "longueur_robe": 138.0},
    ).json()

    # 3. Récupération catalogue
    cat = client.get("/api/v1/catalogue", headers=accueil_headers).json()
    boubou = next(c for c in cat if c["nom"] == "Boubou")
    pantalon = next(c for c in cat if c["nom"] == "Pantalon")

    return {
        "client": fatou,
        "mesure": mesure,
        "boubou": boubou,
        "pantalon": pantalon,
    }


def test_scenario_demo_etape_3_creation_commande(
    client: TestClient,
    accueil_headers,
    donnees_base,
):
    """
    Annexe A - Étape 3 :
    Accueil crée une commande : 2 boubous et 1 pantalon à prix négocié, avec une remise.
    Vérifier le numéro (RG5), le total (RG7), la date prévue (RG8) et le rattachement automatique aux mesures (RG9).
    """
    fatou = donnees_base["client"]
    mesure = donnees_base["mesure"]
    boubou = donnees_base["boubou"]
    pantalon = donnees_base["pantalon"]

    # 2 boubous à 35 000 FCFA (prix base) + 1 pantalon négocié à 10 000 FCFA (au lieu de 12 000), remise de 5 000 FCFA
    # Total attendu : (2 * 35000 + 1 * 10000) - 5000 = 75 000 FCFA
    # Délai max : Boubou (10 jours) vs Pantalon (4 jours) -> Date commande + 10 jours
    payload = {
        "client_id": fatou["id"],
        "remise": 5000,
        "lignes": [
            {
                "type_vetement_id": boubou["id"],
                "quantite": 2,
                "description": "Bazin riche bleu",
            },
            {
                "type_vetement_id": pantalon["id"],
                "quantite": 1,
                "prix_unitaire": 10000,  # Prix négocié (RG6)
                "description": "Pantalon assorti",
            },
        ],
    }

    resp = client.post("/api/v1/commandes", headers=accueil_headers, json=payload)
    assert resp.status_code == 201
    cmd = resp.json()

    # Vérification RG5 (Numéro)
    annee_courante = date.today().year
    assert cmd["numero"].startswith(f"CMD-{annee_courante}-")

    # Vérification RG7 (Montants)
    assert cmd["montant_total"] == 75000
    assert cmd["remise"] == 5000
    assert cmd["montant_paye"] == 0
    assert cmd["solde"] == 75000

    # Vérification RG8 (Date de livraison prévue automatique)
    date_attendue = (date.today() + timedelta(days=10)).isoformat()
    assert cmd["date_livraison_prevue"] == date_attendue

    # Vérification RG9 (Rattachement automatique aux dernières mesures)
    assert cmd["mesure_id"] == mesure["id"]

    # Statut initial
    assert cmd["statut"] == "en_attente"


def test_scenario_demo_etape_4_transition_invalide(
    client: TestClient,
    accueil_headers,
    donnees_base,
):
    """
    Annexe A - Étape 4 :
    Accueil tente de passer la commande à 'terminee' : refusé (409),
    le message indique les statuts possibles.
    """
    fatou = donnees_base["client"]
    boubou = donnees_base["boubou"]

    cmd = client.post(
        "/api/v1/commandes",
        headers=accueil_headers,
        json={
            "client_id": fatou["id"],
            "lignes": [{"type_vetement_id": boubou["id"], "quantite": 1}],
        },
    ).json()

    # Tentative en_attente -> terminee : 409
    resp_invalide = client.post(
        f"/api/v1/commandes/{cmd['id']}/statut",
        headers=accueil_headers,
        json={"statut": "terminee"},
    )
    assert resp_invalide.status_code == 409
    detail = resp_invalide.json()["detail"]
    assert "Transition interdite" in detail
    assert "en_attente → terminee" in detail
    assert "en_coupe" in detail
    assert "annulee" in detail


def test_scenario_demo_etape_5_workflow_complet_et_historique(
    client: TestClient,
    accueil_headers,
    tailleur_headers,
    donnees_base,
):
    """
    Annexe A - Étape 5 :
    Tailleur fait avancer la commande jusqu'à 'terminee',
    avec un aller-retour essayage / retouches. Vérifier l'historique (RG15).
    """
    fatou = donnees_base["client"]
    boubou = donnees_base["boubou"]

    cmd = client.post(
        "/api/v1/commandes",
        headers=accueil_headers,
        json={
            "client_id": fatou["id"],
            "lignes": [{"type_vetement_id": boubou["id"], "quantite": 1}],
        },
    ).json()
    cmd_id = cmd["id"]

    # 1. en_attente -> en_coupe
    r1 = client.post(
        f"/api/v1/commandes/{cmd_id}/statut",
        headers=tailleur_headers,
        json={"statut": "en_coupe", "commentaire": "Tissu coupé"},
    )
    assert r1.status_code == 200
    assert r1.json()["statut"] == "en_coupe"

    # 2. en_coupe -> en_couture
    r2 = client.post(
        f"/api/v1/commandes/{cmd_id}/statut",
        headers=tailleur_headers,
        json={"statut": "en_couture", "commentaire": "Assemblage"},
    )
    assert r2.status_code == 200
    assert r2.json()["statut"] == "en_couture"

    # 3. en_couture -> essayage
    r3 = client.post(
        f"/api/v1/commandes/{cmd_id}/statut",
        headers=tailleur_headers,
        json={"statut": "essayage", "commentaire": "Pret pour premier essayage"},
    )
    assert r3.status_code == 200
    assert r3.json()["statut"] == "essayage"

    # 4. essayage -> retouches (aller-retour)
    r4 = client.post(
        f"/api/v1/commandes/{cmd_id}/statut",
        headers=tailleur_headers,
        json={"statut": "retouches", "commentaire": "Ajuster la carrure"},
    )
    assert r4.status_code == 200
    assert r4.json()["statut"] == "retouches"

    # 5. retouches -> essayage
    r5 = client.post(
        f"/api/v1/commandes/{cmd_id}/statut",
        headers=tailleur_headers,
        json={"statut": "essayage", "commentaire": "Deuxieme essayage"},
    )
    assert r5.status_code == 200
    assert r5.json()["statut"] == "essayage"

    # 6. essayage -> terminee
    r6 = client.post(
        f"/api/v1/commandes/{cmd_id}/statut",
        headers=tailleur_headers,
        json={"statut": "terminee", "commentaire": "Repassage et finition acheves"},
    )
    assert r6.status_code == 200
    assert r6.json()["statut"] == "terminee"

    # Vérification de l'historique complet (RG15)
    hist_resp = client.get(f"/api/v1/commandes/{cmd_id}/historique", headers=accueil_headers)
    assert hist_resp.status_code == 200
    historique = hist_resp.json()
    assert len(historique) == 7  # 1 initial + 6 transitions
    assert historique[0]["ancien_statut"] is None
    assert historique[0]["nouveau_statut"] == "en_attente"
    assert historique[-1]["nouveau_statut"] == "terminee"


def test_restrictions_annulation_rg14(
    client: TestClient,
    accueil_headers,
    tailleur_headers,
    donnees_base,
):
    """
    Règle RG14 :
    - Le tailleur ne peut pas annuler une commande (403).
    - Passage à 'livree' via route statut est refusé (409 - RG13).
    """
    fatou = donnees_base["client"]
    boubou = donnees_base["boubou"]

    cmd = client.post(
        "/api/v1/commandes",
        headers=accueil_headers,
        json={
            "client_id": fatou["id"],
            "lignes": [{"type_vetement_id": boubou["id"], "quantite": 1}],
        },
    ).json()

    # Tentative d'annulation par le tailleur -> 403
    resp_annul_tailleur = client.post(
        f"/api/v1/commandes/{cmd['id']}/statut",
        headers=tailleur_headers,
        json={"statut": "annulee"},
    )
    assert resp_annul_tailleur.status_code == 403

    # Tentative de poser statut 'livree' directement -> 409
    resp_livree_direct = client.post(
        f"/api/v1/commandes/{cmd['id']}/statut",
        headers=accueil_headers,
        json={"statut": "livree"},
    )
    assert resp_livree_direct.status_code == 409


def test_lignes_commandes_rg10(
    client: TestClient,
    accueil_headers,
    donnees_base,
):
    """
    Règle RG10 :
    - Lignes modifiables seulement en 'en_attente' (409 sinon).
    - Une commande garde toujours au moins une ligne (409 si suppression de la dernière).
    """
    fatou = donnees_base["client"]
    boubou = donnees_base["boubou"]
    pantalon = donnees_base["pantalon"]

    # Commande avec 1 seule ligne
    cmd = client.post(
        "/api/v1/commandes",
        headers=accueil_headers,
        json={
            "client_id": fatou["id"],
            "lignes": [{"type_vetement_id": boubou["id"], "quantite": 1}],
        },
    ).json()
    cmd_id = cmd["id"]
    ligne_id = cmd["lignes"][0]["id"]

    # Tentative de supprimer l'unique ligne -> 409
    del_derniere = client.delete(
        f"/api/v1/commandes/{cmd_id}/lignes/{ligne_id}",
        headers=accueil_headers,
    )
    assert del_derniere.status_code == 409

    # Ajout d'une deuxième ligne -> 201
    add_resp = client.post(
        f"/api/v1/commandes/{cmd_id}/lignes",
        headers=accueil_headers,
        json={"type_vetement_id": pantalon["id"], "quantite": 1},
    )
    assert add_resp.status_code == 201
    assert len(add_resp.json()["lignes"]) == 2

    # Passage en_coupe
    client.post(
        f"/api/v1/commandes/{cmd_id}/statut",
        headers=accueil_headers,
        json={"statut": "en_coupe"},
    )

    # Tentative d'ajout en_coupe -> 409
    add_bloque = client.post(
        f"/api/v1/commandes/{cmd_id}/lignes",
        headers=accueil_headers,
        json={"type_vetement_id": pantalon["id"], "quantite": 1},
    )
    assert add_bloque.status_code == 409
