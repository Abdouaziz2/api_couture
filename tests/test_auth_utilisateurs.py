import uuid
import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Vérifie que la route de santé répond 200 et {'status': 'ok'}."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_success(client: TestClient):
    """Vérifie la connexion avec identifiants valides (retourne access_token et expires_in)."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@atelier.sn", "password": "Admin1234!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    assert isinstance(data["expires_in"], int)


def test_login_invalid_credentials_rg23(client: TestClient):
    """Vérifie RG23 : même message 401 que l'email soit inconnu ou le mdp faux."""
    # Faux mot de passe
    resp1 = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@atelier.sn", "password": "WrongPassword99!"},
    )
    assert resp1.status_code == 401
    detail1 = resp1.json()["detail"]

    # Email inconnu
    resp2 = client.post(
        "/api/v1/auth/login",
        data={"username": f"inconnu_{uuid.uuid4().hex[:6]}@atelier.sn", "password": "WrongPassword99!"},
    )
    assert resp2.status_code == 401
    detail2 = resp2.json()["detail"]

    assert detail1 == detail2 == "Identifiants de connexion incorrects."


def test_auth_me(client: TestClient):
    """Vérifie la route /auth/me avec jeton valide."""
    # Connexion admin
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@atelier.sn", "password": "Admin1234!"},
    )
    token = login_resp.json()["access_token"]

    # Requête /auth/me
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    user_data = me_resp.json()
    assert user_data["email"] == "admin@atelier.sn"
    assert user_data["role"] == "admin"
    assert "mot_de_passe_hash" not in user_data


def test_crud_utilisateurs_et_rg24(client: TestClient):
    """
    Vérifie le CRUD des utilisateurs par un admin et les règles associées :
    - RG21 : mot de passe min 8 car
    - 409 sur email en doublon
    - 403 pour un non-admin
    - RG24 : interdiction d'auto-désactivation ou rétrogradation d'un admin
    """
    unique_id = uuid.uuid4().hex[:6]
    # 1. Login admin
    login_admin = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@atelier.sn", "password": "Admin1234!"},
    )
    admin_token = login_admin.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Récupérer l'ID de l'admin
    admin_info = client.get("/api/v1/auth/me", headers=admin_headers).json()
    admin_id = admin_info["id"]

    # 2. Création d'un utilisateur Tailleur
    tailleur_email = f"modou_{unique_id}@atelier.sn"
    create_resp = client.post(
        "/api/v1/utilisateurs",
        headers=admin_headers,
        json={
            "email": tailleur_email,
            "nom_complet": "Modou Fall",
            "mot_de_passe": "ModouPass123!",
            "role": "tailleur",
        },
    )
    assert create_resp.status_code == 201
    tailleur_data = create_resp.json()
    tailleur_id = tailleur_data["id"]
    assert tailleur_data["role"] == "tailleur"
    assert "mot_de_passe_hash" not in tailleur_data

    # 3. Doublon d'email -> 409
    dup_resp = client.post(
        "/api/v1/utilisateurs",
        headers=admin_headers,
        json={
            "email": tailleur_email,
            "nom_complet": "Modou Clone",
            "mot_de_passe": "AutrePass123!",
            "role": "tailleur",
        },
    )
    assert dup_resp.status_code == 409

    # 4. Mot de passe trop court (< 8 car) -> 422 (RG21)
    short_pwd_resp = client.post(
        "/api/v1/utilisateurs",
        headers=admin_headers,
        json={
            "email": f"court_{unique_id}@atelier.sn",
            "nom_complet": "Court Test",
            "mot_de_passe": "12345",
            "role": "accueil",
        },
    )
    assert short_pwd_resp.status_code == 422

    # 5. Tentative d'accès à /utilisateurs avec compte Tailleur -> 403
    login_tailleur = client.post(
        "/api/v1/auth/login",
        data={"username": tailleur_email, "password": "ModouPass123!"},
    )
    assert login_tailleur.status_code == 200
    tailleur_token = login_tailleur.json()["access_token"]
    tailleur_headers = {"Authorization": f"Bearer {tailleur_token}"}

    forbidden_resp = client.get("/api/v1/utilisateurs", headers=tailleur_headers)
    assert forbidden_resp.status_code == 403

    # 6. Lister les utilisateurs (Admin)
    list_resp = client.get("/api/v1/utilisateurs", headers=admin_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 2

    # 7. Modifier le tailleur (Admin)
    patch_resp = client.patch(
        f"/api/v1/utilisateurs/{tailleur_id}",
        headers=admin_headers,
        json={"nom_complet": "Modou Fall Master"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["nom_complet"] == "Modou Fall Master"

    # 8. Test RG24 : l'administrateur tente de se désactiver lui-même -> 409
    self_deact = client.patch(
        f"/api/v1/utilisateurs/{admin_id}",
        headers=admin_headers,
        json={"actif": False},
    )
    assert self_deact.status_code == 409
    assert "ne peut pas se désactiver lui-même" in self_deact.json()["detail"]

    # 9. Test RG24 : l'administrateur tente de retirer son propre rôle admin -> 409
    self_demote = client.patch(
        f"/api/v1/utilisateurs/{admin_id}",
        headers=admin_headers,
        json={"role": "tailleur"},
    )
    assert self_demote.status_code == 409
    assert "ne peut pas retirer son propre rôle d'administrateur" in self_demote.json()["detail"]


def test_compte_desactive_rg22(client: TestClient):
    """Vérifie RG22 : un compte désactivé est refusé à la connexion et à l'accès API."""
    unique_id = uuid.uuid4().hex[:6]
    # 1. Login admin
    login_admin = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@atelier.sn", "password": "Admin1234!"},
    )
    admin_token = login_admin.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Créer un utilisateur accueil
    accueil_email = f"astou_{unique_id}@atelier.sn"
    accueil_pass = "AstouPass123!"
    create_resp = client.post(
        "/api/v1/utilisateurs",
        headers=admin_headers,
        json={
            "email": accueil_email,
            "nom_complet": "Astou Diallo",
            "mot_de_passe": accueil_pass,
            "role": "accueil",
        },
    )
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    # 3. Connexion initiale et récupération d'un token
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": accueil_email, "password": accueil_pass},
    )
    assert login_resp.status_code == 200
    user_token = login_resp.json()["access_token"]

    # 4. Désactivation du compte par l'administrateur
    client.patch(
        f"/api/v1/utilisateurs/{user_id}",
        headers=admin_headers,
        json={"actif": False},
    )

    # 5. Tentative de nouvelle connexion -> 401
    login_blocked = client.post(
        "/api/v1/auth/login",
        data={"username": accueil_email, "password": accueil_pass},
    )
    assert login_blocked.status_code == 401
    assert "désactivé" in login_blocked.json()["detail"]

    # 6. Tentative d'utilisation du token précédemment émis -> 401 (RG22)
    api_blocked = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert api_blocked.status_code == 401
    assert "désactivé" in api_blocked.json()["detail"]
