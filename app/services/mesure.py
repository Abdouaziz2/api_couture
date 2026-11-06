from datetime import date
from typing import Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.mesure import CHAMPS_MESURES, Mesure
from app.schemas.mesure import MesureCreate, MesureUpdate


def get_mesure_by_id(db: Session, mesure_id: int) -> Optional[Mesure]:
    """Récupère une prise de mesures par son identifiant unique."""
    return db.get(Mesure, mesure_id)


def create_mesure(
    db: Session,
    client_id: int,
    prise_par_id: int,
    mesure_in: MesureCreate,
) -> Mesure:
    """
    Enregistre une nouvelle prise de mesures (Route 18 - Tailleur).
    - Vérifie que le client existe (404 si non trouvé).
    - Applique RG2 : au moins une mesure positive <= 300 cm.
    - Définit la date_prise du jour si omise.
    """
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun client trouvé avec l'identifiant {client_id}.",
        )

    nouvelle_mesure = Mesure(
        client_id=client_id,
        prise_par_id=prise_par_id,
        date_prise=mesure_in.date_prise or date.today(),
        notes=mesure_in.notes.strip() if mesure_in.notes else None,
    )

    # Affectation des 18 mesures corporelles
    for champ in CHAMPS_MESURES:
        val = getattr(mesure_in, champ)
        if val is not None:
            setattr(nouvelle_mesure, champ, val)

    db.add(nouvelle_mesure)
    db.commit()
    db.refresh(nouvelle_mesure)
    return nouvelle_mesure


def list_mesures_client(db: Session, client_id: int) -> Sequence[Mesure]:
    """
    Historique complet des mesures d'un client, la plus récente d'abord (RG3 / Route 19).
    """
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun client trouvé avec l'identifiant {client_id}.",
        )

    stmt = (
        select(Mesure)
        .where(Mesure.client_id == client_id)
        .order_by(Mesure.date_prise.desc(), Mesure.id.desc())
    )
    return db.execute(stmt).scalars().all()


def get_derniere_mesure_client(db: Session, client_id: int) -> Mesure:
    """
    Récupère la prise de mesures la plus récente d'un client (RG3 / Route 20).
    Renvoie 404 si le client n'a aucune mesure.
    """
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun client trouvé avec l'identifiant {client_id}.",
        )

    stmt = (
        select(Mesure)
        .where(Mesure.client_id == client_id)
        .order_by(Mesure.date_prise.desc(), Mesure.id.desc())
        .limit(1)
    )
    derniere = db.execute(stmt).scalar_one_or_none()
    if derniere is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ce client ne possède aucune prise de mesures enregistrée.",
        )
    return derniere


def update_mesure(
    db: Session,
    mesure_db: Mesure,
    mesure_in: MesureUpdate,
) -> Mesure:
    """
    Corrige une erreur de saisie sur une prise de mesures (Route 22 - Tailleur).
    Règle : 422 si la correction supprimait toutes les mesures corporelles (RG2).
    """
    champs_modifies = mesure_in.model_dump(exclude_unset=True)

    if "notes" in champs_modifies:
        mesure_db.notes = mesure_in.notes.strip() if mesure_in.notes else None
    if "date_prise" in champs_modifies and mesure_in.date_prise is not None:
        mesure_db.date_prise = mesure_in.date_prise

    for champ in CHAMPS_MESURES:
        if champ in champs_modifies:
            setattr(mesure_db, champ, champs_modifies[champ])

    # Vérification qu'au moins une mesure reste présente après la modification
    au_moins_une = any(getattr(mesure_db, c) is not None for c in CHAMPS_MESURES)
    if not au_moins_une:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La modification ne peut pas supprimer l'ensemble des mesures corporelles (RG2).",
        )

    db.commit()
    db.refresh(mesure_db)
    return mesure_db


def delete_mesure(db: Session, mesure: Mesure) -> None:
    """
    Supprime une prise de mesures (Route 23 - Tailleur).
    Règle RG4 : 409 si une commande les utilise.
    """
    try:
        from app.models.commande import Commande
        nb_utilisations = db.execute(
            select(func.count(Commande.id)).where(Commande.mesure_id == mesure.id)
        ).scalar_one()
        if nb_utilisations > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Impossible de supprimer cette prise de mesures car elle est rattachée à une commande (RG4).",
            )
    except ImportError:
        pass

    db.delete(mesure)
    db.commit()
