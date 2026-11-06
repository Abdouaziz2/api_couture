from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.utilisateur import Utilisateur
from app.schemas.utilisateur import (
    UtilisateurCreate,
    UtilisateurRead,
    UtilisateurUpdate,
)
from app.services.utilisateur import (
    create_utilisateur,
    get_utilisateur_by_id,
    list_utilisateurs,
    update_utilisateur,
)

router = APIRouter(
    prefix="/utilisateurs",
    tags=["Utilisateurs"],
    dependencies=[Depends(require_admin)],
)


@router.post(
    "",
    response_model=UtilisateurRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un compte utilisateur (Admin)",
    description="Permet à l'administrateur de créer un compte pour un membre de l'atelier.",
)
def create_new_user(
    user_in: UtilisateurCreate,
    db: Session = Depends(get_db),
) -> Utilisateur:
    """Crée un utilisateur après vérification de l'unicité de l'email et hachage du mot de passe."""
    return create_utilisateur(db=db, user_in=user_in)


@router.get(
    "",
    response_model=list[UtilisateurRead],
    summary="Lister tous les comptes utilisateurs (Admin)",
    description="Renvoie la liste complète des utilisateurs enregistrés, triés par nom complet.",
)
def get_all_users(
    db: Session = Depends(get_db),
) -> Sequence[Utilisateur]:
    """Récupère l'ensemble des comptes de personnel."""
    return list_utilisateurs(db=db)


@router.get(
    "/{id}",
    response_model=UtilisateurRead,
    summary="Détail d'un compte utilisateur (Admin)",
    description="Renvoie les détails du compte spécifié par son identifiant.",
)
def get_user_detail(
    id: int,
    db: Session = Depends(get_db),
) -> Utilisateur:
    """Récupère un compte utilisateur par son identifiant ; renvoie 404 s'il n'existe pas."""
    user = get_utilisateur_by_id(db=db, user_id=id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun utilisateur trouvé avec l'identifiant {id}.",
        )
    return user


@router.patch(
    "/{id}",
    response_model=UtilisateurRead,
    summary="Modifier un compte utilisateur (Admin)",
    description="Modifie le nom, le rôle, l'état actif ou le mot de passe d'un compte. Applique RG24.",
)
def patch_user(
    id: int,
    user_in: UtilisateurUpdate,
    db: Session = Depends(get_db),
    current_admin: Utilisateur = Depends(require_admin),
) -> Utilisateur:
    """Applique les modifications partielles au compte utilisateur avec application stricte de RG24."""
    user_db = get_utilisateur_by_id(db=db, user_id=id)
    if user_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun utilisateur trouvé avec l'identifiant {id}.",
        )
    return update_utilisateur(
        db=db,
        user_db=user_db,
        user_in=user_in,
        current_user=current_admin,
    )

