from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.livraison import StatutLivraison
from app.schemas.livraison import LivraisonTourneeItem
from app.services.livraison import lister_livraisons_tournee

router = APIRouter(
    prefix="/livraisons",
    tags=["Livraisons"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "",
    response_model=List[LivraisonTourneeItem],
    summary="Tournée et planning des livraisons (Tous rôles)",
    description="Liste les livraisons prévues ou effectuées, ordonnées par date prévue croissante. Filtres par statut, date minimale et maximale (Route 38).",
)
def list_deliveries(
    statut: Optional[StatutLivraison] = Query(
        None,
        description="Filtrer par statut de livraison (planifiee, livree)",
    ),
    date_min: Optional[date] = Query(
        None,
        description="Date minimale prévue (inclus)",
    ),
    date_max: Optional[date] = Query(
        None,
        description="Date maximale prévue (inclus)",
    ),
    db: Session = Depends(get_db),
) -> List[LivraisonTourneeItem]:
    """Tournée / planning chronologique des livraisons."""
    return lister_livraisons_tournee(
        db=db,
        statut=statut,
        date_min=date_min,
        date_max=date_max,
    )
