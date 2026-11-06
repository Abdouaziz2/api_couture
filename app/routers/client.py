from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.models.client import Client, GenreClient
from app.models.utilisateur import Utilisateur
from app.schemas.client import (
    ClientCreate,
    ClientPagination,
    ClientRead,
    ClientResume,
    ClientUpdate,
)
from app.services.client import (
    create_client,
    delete_client,
    get_client_by_id,
    get_client_resume,
    list_clients,
    update_client,
)

router = APIRouter(
    prefix="/clients",
    tags=["Clients"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "",
    response_model=ClientRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un client (Tous rôles)",
    description="Enregistre un nouveau client après normalisation et contrôle d'unicité du téléphone (RG1).",
)
def create_new_client(
    client_in: ClientCreate,
    db: Session = Depends(get_db),
) -> Client:
    """Crée un client. Renvoie 201 en cas de succès, 409 si doublon, 422 si téléphone invalide."""
    return create_client(db=db, client_in=client_in)


@router.get(
    "",
    response_model=ClientPagination,
    summary="Lister les clients avec recherche et pagination (Tous rôles)",
    description="Renvoie la liste des clients triée par nom puis prénom. Recherche via 'q' (min 2 caractères).",
)
def get_all_clients(
    q: Optional[str] = Query(None, description="Recherche par nom, prénom ou téléphone (min 2 car)"),
    genre: Optional[GenreClient] = Query(None, description="Filtrer par genre"),
    limit: int = Query(20, ge=1, le=100, description="Nombre d'éléments par page"),
    offset: int = Query(0, ge=0, description="Décalage pour la pagination"),
    db: Session = Depends(get_db),
) -> ClientPagination:
    """Liste paginée des clients."""
    items, total = list_clients(
        db=db,
        q=q,
        genre=genre,
        limit=limit,
        offset=offset,
    )
    return ClientPagination(
        items=[ClientRead.model_validate(c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{id}",
    response_model=ClientRead,
    summary="Fiche détaillée d'un client (Tous rôles)",
    description="Récupère la fiche complète d'un client par son identifiant.",
)
def get_client_detail(
    id: int,
    db: Session = Depends(get_db),
) -> Client:
    """Renvoie la fiche client ou 404 si inconnu."""
    client = get_client_by_id(db=db, client_id=id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun client trouvé avec l'identifiant {id}.",
        )
    return client


@router.patch(
    "/{id}",
    response_model=ClientRead,
    summary="Modifier un client (Tous rôles)",
    description="Modification partielle. nom, prénom et téléphone ne peuvent pas être vidés (422).",
)
def patch_client(
    id: int,
    client_in: ClientUpdate,
    db: Session = Depends(get_db),
) -> Client:
    """Met à jour un client existant."""
    client_db = get_client_by_id(db=db, client_id=id)
    if client_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun client trouvé avec l'identifiant {id}.",
        )
    return update_client(db=db, client_db=client_db, client_in=client_in)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un client (Admin uniquement)",
    description="Supprime un client s'il n'a pas de commandes (RG4). Supprime aussi ses mesures.",
    dependencies=[Depends(require_admin)],
)
def delete_client_by_id(
    id: int,
    db: Session = Depends(get_db),
) -> None:
    """Supprime un client si aucune commande n'existe pour lui (RG4)."""
    client = get_client_by_id(db=db, client_id=id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun client trouvé avec l'identifiant {id}.",
        )
    delete_client(db=db, client=client)


@router.get(
    "/{id}/resume",
    response_model=ClientResume,
    summary="Résumé d'activité du client (Tous rôles)",
    description="Renvoie le nombre de commandes, le CA, le montant payé, le solde dû et la présence de mesures.",
)
def get_client_summary(
    id: int,
    db: Session = Depends(get_db),
) -> ClientResume:
    """Calcule le résumé financier et de production du client."""
    client = get_client_by_id(db=db, client_id=id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun client trouvé avec l'identifiant {id}.",
        )
    return get_client_resume(db=db, client=client)


@router.get(
    "/{id}/commandes",
    summary="Commandes du client (Tous rôles)",
    description="Renvoie les commandes du client, paginées, la plus récente d'abord.",
)
def get_client_commandes(
    id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    """Récupère les commandes associées à un client."""
    client = get_client_by_id(db=db, client_id=id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun client trouvé avec l'identifiant {id}.",
        )
    # Si le modèle Commande est présent
    try:
        from app.models.commande import Commande
        from sqlalchemy import select
        stmt = (
            select(Commande)
            .where(Commande.client_id == id)
            .order_by(Commande.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        commandes = db.execute(stmt).scalars().all()
        return {
            "items": [c.id for c in commandes],
            "total": len(commandes),
            "limit": limit,
            "offset": offset,
        }
    except ImportError:
        return {"items": [], "total": 0, "limit": limit, "offset": offset}
