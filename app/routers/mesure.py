from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user, require_tailleur
from app.models.mesure import Mesure
from app.schemas.mesure import MesureRead, MesureUpdate
from app.services.mesure import (
    delete_mesure,
    get_mesure_by_id,
    update_mesure,
)

router = APIRouter(
    prefix="/mesures",
    tags=["Mesures"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/{id}",
    response_model=MesureRead,
    summary="Consulter une prise de mesures (Tous rôles)",
    description="Renvoie le détail d'une prise de mesures spécifiée par son identifiant.",
)
def get_measure_by_id(
    id: int,
    db: Session = Depends(get_db),
) -> Mesure:
    """Récupère une mesure par son ID ; 404 si introuvable."""
    mesure = get_mesure_by_id(db=db, mesure_id=id)
    if mesure is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune prise de mesures trouvée avec l'identifiant {id}.",
        )
    return mesure


@router.patch(
    "/{id}",
    response_model=MesureRead,
    summary="Corriger une prise de mesures (Tailleur)",
    description="Corrige une erreur de saisie. Rôle tailleur requis. 422 si la correction supprimait toutes les mesures (RG2).",
    dependencies=[Depends(require_tailleur)],
)
def patch_measure(
    id: int,
    mesure_in: MesureUpdate,
    db: Session = Depends(get_db),
) -> Mesure:
    """Corrige une prise de mesures."""
    mesure_db = get_mesure_by_id(db=db, mesure_id=id)
    if mesure_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune prise de mesures trouvée avec l'identifiant {id}.",
        )
    return update_mesure(db=db, mesure_db=mesure_db, mesure_in=mesure_in)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une prise de mesures (Tailleur)",
    description="Supprime une prise de mesures. Rôle tailleur requis. 409 si une commande les utilise (RG4).",
    dependencies=[Depends(require_tailleur)],
)
def delete_measure_by_id(
    id: int,
    db: Session = Depends(get_db),
) -> None:
    """Supprime une mesure non rattachée à une commande."""
    mesure = get_mesure_by_id(db=db, mesure_id=id)
    if mesure is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune prise de mesures trouvée avec l'identifiant {id}.",
        )
    delete_mesure(db=db, mesure=mesure)
