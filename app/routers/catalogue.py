from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.models.type_vetement import TypeVetement
from app.schemas.type_vetement import (
    TypeVetementCreate,
    TypeVetementRead,
    TypeVetementUpdate,
)
from app.services.type_vetement import (
    create_type_vetement,
    get_type_vetement_by_id,
    list_types_vetement,
    update_type_vetement,
)

router = APIRouter(
    prefix="/catalogue",
    tags=["Catalogue"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "",
    response_model=TypeVetementRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une prestation au catalogue (Admin)",
    description="Permet à l'administrateur d'ajouter un modèle ou une prestation au catalogue.",
    dependencies=[Depends(require_admin)],
)
def add_catalogue_item(
    item_in: TypeVetementCreate,
    db: Session = Depends(get_db),
) -> TypeVetement:
    """Ajoute une prestation. Renvoie 201 en cas de succès, 409 si le nom existe déjà."""
    return create_type_vetement(db=db, item_in=item_in)


@router.get(
    "",
    response_model=list[TypeVetementRead],
    summary="Lister les prestations du catalogue (Tous rôles)",
    description="Renvoie la liste des prestations triée par nom. Seules les prestations actives sont renvoyées sauf si actifs_seulement=false.",
)
def get_catalogue(
    actifs_seulement: bool = Query(
        True,
        description="Filtrer uniquement sur les prestations actives (défaut: True)",
    ),
    db: Session = Depends(get_db),
) -> Sequence[TypeVetement]:
    """Liste complète des prestations du catalogue triée par nom."""
    return list_types_vetement(db=db, actifs_seulement=actifs_seulement)


@router.get(
    "/{id}",
    response_model=TypeVetementRead,
    summary="Détail d'une prestation (Tous rôles)",
    description="Récupère les informations détaillées d'une prestation par son identifiant.",
)
def get_catalogue_item(
    id: int,
    db: Session = Depends(get_db),
) -> TypeVetement:
    """Renvoie le détail d'une prestation ou 404 si inconnue."""
    item = get_type_vetement_by_id(db=db, item_id=id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune prestation trouvée avec l'identifiant {id}.",
        )
    return item


@router.patch(
    "/{id}",
    response_model=TypeVetementRead,
    summary="Modifier une prestation (Admin)",
    description="Modifie le prix de base, le délai, le nom ou l'état actif. Actif=false retire la prestation sans impacter les anciennes commandes.",
    dependencies=[Depends(require_admin)],
)
def patch_catalogue_item(
    id: int,
    item_in: TypeVetementUpdate,
    db: Session = Depends(get_db),
) -> TypeVetement:
    """Modifie une prestation existante du catalogue."""
    item_db = get_type_vetement_by_id(db=db, item_id=id)
    if item_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune prestation trouvée avec l'identifiant {id}.",
        )
    return update_type_vetement(db=db, item_db=item_db, item_in=item_in)
