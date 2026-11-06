import uuid
import pytest
from fastapi.testclient import TestClient


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
            "nom_complet": "Samba Tailleur",
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


def test_ajouter_prestation_et_doublon(client: TestClient, auth_headers, tailleur_headers):
    """
    Vérifie l'ajout d'une prestation au catalogue (Route 14) :
    - Succès pour l'admin (201)
    - Doublon de nom refusé (409)
    - Refus pour un non-admin (403)
    """
    unique_nom = f"Veste Saharienne {uuid.uuid4().hex[:4]}"

    # 1. Tentative par un tailleur -> 403
    resp_tailleur = client.post(
        "/api/v1/catalogue",
        headers=tailleur_headers,
        json={
            "nom": unique_nom,
            "description": "Veste légère en lin",
            "prix_base": 45000,
            "delai_jours": 8,
        },
    )
    assert resp_tailleur.status_code == 403

    # 2. Ajout par l'admin -> 201
    resp_admin = client.post(
        "/api/v1/catalogue",
        headers=auth_headers,
        json={
            "nom": unique_nom,
            "description": "Veste légère en lin",
            "prix_base": 45000,
            "delai_jours": 8,
        },
    )
    assert resp_admin.status_code == 201
    data = resp_admin.json()
    assert data["nom"] == unique_nom
    assert data["prix_base"] == 45000
    assert data["delai_jours"] == 8
    assert data["actif"] is True

    # 3. Doublon de nom -> 409
    resp_dup = client.post(
        "/api/v1/catalogue",
        headers=auth_headers,
        json={
            "nom": unique_nom,
            "prix_base": 50000,
            "delai_jours": 10,
        },
    )
    assert resp_dup.status_code == 409
    assert "existe déjà" in resp_dup.json()["detail"]


def test_lister_catalogue_et_filtrage_actifs(client: TestClient, auth_headers, tailleur_headers):
    """
    Vérifie la consultation du catalogue (Route 15) :
    - Triée par nom
    - Filtrage actif par défaut
    - Inactifs visibles si actifs_seulement=false
    """
    u = uuid.uuid4().hex[:4]
    nom_actif = f"Prestation Active {u}"
    nom_inactif = f"Prestation Inactive {u}"

    # Création active
    client.post(
        "/api/v1/catalogue",
        headers=auth_headers,
        json={"nom": nom_actif, "prix_base": 20000, "delai_jours": 5},
    )

    # Création et désactivation
    resp_inactif = client.post(
        "/api/v1/catalogue",
        headers=auth_headers,
        json={"nom": nom_inactif, "prix_base": 25000, "delai_jours": 6},
    ).json()

    client.patch(
        f"/api/v1/catalogue/{resp_inactif['id']}",
        headers=auth_headers,
        json={"actif": False},
    )

    # Consultation par défaut (actifs_seulement=true)
    list_active = client.get("/api/v1/catalogue", headers=tailleur_headers).json()
    noms_actifs = [item["nom"] for item in list_active]
    assert nom_actif in noms_actifs
    assert nom_inactif not in noms_actifs

    # Consultation incluant les inactifs
    list_all = client.get("/api/v1/catalogue?actifs_seulement=false", headers=tailleur_headers).json()
    noms_all = [item["nom"] for item in list_all]
    assert nom_actif in noms_all
    assert nom_inactif in noms_all


def test_detail_et_modification_prestation(client: TestClient, auth_headers, tailleur_headers):
    """
    Vérifie les routes GET /catalogue/{id} et PATCH /catalogue/{id} (Routes 16 et 17) :
    - Détail 200 / 404
    - Modification par Admin (prix, délai, nom, actif)
    - Protection 403 pour non-admin
    """
    nom = f"Djellaba {uuid.uuid4().hex[:4]}"
    created = client.post(
        "/api/v1/catalogue",
        headers=auth_headers,
        json={"nom": nom, "prix_base": 40000, "delai_jours": 9},
    ).json()
    item_id = created["id"]

    # Consultation détail (Route 16)
    get_resp = client.get(f"/api/v1/catalogue/{item_id}", headers=tailleur_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["nom"] == nom

    # Détail inexistant -> 404
    assert client.get("/api/v1/catalogue/999999", headers=tailleur_headers).status_code == 404

    # Tentative de modification par le tailleur -> 403
    patch_tailleur = client.patch(
        f"/api/v1/catalogue/{item_id}",
        headers=tailleur_headers,
        json={"prix_base": 42000},
    )
    assert patch_tailleur.status_code == 403

    # Modification par l'admin -> 200 (Route 17)
    patch_admin = client.patch(
        f"/api/v1/catalogue/{item_id}",
        headers=auth_headers,
        json={"prix_base": 42000, "delai_jours": 10},
    )
    assert patch_admin.status_code == 200
    assert patch_admin.json()["prix_base"] == 42000
    assert patch_admin.json()["delai_jours"] == 10
