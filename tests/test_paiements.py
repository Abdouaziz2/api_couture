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
def commande_test(client: TestClient, accueil_headers):
    """Crée une commande test avec un montant de 70 000 FCFA."""
    # Création client
    client_data = client.post(
        "/api/v1/clients",
        headers=accueil_headers,
        json={
            "nom": "Sall",
            "prenom": "Moussa",
            "telephone": fake_phone(prefix="70"),
            "genre": "homme",
        },
    ).json()

    # Récupération catalogue
    cat = client.get("/api/v1/catalogue", headers=accueil_headers).json()
    boubou = next(c for c in cat if c["nom"] == "Boubou")

    # Commande : 2 boubous à 35 000 FCFA = 70 000 FCFA
    cmd = client.post(
        "/api/v1/commandes",
        headers=accueil_headers,
        json={
            "client_id": client_data["id"],
            "lignes": [{"type_vetement_id": boubou["id"], "quantite": 2}],
        },
    ).json()
    return cmd


def test_scenario_demo_etape_6_acompte_wave_et_rg16(
    client: TestClient,
    accueil_headers,
    commande_test,
):
    """
    Annexe A - Étape 6 :
    Accueil encaisse un acompte Wave.
    Un paiement supérieur au solde est refusé (409).
    """
    cmd_id = commande_test["id"]
    # Total de la commande = 70 000 FCFA, solde = 70 000 FCFA

    # 1. Tentative de paiement supérieur au solde -> 409 (RG16)
    resp_trop = client.post(
        f"/api/v1/commandes/{cmd_id}/paiements",
        headers=accueil_headers,
        json={"montant": 80000, "mode": "wave"},
    )
    assert resp_trop.status_code == 409
    assert "dépasse le solde restant" in resp_trop.json()["detail"]

    # 2. Encaissement d'un acompte Wave valide de 30 000 FCFA -> 201
    resp_acompte = client.post(
        f"/api/v1/commandes/{cmd_id}/paiements",
        headers=accueil_headers,
        json={
            "montant": 30000,
            "mode": "wave",
            "reference": "WAVE-SN-498213",
        },
    )
    assert resp_acompte.status_code == 201
    paiement = resp_acompte.json()
    assert paiement["montant"] == 30000
    assert paiement["mode"] == "wave"

    # Vérification que la commande reflète le solde restant (70 000 - 30 000 = 40 000 FCFA)
    cmd_updated = client.get(f"/api/v1/commandes/{cmd_id}", headers=accueil_headers).json()
    assert cmd_updated["montant_paye"] == 30000
    assert cmd_updated["solde"] == 40000


def test_regles_gestion_paiement_rg16(
    client: TestClient,
    accueil_headers,
    commande_test,
):
    """
    Règle RG16 :
    - Montant strictement positif (> 0) -> 422
    - Pas de date future -> 422
    - Refusé sur une commande annulée -> 409
    """
    cmd_id = commande_test["id"]

    # Montant <= 0 -> 422
    assert client.post(
        f"/api/v1/commandes/{cmd_id}/paiements",
        headers=accueil_headers,
        json={"montant": 0, "mode": "especes"},
    ).status_code == 422

    # Date future -> 422
    demain = (date.today() + timedelta(days=1)).isoformat()
    resp_future = client.post(
        f"/api/v1/commandes/{cmd_id}/paiements",
        headers=accueil_headers,
        json={"montant": 10000, "mode": "especes", "date_paiement": demain},
    )
    assert resp_future.status_code == 422
    assert "futur" in resp_future.json()["detail"]

    # Annulation de la commande
    client.post(
        f"/api/v1/commandes/{cmd_id}/statut",
        headers=accueil_headers,
        json={"statut": "annulee"},
    )

    # Paiement sur commande annulée -> 409
    resp_annulee = client.post(
        f"/api/v1/commandes/{cmd_id}/paiements",
        headers=accueil_headers,
        json={"montant": 10000, "mode": "especes"},
    )
    assert resp_annulee.status_code == 409
    assert "annulée" in resp_annulee.json()["detail"]


def test_annulation_paiement_admin_rg17(
    client: TestClient,
    accueil_headers,
    auth_headers,
    commande_test,
):
    """
    Règle RG17 :
    - Annulation d'un paiement (Admin uniquement, 403 pour l'accueil).
    - Recalcule le montant payé et le solde de la commande.
    """
    cmd_id = commande_test["id"]

    # 1. Enregistrement d'un paiement de 25 000 FCFA
    p_resp = client.post(
        f"/api/v1/commandes/{cmd_id}/paiements",
        headers=accueil_headers,
        json={"montant": 25000, "mode": "orange_money"},
    ).json()
    p_id = p_resp["id"]

    # 2. Vérification liste des paiements (Route 33)
    list_p = client.get(f"/api/v1/commandes/{cmd_id}/paiements", headers=accueil_headers).json()
    assert len(list_p) == 1
    assert list_p[0]["id"] == p_id

    # 3. Tentative de suppression par l'accueil -> 403
    assert client.delete(f"/api/v1/paiements/{p_id}", headers=accueil_headers).status_code == 403

    # 4. Suppression par l'administrateur -> 204 (RG17)
    del_admin = client.delete(f"/api/v1/paiements/{p_id}", headers=auth_headers)
    assert del_admin.status_code == 204

    # 5. Vérification du recalcul du solde de la commande
    cmd_after = client.get(f"/api/v1/commandes/{cmd_id}", headers=accueil_headers).json()
    assert cmd_after["montant_paye"] == 0
    assert cmd_after["solde"] == 70000
