from datetime import date
from typing import Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.commande import Commande, StatutCommande
from app.models.paiement import Paiement
from app.models.utilisateur import Utilisateur
from app.schemas.paiement import PaiementCreate


def get_paiement_by_id(db: Session, paiement_id: int) -> Optional[Paiement]:
    """Récupère un paiement par son identifiant unique."""
    return db.get(Paiement, paiement_id)


def create_paiement(
    db: Session,
    commande_id: int,
    paiement_in: PaiementCreate,
    current_user: Utilisateur,
) -> Paiement:
    """
    Enregistre un paiement (acompte ou solde) sur une commande (Route 32).
    Applique rigoureusement la règle RG16 :
    - Strictement positif (> 0, garanti par Pydantic).
    - Refusé sur une commande annulée (409).
    - Date future interdite (422).
    - Ne peut pas dépasser le solde restant (409).
    """
    commande = db.get(Commande, commande_id)
    if commande is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune commande trouvée avec l'identifiant {commande_id}.",
        )

    # RG16 : refus sur commande annulée
    if commande.statut == StatutCommande.ANNULEE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible d'enregistrer un paiement sur une commande annulée (RG16).",
        )

    # RG16 : date future interdite
    date_reglement = paiement_in.date_paiement or date.today()
    if date_reglement > date.today():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La date de paiement ne peut pas être fixée dans le futur (RG16).",
        )

    # RG16 : ne peut pas dépasser le solde restant
    solde_restant = commande.solde
    if paiement_in.montant > solde_restant:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Le montant saisi ({paiement_in.montant} FCFA) dépasse le solde "
                f"restant de la commande ({solde_restant} FCFA) (RG16)."
            ),
        )

    nouveau_paiement = Paiement(
        commande_id=commande.id,
        montant=paiement_in.montant,
        mode=paiement_in.mode,
        reference=paiement_in.reference.strip() if paiement_in.reference else None,
        date_paiement=date_reglement,
        enregistre_par_id=current_user.id,
    )
    # Recalcul du montant payé
    commande.montant_paye += paiement_in.montant

    db.add(nouveau_paiement)
    db.commit()
    db.refresh(nouveau_paiement)
    db.refresh(commande)
    return nouveau_paiement


def list_paiements_commande(db: Session, commande_id: int) -> Sequence[Paiement]:
    """
    Renvoie tous les paiements d'une commande dans l'ordre de saisie (Route 33).
    """
    commande = db.get(Commande, commande_id)
    if commande is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune commande trouvée avec l'identifiant {commande_id}.",
        )

    stmt = (
        select(Paiement)
        .where(Paiement.commande_id == commande_id)
        .order_by(Paiement.id.asc())
    )
    return db.execute(stmt).scalars().all()


def delete_paiement(db: Session, paiement: Paiement) -> None:
    """
    Annule un paiement saisi par erreur (Route 34 - Admin).
    Applique la règle RG17 : recalcule automatiquement le montant payé et le solde.
    """
    commande = db.get(Commande, paiement.commande_id)
    if commande:
        commande.montant_paye = max(0, commande.montant_paye - paiement.montant)

    db.delete(paiement)
    db.commit()
    if commande:
        db.refresh(commande)
