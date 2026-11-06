import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models.utilisateur import RoleUtilisateur, Utilisateur
from app.core.security import hash_password
from main import app


@pytest.fixture(scope="session")
def client():
    """Client de test FastAPI."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def db_session():
    """Session de base de données pour les fixtures de test."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

