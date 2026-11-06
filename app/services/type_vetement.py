from typing import Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.type_vetement import TypeVetement
from app.schemas.type_vetement import TypeVetementCreate, TypeVetementUpdate


def get_type_vetement_by_id(db: Session, item_id: int) -> Optional[TypeVetement]:
    """Récupère une prestation du catalogue par son identifiant unique."""
    return db.get(TypeVetement, item_id)


def get_type_vetement_by_nom(db: Session, nom: str) -> Optional[TypeVetement]:
    """Recherche une prestation par son nom exact (insensible à la casse)."""
    stmt = select(TypeVetement).where(func.lower(TypeVetement.nom) == nom.strip().lower())
    return db.execute(stmt).scalar_one_or_none()


def list_types_vetement(
    db: Session,
    actifs_seulement: bool = True,
) -> Sequence[TypeVetement]:
    """
    Renvoie la liste des prestations du catalogue, triée par nom (Route 15).
    Par défaut, filtre sur les prestations actives (actif=True) sauf si actifs_seulement=False.
    """
    stmt = select(TypeVetement)
    if actifs_seulement:
        stmt = stmt.where(TypeVetement.actif.is_(True))
    stmt = stmt.order_by(TypeVetement.nom.asc())
    return db.execute(stmt).scalars().all()


def create_type_vetement(
    db: Session,
    item_in: TypeVetementCreate,
) -> TypeVetement:
    """
    Ajoute une prestation au catalogue (Route 14 - Admin).
    Renvoie 409 si une prestation avec le même nom existe déjà.
    """
    nom_clean = item_in.nom.strip()
    existant = get_type_vetement_by_nom(db, nom_clean)
    if existant is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Une prestation avec le nom '{nom_clean}' existe déjà dans le catalogue.",
        )

    nouvel_article = TypeVetement(
        nom=nom_clean,
        description=item_in.description.strip() if item_in.description else None,
        prix_base=item_in.prix_base,
        delai_jours=item_in.delai_jours,
        actif=True,
    )
    db.add(nouvel_article)
    db.commit()
    db.refresh(nouvel_article)
    return nouvel_article


def update_type_vetement(
    db: Session,
    item_db: TypeVetement,
    item_in: TypeVetementUpdate,
) -> TypeVetement:
    """
    Modifie prix, délai, nom ou état actif d'une prestation (Route 17 - Admin).
    Si le nom est modifié, vérifie qu'aucun autre article ne le possède déjà (409 si doublon).
    """
    if item_in.nom is not None:
        nom_clean = item_in.nom.strip()
        if nom_clean.lower() != item_db.nom.lower():
            autre = get_type_vetement_by_nom(db, nom_clean)
            if autre is not None and autre.id != item_db.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Une prestation avec le nom '{nom_clean}' existe déjà dans le catalogue.",
                )
            item_db.nom = nom_clean

    if item_in.description is not None:
        item_db.description = item_in.description.strip() if item_in.description else None

    if item_in.prix_base is not None:
        item_db.prix_base = item_in.prix_base

    if item_in.delai_jours is not None:
        item_db.delai_jours = item_in.delai_jours

    if item_in.actif is not None:
        item_db.actif = item_in.actif

    db.commit()
    db.refresh(item_db)
    return item_db
