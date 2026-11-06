from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.utilisateur import Utilisateur
from app.schemas.auth import Token
from app.schemas.utilisateur import UtilisateurRead
from app.services.auth import authenticate_user

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post(
    "/login",
    response_model=Token,
    summary="Connexion utilisateur (OAuth2)",
    description="Permet à un membre du personnel de s'authentifier par formulaire OAuth2 (email + mot de passe).",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Authentifie l'utilisateur et émet un jeton JWT avec sa durée de validité en secondes."""
    utilisateur = authenticate_user(
        db,
        email=form_data.username,
        password=form_data.password,
    )
    access_token, expires_in = create_access_token(subject=utilisateur.email)
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
    )


@router.get(
    "/me",
    response_model=UtilisateurRead,
    summary="Profil de l'utilisateur connecté",
    description="Renvoie les informations du compte de l'utilisateur actuellement authentifié.",
)
def read_current_user_profile(
    current_user: Utilisateur = Depends(get_current_user),
) -> Utilisateur:
    """Renvoie le profil de l'utilisateur connecté (sans données sensibles)."""
    return current_user

