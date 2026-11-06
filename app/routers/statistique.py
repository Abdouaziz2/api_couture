from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.schemas.statistique import (
    ChiffreAffairesPoint,
    ImpayeItem,
    StatTypeVetement,
    TableauDeBord,
    TopClientItem,
)
from app.services.statistique import (
    get_chiffre_affaires_evolution,
    get_impayes,
    get_stats_types_vetement,
    get_tableau_de_bord,
    get_top_clients,
)

router = APIRouter(
    prefix="/statistiques",
    tags=["Statistiques"],
    dependencies=[Depends(get_current_user), Depends(require_admin)],
)


@router.get(
    "/tableau-de-bord",
    response_model=TableauDeBord,
    summary="Tableau de bord global de l'atelier (Admin)",
    description="Indicateurs clés d'activité : CA du mois, encaissements, commandes par statut, impayés et alertes retards (Route 39).",
)
def read_dashboard(
    db: Session = Depends(get_db),
) -> TableauDeBord:
    """Tableau de bord de pilotage d'activité."""
    return get_tableau_de_bord(db=db)


@router.get(
    "/chiffre-affaires",
    response_model=List[ChiffreAffairesPoint],
    summary="Chiffre d'affaires par période (Admin)",
    description="Évolution du chiffre d'affaires et des montants encaissés, groupés par mois ou par jour (Route 40).",
)
def read_revenue_stats(
    periode: str = Query("mois", pattern="^(jour|mois)$", description="Granularité temporelle ('jour' ou 'mois')"),
    date_debut: Optional[date] = Query(None, description="Date de début (inclus)"),
    date_fin: Optional[date] = Query(None, description="Date de fin (inclus)"),
    db: Session = Depends(get_db),
) -> List[ChiffreAffairesPoint]:
    """Évolution chronologique du CA et encaissements."""
    return get_chiffre_affaires_evolution(
        db=db,
        periode=periode,
        date_debut=date_debut,
        date_fin=date_fin,
    )


@router.get(
    "/types-vetement",
    response_model=List[StatTypeVetement],
    summary="Statistiques par type de vêtement (Admin)",
    description="Palmarès des confections du catalogue : volumes confectionnés et chiffre d'affaires associé (Route 41).",
)
def read_clothing_types_stats(
    db: Session = Depends(get_db),
) -> List[StatTypeVetement]:
    """Performance des types de vêtements du catalogue."""
    return get_stats_types_vetement(db=db)


@router.get(
    "/top-clients",
    response_model=List[TopClientItem],
    summary="Meilleurs clients de l'atelier (Admin)",
    description="Liste des clients ayant généré le plus fort volume d'affaires (Route 42).",
)
def read_top_clients(
    limite: int = Query(10, ge=1, le=100, description="Nombre maximum de clients à renvoyer"),
    db: Session = Depends(get_db),
) -> List[TopClientItem]:
    """Classement des clients les plus contributeurs."""
    return get_top_clients(db=db, limite=limite)


@router.get(
    "/impayes",
    response_model=List[ImpayeItem],
    summary="Gestion des créances et impayés (Admin)",
    description="Liste l'ensemble des commandes non soldées avec solde débiteur, triées par ordre d'urgence de livraison (Route 43).",
)
def read_unpaid_orders(
    db: Session = Depends(get_db),
) -> List[ImpayeItem]:
    """Liste de relance des créances clients."""
    return get_impayes(db=db)
