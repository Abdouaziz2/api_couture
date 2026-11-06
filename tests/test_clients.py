import random
import uuid
import pytest
from fastapi.testclient import TestClient


def fake_phone(prefix: str = "77") -> str:
    """Génère un numéro valide composé uniquement de chiffres."""
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
            "nom_complet": "Awa Diallo",
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


def test_scenario_demo_etape_1_et_rg1(client: TestClient, accueil_headers):
    """
    Annexe A - Étape 1 :
    Accueil crée la cliente Fatou Diop, tel '77 123 45 67'.
    Un second client avec '771234567' est refusé (409 doublon).
    """
    tel_brut = fake_phone(prefix="77")
    # Insertion d'espaces dans le numéro pour tester la normalisation
    tel_original = f"{tel_brut[:2]} {tel_brut[2:5]} {tel_brut[5:7]} {tel_brut[7:]}"
    tel_condense = tel_original.replace(" ", "")

    # 1. Création initiale réussie (201)
    resp1 = client.post(
        "/api/v1/clients",
        headers=accueil_headers,
        json={
            "nom": "Diop",
            "prenom": "Fatou",
            "telephone": tel_original,
            "genre": "femme",
            "adresse": "Dakar, Medina",
        },
    )
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert data1["telephone"] == tel_condense  # Vérification de la normalisation RG1

    # 2. Tentative de création avec le numéro sans espaces -> 409 (RG1)
    resp2 = client.post(
        "/api/v1/clients",
        headers=accueil_headers,
        json={
            "nom": "Diop",
            "prenom": "Fatou Clone",
            "telephone": tel_condense,
            "genre": "femme",
        },
    )
    assert resp2.status_code == 409
    assert "existe déjà" in resp2.json()["detail"]


def test_validation_telephone_invalide_rg1(client: TestClient, accueil_headers):
    """Vérifie RG1 : numéro < 6 chiffres ou contenant des lettres -> 422."""
    # Trop court (< 6 chiffres)
    resp1 = client.post(
        "/api/v1/clients",
        headers=accueil_headers,
        json={
            "nom": "Sow",
            "prenom": "Ali",
            "telephone": "123",
            "genre": "homme",
        },
    )
    assert resp1.status_code == 422

    # Contient des lettres
    resp2 = client.post(
        "/api/v1/clients",
        headers=accueil_headers,
        json={
            "nom": "Sow",
            "prenom": "Ali",
            "telephone": "77abc1234",
            "genre": "homme",
        },
    )
    assert resp2.status_code == 422


def test_recherche_et_pagination_clients(client: TestClient, accueil_headers):
    """Vérifie la recherche q (min 2 car) et la pagination {items, total, limit, offset}."""
    unique_nom = f"ClientRecherche{uuid.uuid4().hex[:5]}"
    client.post(
        "/api/v1/clients",
        headers=accueil_headers,
        json={
            "nom": unique_nom,
            "prenom": "Oumar",
            "telephone": fake_phone(prefix="76"),
            "genre": "homme",
        },
    )

    # Recherche valide
    resp = client.get(
        f"/api/v1/clients?q={unique_nom[:5]}",
        headers=accueil_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["limit"] == 20
    assert data["offset"] == 0
    assert any(c["nom"] == unique_nom for c in data["items"])

    # Recherche invalide (q < 2 car) -> 422
    resp_short = client.get(
        "/api/v1/clients?q=a",
        headers=accueil_headers,
    )
    assert resp_short.status_code == 422


def test_modification_partielle_client(client: TestClient, accueil_headers):
    """
    Vérifie la mise à jour (PATCH) :
    - Garder son propre numéro n'est pas un doublon
    - Vider nom/prénom/téléphone -> 422
    - Numéro déjà attribué à un autre -> 409
    """
    tel1 = fake_phone(prefix="78")
    tel2 = fake_phone(prefix="70")

    resp_c1 = client.post(
        "/api/v1/clients",
        headers=accueil_headers,
        json={"nom": "Ndiaye", "prenom": "Cheikh", "telephone": tel1, "genre": "homme"},
    )
    assert resp_c1.status_code == 201
    c1 = resp_c1.json()

    resp_c2 = client.post(
        "/api/v1/clients",
        headers=accueil_headers,
        json={"nom": "Ba", "prenom": "Mariama", "telephone": tel2, "genre": "femme"},
    )
    assert resp_c2.status_code == 201
    c2 = resp_c2.json()

    # Garder son propre numéro -> 200
    patch_self = client.patch(
        f"/api/v1/clients/{c1['id']}",
        headers=accueil_headers,
        json={"telephone": tel1, "nom": "Ndiaye Modifié"},
    )
    assert patch_self.status_code == 200
    assert patch_self.json()["nom"] == "Ndiaye Modifié"

    # Attribuer le numéro de c2 à c1 -> 409
    patch_dup = client.patch(
        f"/api/v1/clients/{c1['id']}",
        headers=accueil_headers,
        json={"telephone": tel2},
    )
    assert patch_dup.status_code == 409

    # Vider le nom -> 422
    patch_empty = client.patch(
        f"/api/v1/clients/{c1['id']}",
        headers=accueil_headers,
        json={"nom": "   "},
    )
    assert patch_empty.status_code == 422


def test_suppression_client_et_droits(client: TestClient, auth_headers, accueil_headers):
    """Vérifie que seul l'Admin peut supprimer un client (403 pour l'accueil)."""
    tel = fake_phone(prefix="75")
    resp_create = client.post(
        "/api/v1/clients",
        headers=accueil_headers,
        json={"nom": "Gueye", "prenom": "Ibrahima", "telephone": tel, "genre": "homme"},
    )
    assert resp_create.status_code == 201
    created = resp_create.json()
    client_id = created["id"]

    # Tentative par l'accueil -> 403
    del_accueil = client.delete(
        f"/api/v1/clients/{client_id}",
        headers=accueil_headers,
    )
    assert del_accueil.status_code == 403

    # Suppression par l'administrateur -> 204
    del_admin = client.delete(
        f"/api/v1/clients/{client_id}",
        headers=auth_headers,
    )
    assert del_admin.status_code == 204

    # Vérification que le client n'existe plus -> 404
    get_del = client.get(
        f"/api/v1/clients/{client_id}",
        headers=accueil_headers,
    )
    assert get_del.status_code == 404


def test_resume_client(client: TestClient, accueil_headers):
    """Vérifie la route GET /clients/{id}/resume."""
    tel = fake_phone(prefix="76")
    resp_create = client.post(
        "/api/v1/clients",
        headers=accueil_headers,
        json={"nom": "Fall", "prenom": "Aida", "telephone": tel, "genre": "femme"},
    )
    assert resp_create.status_code == 201
    created = resp_create.json()

    resume_resp = client.get(
        f"/api/v1/clients/{created['id']}/resume",
        headers=accueil_headers,
    )
    assert resume_resp.status_code == 200
    resume_data = resume_resp.json()
    assert resume_data["client_id"] == created["id"]
    assert resume_data["nb_commandes"] == 0
    assert resume_data["a_des_mesures"] is False
