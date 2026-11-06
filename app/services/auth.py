from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.utilisateur import Utilisateur
from app.services.utilisateur import get_utilisateur_by_email


def authenticate_user(db: Session, email: str, password: str) -> Utilisateur:
    """
    Authentifie un utilisateur avec son email et son mot de passe.
    - Applique la règle RG23 : renvoie la même erreur 401 que l'email soit inconnu ou le mot de passe incorrect.
    - Applique la règle RG22 : refuse la connexion si le compte est inactif.
    """
    utilisateur = get_utilisateur_by_email(db, email)
    if utilisateur is None or not verify_password(password, utilisateur.mot_de_passe_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants de connexion incorrects.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not utilisateur.actif:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ce compte utilisateur a été désactivé.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return utilisateur

