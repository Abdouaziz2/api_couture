from datetime import date
from typing import List, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user, require_accueil
from app.models.commande import Commande, StatutCommande
from app.models.paiement import Paiement
from app.models.utilisateur import Utilisateur
from app.schemas.commande import (
    ChangementStatutRequest,
    CommandeCreate,
    CommandePagination,
    CommandeRead,
    CommandeUpdate,
    HistoriqueStatutRead,
    LigneCommandeCreate,
)
from app.schemas.paiement import PaiementCreate, PaiementRead
from app.services.commande import (
    add_ligne_commande,
    changer_statut_commande,
    create_commande,
    delete_ligne_commande,
    format_commande_list_item,
    format_commande_read,
    get_commande_by_id,
    list_commandes,
    update_commande,
)
from app.services.paiement import (
    create_paiement,
    list_paiements_commande,
)

router = APIRouter(
    prefix="/commandes",
    tags=["Commandes"],
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "",
    response_model=CommandeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une commande (Accueil)",
    description="Enregistre une commande avec ses lignes. Calcule le numéro (RG5), les montants (RG7), les délais (RG8) et rattache les mesures (RG9).",
    dependencies=[Depends(require_accueil)],
)
def create_new_order(
    cmd_in: CommandeCreate,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommandeRead:
    """Crée une nouvelle commande en statut en_attente."""
    cmd = create_commande(db=db, cmd_in=cmd_in, current_user=current_user)
    return format_commande_read(cmd)


@router.get(
    "",
    response_model=CommandePagination,
    summary="Lister les commandes avec filtres et pagination (Tous rôles)",
    description="Renvoie la liste paginée des commandes triée par date décroissante. Permet de filtrer par statut, client, retard, date ou numéro.",
)
def get_all_orders(
    statut: Optional[StatutCommande] = Query(None, description="Filtrer par statut"),
    client_id: Optional[int] = Query(None, description="Filtrer par client"),
    en_retard: Optional[bool] = Query(None, description="Filtrer les commandes en retard"),
    date_min: Optional[date] = Query(None, description="Date de commande minimale"),
    date_max: Optional[date] = Query(None, description="Date de commande maximale"),
    numero: Optional[str] = Query(None, description="Recherche par numéro de commande"),
    limit: int = Query(20, ge=1, le=100, description="Nombre d'éléments"),
    offset: int = Query(0, ge=0, description="Décalage pour la pagination"),
    db: Session = Depends(get_db),
) -> CommandePagination:
    """Liste paginée des commandes avec indicateurs solde et retard."""
    items, total = list_commandes(
        db=db,
        statut=statut,
        client_id=client_id,
        en_retard=en_retard,
        date_min=date_min,
        date_max=date_max,
        numero=numero,
        limit=limit,
        offset=offset,
    )
    return CommandePagination(
        items=[format_commande_list_item(cmd) for cmd in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{id}",
    response_model=CommandeRead,
    summary="Détail complet d'une commande (Tous rôles)",
    description="Récupère une commande avec ses lignes (nom de prestation, sous-total), son historique, ses montants et solde.",
)
def get_order_detail(
    id: int,
    db: Session = Depends(get_db),
) -> CommandeRead:
    """Détail complet de la commande."""
    cmd = get_commande_by_id(db=db, commande_id=id)
    if cmd is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune commande trouvée avec l'identifiant {id}.",
        )
    return format_commande_read(cmd)


@router.patch(
    "/{id}",
    response_model=CommandeRead,
    summary="Modifier une commande (Accueil)",
    description="Modifie mesure_id, date_livraison_prevue, remise, notes et recalcule les montants. 409 si livrée ou annulée.",
    dependencies=[Depends(require_accueil)],
)
def patch_order(
    id: int,
    cmd_in: CommandeUpdate,
    db: Session = Depends(get_db),
) -> CommandeRead:
    """Mise à jour partielle d'une commande."""
    cmd = get_commande_by_id(db=db, commande_id=id)
    if cmd is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune commande trouvée avec l'identifiant {id}.",
        )
    cmd_updated = update_commande(db=db, commande=cmd, cmd_in=cmd_in)
    return format_commande_read(cmd_updated)


@router.post(
    "/{id}/statut",
    response_model=CommandeRead,
    summary="Faire évoluer le statut d'une commande (Tous rôles avec restrictions)",
    description="Fait évoluer le statut selon la matrice du workflow. Applique les contrôles RG13, RG14 et enregistre l'historique RG15.",
)
def update_order_status(
    id: int,
    body: ChangementStatutRequest,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommandeRead:
    """Transition de statut avec traçabilité complète."""
    cmd = get_commande_by_id(db=db, commande_id=id)
    if cmd is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune commande trouvée avec l'identifiant {id}.",
        )
    cmd_updated = changer_statut_commande(
        db=db,
        commande=cmd,
        nouveau_statut=body.statut,
        commentaire=body.commentaire,
        current_user=current_user,
    )
    return format_commande_read(cmd_updated)


@router.get(
    "/{id}/historique",
    response_model=List[HistoriqueStatutRead],
    summary="Historique des changements de statut (Tous rôles)",
    description="Renvoie la liste chronologique complète de tous les changements de statut de la commande (RG15).",
)
def get_order_history(
    id: int,
    db: Session = Depends(get_db),
) -> List[HistoriqueStatutRead]:
    """Historique chronologique des statuts."""
    cmd = get_commande_by_id(db=db, commande_id=id)
    if cmd is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune commande trouvée avec l'identifiant {id}.",
        )
    return [
        HistoriqueStatutRead(
            id=h.id,
            ancien_statut=h.ancien_statut,
            nouveau_statut=h.nouveau_statut,
            commentaire=h.commentaire,
            utilisateur_id=h.utilisateur_id,
            date_changement=h.date_changement,
        )
        for h in cmd.historique
    ]


@router.post(
    "/{id}/lignes",
    response_model=CommandeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une ligne de commande (Accueil)",
    description="Ajoute une prestation à une commande en attente et recalcule les montants (RG10).",
    dependencies=[Depends(require_accueil)],
)
def add_line(
    id: int,
    ligne_in: LigneCommandeCreate,
    db: Session = Depends(get_db),
) -> CommandeRead:
    """Ajout d'une prestation à une commande."""
    cmd = get_commande_by_id(db=db, commande_id=id)
    if cmd is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune commande trouvée avec l'identifiant {id}.",
        )
    cmd_updated = add_ligne_commande(db=db, commande=cmd, ligne_in=ligne_in)
    return format_commande_read(cmd_updated)


@router.delete(
    "/{id}/lignes/{ligne_id}",
    response_model=CommandeRead,
    summary="Retirer une ligne de commande (Accueil)",
    description="Supprime une prestation d'une commande en attente (garde au moins une ligne - RG10).",
    dependencies=[Depends(require_accueil)],
)
def remove_line(
    id: int,
    ligne_id: int,
    db: Session = Depends(get_db),
) -> CommandeRead:
    """Retrait d'une prestation d'une commande."""
    cmd = get_commande_by_id(db=db, commande_id=id)
    if cmd is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune commande trouvée avec l'identifiant {id}.",
        )
    cmd_updated = delete_ligne_commande(db=db, commande=cmd, ligne_id=ligne_id)
    return format_commande_read(cmd_updated)


# --- Routes des Paiements associées à la commande (Routes 32 & 33) ---

@router.post(
    "/{id}/paiements",
    response_model=PaiementRead,
    status_code=status.HTTP_201_CREATED,
    summary="Encaisser un acompte ou le solde (Accueil)",
    description="Enregistre un paiement sur la commande. Applique les contrôles RG16 (montant <= solde, pas de date future, commande non annulée).",
    dependencies=[Depends(require_accueil)],
)
def pay_order(
    id: int,
    paiement_in: PaiementCreate,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Paiement:
    """Encaissement d'un règlement sur la commande."""
    return create_paiement(
        db=db,
        commande_id=id,
        paiement_in=paiement_in,
        current_user=current_user,
    )


@router.get(
    "/{id}/paiements",
    response_model=List[PaiementRead],
    summary="Lister les paiements d'une commande (Tous rôles)",
    description="Renvoie l'ensemble des paiements de la commande dans leur ordre chronologique de saisie (Route 33).",
)
def get_order_payments(
    id: int,
    db: Session = Depends(get_db),
) -> Sequence[Paiement]:
    """Historique des paiements d'une commande."""
    return list_paiements_commande(db=db, commande_id=id)
