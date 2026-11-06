from typing import Callable, Sequence

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import decode_access_token
from app.database import get_db
from app.models.utilisateur import RoleUtilisateur, Utilisateur
from app.services.utilisateur import get_utilisateur_by_email

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login"
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Utilisateur:
    """
    Extrait et valide l'utilisateur à partir du jeton JWT.
    - Vérifie la validité et la signature du token.
    - Applique la règle RG22 : refuse immédiatement l'accès si le compte est désactivé.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Jeton d'authentification invalide ou expiré.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    email: str | None = payload.get("sub")
    if email is None:
        raise credentials_exception

    utilisateur = get_utilisateur_by_email(db, email=email)
    if utilisateur is None:
        raise credentials_exception

    # Conforme RG22 : Un compte désactivé est refusé immédiatement, même avec un jeton valide
    if not utilisateur.actif:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ce compte utilisateur a été désactivé.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return utilisateur


def require_roles(*allowed_roles: RoleUtilisateur) -> Callable[..., Utilisateur]:
    """
    Générateur de dépendance vérifiant que l'utilisateur connecté possède l'un des rôles requis.
    Renvoie 403 en cas de rôle insuffisant (conforme aux spécifications).
    """

    def role_checker(
        current_user: Utilisateur = Depends(get_current_user),
    ) -> Utilisateur:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Droits insuffisants pour accéder à cette ressource.",
            )
        return current_user

    return role_checker


# Raccourcis pour les rôles applicatifs
require_admin = require_roles(RoleUtilisateur.ADMIN)
require_tailleur = require_roles(RoleUtilisateur.TAILLEUR, RoleUtilisateur.ADMIN)
require_accueil = require_roles(RoleUtilisateur.ACCUEIL, RoleUtilisateur.ADMIN)
