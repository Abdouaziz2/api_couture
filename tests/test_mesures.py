import random
import uuid
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
            "nom_complet": "Mamadou Tailleur",
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
def test_client_id(client: TestClient, accueil_headers):
    """Crée un client de test pour les mesures."""
    resp = client.post(
        "/api/v1/clients",
        headers=accueil_headers,
        json={
            "nom": "Diop",
            "prenom": "Fatou",
            "telephone": fake_phone(prefix="77"),
            "genre": "femme",
        },
    )
    return resp.json()["id"]


def test_scenario_demo_etape_2_et_droits(
    client: TestClient,
    tailleur_headers,
    accueil_headers,
    test_client_id,
):
    """
    Annexe A - Étape 2 :
    Tailleur se connecte et prend les mesures de Fatou.
    L'accueil qui tente la même action reçoit 403.
    """
    payload = {
        "tour_poitrine": 92.5,
        "tour_taille": 74.0,
        "tour_bassin": 98.0,
        "longueur_robe": 140.0,
        "notes": "Mesures pour boubou festif",
    }

    # 1. Tentative par l'accueil -> 403
    resp_accueil = client.post(
        f"/api/v1/clients/{test_client_id}/mesures",
        headers=accueil_headers,
        json=payload,
    )
    assert resp_accueil.status_code == 403

    # 2. Prise par le tailleur -> 201
    resp_tailleur = client.post(
        f"/api/v1/clients/{test_client_id}/mesures",
        headers=tailleur_headers,
        json=payload,
    )
    assert resp_tailleur.status_code == 201
    data = resp_tailleur.json()
    assert data["tour_poitrine"] == 92.5
    assert data["longueur_robe"] == 140.0
    assert data["client_id"] == test_client_id


def test_validation_mesures_rg2(client: TestClient, tailleur_headers, test_client_id):
    """
    Règle RG2 :
    - Au moins une mesure requise
    - Chaque mesure strictement positive (> 0) et <= 300 cm
    """
    # Aucune mesure renseignée -> 422
    resp_vide = client.post(
        f"/api/v1/clients/{test_client_id}/mesures",
        headers=tailleur_headers,
        json={"notes": "Sans mesure"},
    )
    assert resp_vide.status_code == 422

    # Mesure négative ou nulle -> 422
    resp_nulle = client.post(
        f"/api/v1/clients/{test_client_id}/mesures",
        headers=tailleur_headers,
        json={"tour_taille": 0},
    )
    assert resp_nulle.status_code == 422

    # Mesure supérieure à 300 cm -> 422
    resp_trop_grand = client.post(
        f"/api/v1/clients/{test_client_id}/mesures",
        headers=tailleur_headers,
        json={"tour_taille": 305.5},
    )
    assert resp_trop_grand.status_code == 422


def test_historique_et_derniere_mesure_rg3(
    client: TestClient,
    tailleur_headers,
    accueil_headers,
    test_client_id,
):
    """
    Règle RG3 :
    - GET /clients/{id}/mesures renvoie l'historique chronologique inverse
    - GET /clients/{id}/mesures/derniere renvoie la plus récente
    """
    # Prise 1
    m1 = client.post(
        f"/api/v1/clients/{test_client_id}/mesures",
        headers=tailleur_headers,
        json={"tour_taille": 72.0, "notes": "Prise initiale"},
    ).json()

    # Prise 2
    m2 = client.post(
        f"/api/v1/clients/{test_client_id}/mesures",
        headers=tailleur_headers,
        json={"tour_taille": 74.0, "notes": "Prise recente"},
    ).json()

    # Historique complet
    hist_resp = client.get(
        f"/api/v1/clients/{test_client_id}/mesures",
        headers=accueil_headers,
    )
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert len(hist) >= 2
    assert hist[0]["id"] == m2["id"]  # La plus récente en premier

    # Dernière mesure
    last_resp = client.get(
        f"/api/v1/clients/{test_client_id}/mesures/derniere",
        headers=accueil_headers,
    )
    assert last_resp.status_code == 200
    assert last_resp.json()["id"] == m2["id"]
    assert last_resp.json()["tour_taille"] == 74.0


def test_detail_modification_et_suppression_mesure(
    client: TestClient,
    tailleur_headers,
    accueil_headers,
    test_client_id,
):
    """
    Routes 21, 22, 23 :
    - GET /mesures/{id}
    - PATCH /mesures/{id} (403 pour accueil, 422 si supprime toutes les mesures)
    - DELETE /mesures/{id} (403 pour accueil, 204 pour tailleur)
    """
    created = client.post(
        f"/api/v1/clients/{test_client_id}/mesures",
        headers=tailleur_headers,
        json={"carrure_dos": 42.0, "longueur_bras": None, "tour_bras": 32.0},
    ).json()
    mesure_id = created["id"]

    # Consultation GET /mesures/{id}
    get_resp = client.get(f"/api/v1/mesures/{mesure_id}", headers=accueil_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["carrure_dos"] == 42.0

    # Modification par l'accueil -> 403
    assert client.patch(
        f"/api/v1/mesures/{mesure_id}",
        headers=accueil_headers,
        json={"carrure_dos": 44.0},
    ).status_code == 403

    # Modification par le tailleur -> 200
    patch_resp = client.patch(
        f"/api/v1/mesures/{mesure_id}",
        headers=tailleur_headers,
        json={"carrure_dos": 44.0, "notes": "Correction epaule"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["carrure_dos"] == 44.0
    assert patch_resp.json()["notes"] == "Correction epaule"

    # Suppression par l'accueil -> 403
    assert client.delete(
        f"/api/v1/mesures/{mesure_id}",
        headers=accueil_headers,
    ).status_code == 403

    # Suppression par le tailleur -> 204
    del_resp = client.delete(
        f"/api/v1/mesures/{mesure_id}",
        headers=tailleur_headers,
    )
    assert del_resp.status_code == 204

    # Vérification 404 après suppression
    assert client.get(f"/api/v1/mesures/{mesure_id}", headers=accueil_headers).status_code == 404
