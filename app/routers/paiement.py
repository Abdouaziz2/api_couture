from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.services.paiement import delete_paiement, get_paiement_by_id

router = APIRouter(
    prefix="/paiements",
    tags=["Paiements"],
    dependencies=[Depends(get_current_user)],
)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Annuler un paiement saisi par erreur (Admin)",
    description="Supprime un paiement et recalcule immédiatement le montant payé et le solde de la commande (RG17).",
    dependencies=[Depends(require_admin)],
)
def cancel_payment(
    id: int,
    db: Session = Depends(get_db),
) -> None:
    """Annulation administrative d'un paiement."""
    paiement = get_paiement_by_id(db=db, paiement_id=id)
    if paiement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun paiement trouvé avec l'identifiant {id}.",
        )
    delete_paiement(db=db, paiement=paiement)
