import random
import uuid
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient


def fake_phone(prefix: str = "77") -> str:
    return prefix + "".join(str(random.randint(0, 9)) for _ in range(7))


@pytest.fixture
def auth_headers(client: TestClient):
    """Token d'administrateur."""
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@atelier.sn", "password": "Admin1234!"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def accueil_headers(client: TestClient, auth_headers):
    """Utilisateur Accueil."""
    uid = uuid.uuid4().hex[:6]
    email = f"accueil_stat_{uid}@atelier.sn"
    pwd = "AccueilPass123!"

    client.post(
        "/api/v1/utilisateurs",
        headers=auth_headers,
        json={"email": email, "nom_complet": "Fatou Accueil", "mot_de_passe": pwd, "role": "accueil"},
    )
    login_resp = client.post("/api/v1/auth/login", data={"username": email, "password": pwd})
    return {"Authorization": f"Bearer {login_resp.json()['access_token']}"}


@pytest.fixture
def tailleur_headers(client: TestClient, auth_headers):
    """Utilisateur Tailleur."""
    uid = uuid.uuid4().hex[:6]
    email = f"tailleur_stat_{uid}@atelier.sn"
    pwd = "TailleurPass123!"

    client.post(
        "/api/v1/utilisateurs",
        headers=auth_headers,
        json={"email": email, "nom_complet": "Samba Tailleur", "mot_de_passe": pwd, "role": "tailleur"},
    )
    login_resp = client.post("/api/v1/auth/login", data={"username": email, "password": pwd})
    return {"Authorization": f"Bearer {login_resp.json()['access_token']}"}


def test_statistiques_droits_acces_admin_seul(
    client: TestClient,
    auth_headers,
    accueil_headers,
    tailleur_headers,
):
    """Vérifie que seules les requêtes avec le rôle admin ont accès aux statistiques (403 pour accueil et tailleur)."""
    # 1. Non authentifié -> 401
    assert client.get("/api/v1/statistiques/tableau-de-bord").status_code == 401
    assert client.get("/api/v1/statistiques/chiffre-affaires").status_code == 401
    assert client.get("/api/v1/statistiques/types-vetement").status_code == 401
    assert client.get("/api/v1/statistiques/top-clients").status_code == 401
    assert client.get("/api/v1/statistiques/impayes").status_code == 401

    # 2. Accueil -> 403
    assert client.get("/api/v1/statistiques/tableau-de-bord", headers=accueil_headers).status_code == 403
    assert client.get("/api/v1/statistiques/chiffre-affaires", headers=accueil_headers).status_code == 403
    assert client.get("/api/v1/statistiques/types-vetement", headers=accueil_headers).status_code == 403
    assert client.get("/api/v1/statistiques/top-clients", headers=accueil_headers).status_code == 403
    assert client.get("/api/v1/statistiques/impayes", headers=accueil_headers).status_code == 403

    # 3. Tailleur -> 403
    assert client.get("/api/v1/statistiques/tableau-de-bord", headers=tailleur_headers).status_code == 403
    assert client.get("/api/v1/statistiques/chiffre-affaires", headers=tailleur_headers).status_code == 403
    assert client.get("/api/v1/statistiques/types-vetement", headers=tailleur_headers).status_code == 403
    assert client.get("/api/v1/statistiques/top-clients", headers=tailleur_headers).status_code == 403
    assert client.get("/api/v1/statistiques/impayes", headers=tailleur_headers).status_code == 403

    # 4. Admin -> 200
    assert client.get("/api/v1/statistiques/tableau-de-bord", headers=auth_headers).status_code == 200
    assert client.get("/api/v1/statistiques/chiffre-affaires", headers=auth_headers).status_code == 200
    assert client.get("/api/v1/statistiques/types-vetement", headers=auth_headers).status_code == 200
    assert client.get("/api/v1/statistiques/top-clients", headers=auth_headers).status_code == 200
    assert client.get("/api/v1/statistiques/impayes", headers=auth_headers).status_code == 200


def test_statistiques_tableau_de_bord_et_calculs(
    client: TestClient,
    auth_headers,
    accueil_headers,
    tailleur_headers,
):
    """Vérifie la cohérence des calculs du tableau de bord après passage de commande et acompte."""
    # Création d'un client
    cli_resp = client.post(
        "/api/v1/clients",
        headers=accueil_headers,
        json={"nom": "Ndiaye", "prenom": "Aminata", "telephone": fake_phone("70"), "genre": "femme"},
    )
    cli_id = cli_resp.json()["id"]

    # Mesure
    client.post(
        f"/api/v1/clients/{cli_id}/mesures",
        headers=tailleur_headers,
        json={"longueur_robe": 140.0},
    )

    # Récupération catalogue
    cat_resp = client.get("/api/v1/catalogue", headers=auth_headers)
    type_id = cat_resp.json()[0]["id"]

    # Création d'une commande
    cmd_resp = client.post(
        "/api/v1/commandes",
        headers=accueil_headers,
        json={
            "client_id": cli_id,
            "lignes": [{"type_vetement_id": type_id, "quantite": 2, "prix_unitaire": 20000}],
        },
    )
    cmd_data = cmd_resp.json()
    cmd_id = cmd_data["id"]
    assert cmd_data["montant_total"] == 40000

    # Acompte de 15 000 FCFA
    client.post(
        f"/api/v1/commandes/{cmd_id}/paiements",
        headers=accueil_headers,
        json={"montant": 15000, "mode": "wave"},
    )

    # Lecture du tableau de bord
    resp_tb = client.get("/api/v1/statistiques/tableau-de-bord", headers=auth_headers)
    assert resp_tb.status_code == 200
    tb = resp_tb.json()

    assert tb["chiffre_affaires_mois"] >= 40000
    assert tb["encaisse_mois"] >= 15000
    assert tb["nb_commandes_mois"] >= 1
    assert tb["reste_a_encaisser"] >= 25000
    assert "en_attente" in tb["commandes_par_statut"]
    assert isinstance(tb["nb_commandes_en_retard"], int)


def test_statistiques_top_clients_et_impayes(
    client: TestClient,
    auth_headers,
):
    """Vérifie le fonctionnement de top-clients et impayes."""
    resp_top = client.get("/api/v1/statistiques/top-clients?limite=5", headers=auth_headers)
    assert resp_top.status_code == 200
    top_items = resp_top.json()
    assert isinstance(top_items, list)
    if top_items:
        first = top_items[0]
        assert "nom_complet" in first
        assert "chiffre_affaires_total" in first
        assert "telephone" in first

    resp_impayes = client.get("/api/v1/statistiques/impayes", headers=auth_headers)
    assert resp_impayes.status_code == 200
    impayes = resp_impayes.json()
    assert isinstance(impayes, list)
    for imp in impayes:
        assert imp["solde"] > 0
        assert imp["statut"] != "annulee"
