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
    email = f"accueil_liv_{unique_id}@atelier.sn"
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
    email = f"tailleur_liv_{unique_id}@atelier.sn"
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
def client_avec_mesures(client: TestClient, accueil_headers, tailleur_headers):
    """Crée un client avec une prise de mesures valide."""
    tel = fake_phone("78")
    resp_cli = client.post(
        "/api/v1/clients",
        headers=accueil_headers,
        json={
            "nom": "Sow",
            "prenom": "Oumar",
            "telephone": tel,
            "genre": "homme",
        },
    )
    assert resp_cli.status_code == 201
    cli_data = resp_cli.json()
    cli_id = cli_data["id"]

    client.post(
        f"/api/v1/clients/{cli_id}/mesures",
        headers=tailleur_headers,
        json={
            "tour_cou": 41.0,
            "longueur_bras": 65.0,
            "longueur_pantalon": 105.0,
        },
    )
    return cli_data


@pytest.fixture
def type_boubou(client: TestClient, auth_headers):
    """Récupère ou crée un type de vêtement 'Boubou 3 pièces'."""
    resp = client.get("/api/v1/catalogue", headers=auth_headers)
    for item in resp.json():
        if item["nom"] == "Boubou 3 pièces":
            return item

    resp_create = client.post(
        "/api/v1/catalogue",
        headers=auth_headers,
        json={
            "nom": f"Boubou 3 pièces {uuid.uuid4().hex[:4]}",
            "prix_base": 35000,
            "delai_jours": 10,
        },
    )
    return resp_create.json()


def test_rg18_planification_livraison_domicile_validation(
    client: TestClient,
    accueil_headers,
    tailleur_headers,
    client_avec_mesures,
    type_boubou,
):
    """RG18: En mode 'domicile', l'adresse est obligatoire (422)."""
    resp_cmd = client.post(
        "/api/v1/commandes",
        headers=accueil_headers,
        json={
            "client_id": client_avec_mesures["id"],
            "lignes": [
                {
                    "type_vetement_id": type_boubou["id"],
                    "quantite": 1,
                    "prix_unitaire": 35000,
                }
            ],
        },
    )
    assert resp_cmd.status_code == 201
    cmd_id = resp_cmd.json()["id"]

    # Planification à domicile SANS adresse -> 422
    resp_fail = client.put(
        f"/api/v1/commandes/{cmd_id}/livraison",
        headers=accueil_headers,
        json={
            "mode": "domicile",
            "date_prevue": str(date.today() + timedelta(days=5)),
            "adresse": None,
        },
    )
    assert resp_fail.status_code == 422


def test_rg18_planification_et_replanification_synchronise_date_prevue(
    client: TestClient,
    accueil_headers,
    client_avec_mesures,
    type_boubou,
):
    """RG18: Planifier ou replanifier met à jour date_livraison_prevue de la commande."""
    resp_cmd = client.post(
        "/api/v1/commandes",
        headers=accueil_headers,
        json={
            "client_id": client_avec_mesures["id"],
            "lignes": [
                {"type_vetement_id": type_boubou["id"], "quantite": 1, "prix_unitaire": 35000}
            ],
        },
    )
    cmd_id = resp_cmd.json()["id"]

    date_prevue_initiale = str(date.today() + timedelta(days=7))
    resp_plan = client.put(
        f"/api/v1/commandes/{cmd_id}/livraison",
        headers=accueil_headers,
        json={
            "mode": "domicile",
            "date_prevue": date_prevue_initiale,
            "adresse": "Point E, Rue 3, Dakar",
            "livreur": "Mamadou Express",
        },
    )
    assert resp_plan.status_code == 200
    plan_data = resp_plan.json()
    assert plan_data["statut"] == "planifiee"
    assert plan_data["date_prevue"] == date_prevue_initiale

    # Vérification que la commande a été mise à jour (RG18)
    resp_get_cmd = client.get(f"/api/v1/commandes/{cmd_id}", headers=accueil_headers)
    assert resp_get_cmd.json()["date_livraison_prevue"] == date_prevue_initiale

    # Replanification
    date_prevue_nouvelle = str(date.today() + timedelta(days=12))
    resp_replan = client.put(
        f"/api/v1/commandes/{cmd_id}/livraison",
        headers=accueil_headers,
        json={
            "mode": "retrait_atelier",
            "date_prevue": date_prevue_nouvelle,
        },
    )
    assert resp_replan.status_code == 200
    assert resp_replan.json()["mode"] == "retrait_atelier"
    assert resp_replan.json()["date_prevue"] == date_prevue_nouvelle

    resp_get_cmd2 = client.get(f"/api/v1/commandes/{cmd_id}", headers=accueil_headers)
    assert resp_get_cmd2.json()["date_livraison_prevue"] == date_prevue_nouvelle


def test_scenario_annexe_a_etapes_7_et_8(
    client: TestClient,
    accueil_headers,
    tailleur_headers,
    client_avec_mesures,
    type_boubou,
):
    """Scénario Annexe A : Étape 7 (refus de livraison si solde non réglé) et Étape 8 (paiement solde puis confirmation réussie)."""
    # 1. Création de commande (35 000 FCFA)
    resp_cmd = client.post(
        "/api/v1/commandes",
        headers=accueil_headers,
        json={
            "client_id": client_avec_mesures["id"],
            "lignes": [
                {"type_vetement_id": type_boubou["id"], "quantite": 1, "prix_unitaire": 35000}
            ],
        },
    )
    cmd_id = resp_cmd.json()["id"]

    # 2. Acompte de 20 000 FCFA (Reste 15 000 FCFA)
    client.post(
        f"/api/v1/commandes/{cmd_id}/paiements",
        headers=accueil_headers,
        json={"montant": 20000, "mode": "wave"},
    )

    # 3. Avancement de la commande jusqu'à 'terminee'
    resp_sc1 = client.post(f"/api/v1/commandes/{cmd_id}/statut", headers=tailleur_headers, json={"statut": "en_coupe"})
    assert resp_sc1.status_code == 200
    resp_sc2 = client.post(f"/api/v1/commandes/{cmd_id}/statut", headers=tailleur_headers, json={"statut": "en_couture"})
    assert resp_sc2.status_code == 200
    resp_sc3 = client.post(f"/api/v1/commandes/{cmd_id}/statut", headers=tailleur_headers, json={"statut": "terminee"})
    assert resp_sc3.status_code == 200

    # 4. Étape 7 : Tentative de confirmation de livraison alors que solde=15 000 FCFA -> REFUS 409 (RG19)
    resp_liv_refusee = client.post(
        f"/api/v1/commandes/{cmd_id}/livraison/confirmer",
        headers=accueil_headers,
        json={"autoriser_solde_impaye": False},
    )
    assert resp_liv_refusee.status_code == 409
    assert "15000" in resp_liv_refusee.json()["detail"] or "solde" in resp_liv_refusee.json()["detail"]

    # 5. Étape 8 : Paiement du solde restant (15 000 FCFA)
    resp_solde = client.post(
        f"/api/v1/commandes/{cmd_id}/paiements",
        headers=accueil_headers,
        json={"montant": 15000, "mode": "especes"},
    )
    assert resp_solde.status_code == 201

    # 6. Étape 8 : Confirmation de livraison réussie (RG20)
    resp_liv_succes = client.post(
        f"/api/v1/commandes/{cmd_id}/livraison/confirmer",
        headers=accueil_headers,
        json={},
    )
    assert resp_liv_succes.status_code == 200
    liv_data = resp_liv_succes.json()
    assert liv_data["statut"] == "livree"
    assert liv_data["date_effective"] is not None
    assert liv_data["mode"] == "retrait_atelier"  # Création automatique RG20

    # Vérification de l'état final de la commande
    resp_final_cmd = client.get(f"/api/v1/commandes/{cmd_id}", headers=accueil_headers)
    final_cmd = resp_final_cmd.json()
    assert final_cmd["statut"] == "livree"
    assert final_cmd["solde"] == 0
    assert final_cmd["date_livraison_reelle"] is not None


def test_rg19_derogation_solde_impaye(
    client: TestClient,
    accueil_headers,
    tailleur_headers,
    client_avec_mesures,
    type_boubou,
):
    """RG19: Confirmation autorisée avec solde > 0 si autoriser_solde_impaye=true."""
    resp_cmd = client.post(
        "/api/v1/commandes",
        headers=accueil_headers,
        json={
            "client_id": client_avec_mesures["id"],
            "lignes": [
                {"type_vetement_id": type_boubou["id"], "quantite": 1, "prix_unitaire": 35000}
            ],
        },
    )
    cmd_id = resp_cmd.json()["id"]

    # Progression vers terminee
    client.post(f"/api/v1/commandes/{cmd_id}/statut", headers=tailleur_headers, json={"statut": "en_coupe"})
    client.post(f"/api/v1/commandes/{cmd_id}/statut", headers=tailleur_headers, json={"statut": "en_couture"})
    client.post(f"/api/v1/commandes/{cmd_id}/statut", headers=tailleur_headers, json={"statut": "terminee"})

    # Confirmation avec dérogation autoriser_solde_impaye=true
    resp_conf = client.post(
        f"/api/v1/commandes/{cmd_id}/livraison/confirmer",
        headers=accueil_headers,
        json={"autoriser_solde_impaye": True},
    )
    assert resp_conf.status_code == 200
    assert resp_conf.json()["statut"] == "livree"

    # Vérification commande
    resp_cmd_check = client.get(f"/api/v1/commandes/{cmd_id}", headers=accueil_headers)
    assert resp_cmd_check.json()["statut"] == "livree"
    assert resp_cmd_check.json()["solde"] == 35000


def test_rg19_refus_si_non_terminee(
    client: TestClient,
    accueil_headers,
    tailleur_headers,
    client_avec_mesures,
    type_boubou,
):
    """RG19: Une commande ne peut pas être livrée si elle est en cours de fabrication (ex: en_coupe)."""
    resp_cmd = client.post(
        "/api/v1/commandes",
        headers=accueil_headers,
        json={
            "client_id": client_avec_mesures["id"],
            "lignes": [
                {"type_vetement_id": type_boubou["id"], "quantite": 1, "prix_unitaire": 35000}
            ],
        },
    )
    cmd_id = resp_cmd.json()["id"]
    client.post(f"/api/v1/commandes/{cmd_id}/statut", headers=tailleur_headers, json={"statut": "en_coupe"})

    resp_fail = client.post(
        f"/api/v1/commandes/{cmd_id}/livraison/confirmer",
        headers=accueil_headers,
        json={"autoriser_solde_impaye": True},
    )
    assert resp_fail.status_code == 409
    assert "terminee" in resp_fail.json()["detail"]


def test_lister_tournee_livraisons(
    client: TestClient,
    accueil_headers,
    client_avec_mesures,
    type_boubou,
):
    """Route 38: GET /api/v1/livraisons."""
    resp_cmd = client.post(
        "/api/v1/commandes",
        headers=accueil_headers,
        json={
            "client_id": client_avec_mesures["id"],
            "lignes": [
                {"type_vetement_id": type_boubou["id"], "quantite": 1, "prix_unitaire": 35000}
            ],
        },
    )
    cmd_id = resp_cmd.json()["id"]

    client.put(
        f"/api/v1/commandes/{cmd_id}/livraison",
        headers=accueil_headers,
        json={
            "mode": "retrait_atelier",
            "date_prevue": str(date.today()),
        },
    )

    resp_tournee = client.get("/api/v1/livraisons", headers=accueil_headers)
    assert resp_tournee.status_code == 200
    items = resp_tournee.json()
    assert isinstance(items, list)
    assert any(it["commande_id"] == cmd_id for it in items)
