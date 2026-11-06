from datetime import date
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.client import Client
from app.models.commande import Commande, HistoriqueStatut, StatutCommande
from app.models.livraison import Livraison, ModeLivraison, StatutLivraison
from app.models.utilisateur import Utilisateur
from app.schemas.livraison import (
    LivraisonConfirmation,
    LivraisonPlanification,
    LivraisonTourneeItem,
)


def planifier_ou_replanifier_livraison(
    db: Session,
    commande_id: int,
    data: LivraisonPlanification,
) -> Livraison:
    """Planifie ou replanifie la livraison d'une commande (Route 35).

    Règles appliquées :
    - RG18: Une livraison peut être planifiée dès qu'une commande est créée,
      sauf si elle est déjà livrée ou annulée (409).
    - RG18: En mode 'domicile', l'adresse est obligatoire (422 géré par Pydantic).
    - RG18: Planifier ou replanifier met à jour commande.date_livraison_prevue.
    """
    commande = db.get(Commande, commande_id)
    if not commande:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commande {commande_id} introuvable.",
        )

    if commande.statut in (StatutCommande.LIVREE, StatutCommande.ANNULEE):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Impossible de planifier ou replanifier la livraison d'une commande "
                f"au statut '{commande.statut.value}' (RG18)."
            ),
        )

    # Mise à jour cohérente de la date de livraison prévue sur la commande (RG18)
    commande.date_livraison_prevue = data.date_prevue

    # Recherche d'une livraison existante (replanification)
    stmt = select(Livraison).where(Livraison.commande_id == commande_id)
    livraison = db.execute(stmt).scalar_one_or_none()

    if livraison:
        livraison.mode = data.mode
        livraison.date_prevue = data.date_prevue
        livraison.adresse = data.adresse
        livraison.livreur = data.livreur
        livraison.notes = data.notes
        # Si la livraison n'est pas encore livrée, son statut reste planifiee
        livraison.statut = StatutLivraison.PLANIFIEE
    else:
        livraison = Livraison(
            commande_id=commande_id,
            mode=data.mode,
            date_prevue=data.date_prevue,
            adresse=data.adresse,
            livreur=data.livreur,
            notes=data.notes,
            statut=StatutLivraison.PLANIFIEE,
        )
        db.add(livraison)

    db.commit()
    db.refresh(livraison)
    return livraison


def get_livraison_commande(db: Session, commande_id: int) -> Livraison:
    """Récupère les informations de livraison d'une commande (Route 36)."""
    commande = db.get(Commande, commande_id)
    if not commande:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commande {commande_id} introuvable.",
        )

    stmt = select(Livraison).where(Livraison.commande_id == commande_id)
    livraison = db.execute(stmt).scalar_one_or_none()
    if not livraison:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune livraison planifiée pour la commande {commande.numero}.",
        )

    return livraison


def confirmer_livraison(
    db: Session,
    commande_id: int,
    data: LivraisonConfirmation,
    current_user: Utilisateur,
) -> Livraison:
    """Confirme la livraison d'une commande (Route 37).

    Règles appliquées :
    - RG19: Une commande ne peut être livrée que si son statut est 'terminee' (409).
    - RG19: Si le solde n'est pas nul, refus 409 avec solde restant dû, sauf si autoriser_solde_impaye=true.
    - RG20: Passe la commande au statut 'livree' et la livraison au statut 'livree'.
    - RG20: Si aucune livraison n'avait été planifiée, création automatique en 'retrait_atelier'.
    - RG20: date_effective enregistrée au moment de la confirmation.
    - RG15: Tracé dans l'historique des statuts.
    """
    commande = db.get(Commande, commande_id)
    if not commande:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commande {commande_id} introuvable.",
        )

    # RG19: Vérification du statut préalable
    if commande.statut != StatutCommande.TERMINEE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Une commande ne peut être livrée que si son statut est 'terminee'. "
                f"Statut actuel : '{commande.statut.value}' (RG19)."
            ),
        )

    # RG19: Vérification du solde restant dû
    if commande.solde > 0 and not data.autoriser_solde_impaye:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Impossible de livrer la commande {commande.numero} : un solde de {commande.solde} FCFA "
                f"reste impayé. Veuillez encaisser le solde ou cocher 'autoriser_solde_impaye' (RG19)."
            ),
        )

    date_effective_val = data.date_effective or date.today()

    stmt = select(Livraison).where(Livraison.commande_id == commande_id)
    livraison = db.execute(stmt).scalar_one_or_none()

    # RG20: Création automatique si aucune livraison planifiée au préalable
    if not livraison:
        livraison = Livraison(
            commande_id=commande_id,
            mode=ModeLivraison.RETRAIT_ATELIER,
            date_prevue=date_effective_val,
            date_effective=date_effective_val,
            statut=StatutLivraison.LIVREE,
            notes="Retrait atelier direct sans planification préalable.",
        )
        db.add(livraison)
    else:
        livraison.statut = StatutLivraison.LIVREE
        livraison.date_effective = date_effective_val

    # Mise à jour de la commande
    ancien_statut = commande.statut
    commande.statut = StatutCommande.LIVREE
    commande.date_livraison_reelle = date_effective_val

    # Enregistrement dans l'historique des statuts (RG15)
    commentaire = "Livraison confirmée"
    if commande.solde > 0 and data.autoriser_solde_impaye:
        commentaire += f" avec dérogation : solde restant de {commande.solde} FCFA impayé."

    historique_entry = HistoriqueStatut(
        commande_id=commande.id,
        ancien_statut=ancien_statut,
        nouveau_statut=StatutCommande.LIVREE,
        commentaire=commentaire,
        utilisateur_id=current_user.id,
    )
    db.add(historique_entry)

    db.commit()
    db.refresh(livraison)
    return livraison


def lister_livraisons_tournee(
    db: Session,
    statut: Optional[StatutLivraison] = None,
    date_min: Optional[date] = None,
    date_max: Optional[date] = None,
) -> List[LivraisonTourneeItem]:
    """Liste les livraisons pour le planning ou la tournée (Route 38).

    Triées chronologiquement par date_prevue croissante.
    """
    stmt = (
        select(Livraison)
        .options(
            joinedload(Livraison.commande).joinedload(Commande.client)
        )
        .order_by(Livraison.date_prevue.asc(), Livraison.id.asc())
    )

    if statut:
        stmt = stmt.where(Livraison.statut == statut)
    if date_min:
        stmt = stmt.where(Livraison.date_prevue >= date_min)
    if date_max:
        stmt = stmt.where(Livraison.date_prevue <= date_max)

    livraisons = db.execute(stmt).scalars().all()

    result: List[LivraisonTourneeItem] = []
    for liv in livraisons:
        cmd = liv.commande
        cli = cmd.client if cmd else None
        client_nom = f"{cli.prenom} {cli.nom}".strip() if cli else "Client inconnu"
        client_tel = cli.telephone if cli else ""
        solde_val = cmd.solde if cmd else 0
        cmd_num = cmd.numero if cmd else ""

        result.append(
            LivraisonTourneeItem(
                id=liv.id,
                commande_id=liv.commande_id,
                numero_commande=cmd_num,
                client_nom=client_nom,
                client_telephone=client_tel,
                solde_commande=solde_val,
                mode=liv.mode,
                adresse=liv.adresse,
                livreur=liv.livreur,
                date_prevue=liv.date_prevue,
                date_effective=liv.date_effective,
                statut=liv.statut,
                notes=liv.notes,
            )
        )

    return result
