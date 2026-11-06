from datetime import date, timedelta
from typing import Optional, Sequence, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.client import Client
from app.models.commande import (
    Commande,
    HistoriqueStatut,
    LigneCommande,
    StatutCommande,
    TRANSITIONS_AUTORISEES,
)
from app.models.mesure import Mesure
from app.models.type_vetement import TypeVetement
from app.models.utilisateur import RoleUtilisateur, Utilisateur
from app.schemas.commande import (
    CommandeCreate,
    CommandeListItem,
    CommandeRead,
    CommandeUpdate,
    HistoriqueStatutRead,
    LigneCommandeCreate,
    LigneCommandeRead,
)


def generer_numero_commande(db: Session, annee: int) -> str:
    """
    Génère un numéro unique au format CMD-AAAA-NNNNN (RG5).
    Exemple : CMD-2026-00001
    """
    prefixe = f"CMD-{annee}-"
    stmt = (
        select(Commande.numero)
        .where(Commande.numero.like(f"{prefixe}%"))
        .order_by(Commande.id.desc())
        .limit(1)
    )
    dernier_numero = db.execute(stmt).scalar_one_or_none()
    if dernier_numero:
        try:
            dernier_compteur = int(dernier_numero.split("-")[-1])
            prochain = dernier_compteur + 1
        except ValueError:
            prochain = 1
    else:
        prochain = 1

    return f"{prefixe}{prochain:05d}"


def get_commande_by_id(db: Session, commande_id: int) -> Optional[Commande]:
    """Récupère une commande avec ses lignes et son historique pré-chargés."""
    stmt = (
        select(Commande)
        .where(Commande.id == commande_id)
        .options(
            joinedload(Commande.client),
            joinedload(Commande.lignes).joinedload(LigneCommande.type_vetement),
            joinedload(Commande.historique),
        )
    )
    return db.execute(stmt).unique().scalar_one_or_none()


def recalculer_montants(commande: Commande, nouvelle_remise: Optional[int] = None) -> None:
    """
    Recalcule le montant total après remise et vérifie RG7.
    """
    remise = nouvelle_remise if nouvelle_remise is not None else commande.remise
    somme_prestations = sum(ligne.quantite * ligne.prix_unitaire for ligne in commande.lignes)

    if remise > somme_prestations:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La remise ne peut pas dépasser la somme des prestations (RG7).",
        )

    nouveau_total = somme_prestations - remise
    if nouveau_total < commande.montant_paye:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La modification ne peut pas ramener le total sous le montant déjà payé (RG7).",
        )

    commande.remise = remise
    commande.montant_total = nouveau_total


def create_commande(
    db: Session,
    cmd_in: CommandeCreate,
    current_user: Utilisateur,
) -> Commande:
    """
    Crée une nouvelle commande avec ses lignes et son premier enregistrement d'historique (Route 24).
    Applique les règles RG5, RG6, RG7, RG8, RG9, RG10, RG15.
    """
    # 1. Vérification du client
    client = db.get(Client, cmd_in.client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun client trouvé avec l'identifiant {cmd_in.client_id}.",
        )

    date_jour = date.today()

    # 2. Rattachement des mesures (RG9)
    mesure_id = cmd_in.mesure_id
    if mesure_id is not None:
        mesure = db.get(Mesure, mesure_id)
        if mesure is None or mesure.client_id != client.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Les mesures rattachées doivent appartenir au client de la commande (RG9).",
            )
    else:
        # Recherche automatique des dernières mesures du client
        derniere = (
            db.execute(
                select(Mesure)
                .where(Mesure.client_id == client.id)
                .order_by(Mesure.date_prise.desc(), Mesure.id.desc())
                .limit(1)
            )
            .scalar_one_or_none()
        )
        if derniere:
            mesure_id = derniere.id

    # 3. Vérification des lignes et du catalogue (RG6, RG8)
    delais_jours = []
    lignes_db = []
    somme_prestations = 0

    for ligne_in in cmd_in.lignes:
        tv = db.get(TypeVetement, ligne_in.type_vetement_id)
        if tv is None or not tv.actif:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"La prestation ID {ligne_in.type_vetement_id} est inactive ou introuvable (RG6).",
            )
        prix_u = ligne_in.prix_unitaire if ligne_in.prix_unitaire is not None else tv.prix_base
        delais_jours.append(tv.delai_jours)
        somme_prestations += ligne_in.quantite * prix_u

        ligne = LigneCommande(
            type_vetement_id=tv.id,
            description=ligne_in.description.strip() if ligne_in.description else None,
            quantite=ligne_in.quantite,
            prix_unitaire=prix_u,
        )
        lignes_db.append(ligne)

    # 4. Calculs financiers (RG7)
    if cmd_in.remise > somme_prestations:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La remise ne peut pas dépasser la somme des prestations (RG7).",
        )
    montant_total = somme_prestations - cmd_in.remise

    # 5. Date de livraison prévue (RG8)
    if cmd_in.date_livraison_prevue is not None:
        if cmd_in.date_livraison_prevue < date_jour:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La date de livraison prévue ne peut pas précéder la date de commande (RG8).",
            )
        date_livraison = cmd_in.date_livraison_prevue
    else:
        max_delai = max(delais_jours) if delais_jours else 7
        date_livraison = date_jour + timedelta(days=max_delai)

    # 6. Numérotation (RG5)
    numero = generer_numero_commande(db, date_jour.year)

    nouvelle_commande = Commande(
        numero=numero,
        client_id=client.id,
        mesure_id=mesure_id,
        statut=StatutCommande.EN_ATTENTE,
        date_commande=date_jour,
        date_livraison_prevue=date_livraison,
        remise=cmd_in.remise,
        montant_total=montant_total,
        montant_paye=0,
        notes=cmd_in.notes.strip() if cmd_in.notes else None,
        cree_par_id=current_user.id,
        lignes=lignes_db,
    )

    # 7. Historique initial (RG15)
    premier_historique = HistoriqueStatut(
        ancien_statut=None,
        nouveau_statut=StatutCommande.EN_ATTENTE.value,
        commentaire="Création de la commande",
        utilisateur_id=current_user.id,
    )
    nouvelle_commande.historique.append(premier_historique)

    db.add(nouvelle_commande)
    db.commit()
    db.refresh(nouvelle_commande)
    return nouvelle_commande


def list_commandes(
    db: Session,
    statut: Optional[StatutCommande] = None,
    client_id: Optional[int] = None,
    en_retard: Optional[bool] = None,
    date_min: Optional[date] = None,
    date_max: Optional[date] = None,
    numero: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[Sequence[Commande], int]:
    """
    Liste paginée des commandes avec filtres avancés (Route 25).
    """
    stmt = (
        select(Commande)
        .options(
            joinedload(Commande.client),
            joinedload(Commande.lignes).joinedload(LigneCommande.type_vetement),
        )
    )

    if statut is not None:
        stmt = stmt.where(Commande.statut == statut)

    if client_id is not None:
        stmt = stmt.where(Commande.client_id == client_id)

    if date_min is not None:
        stmt = stmt.where(Commande.date_commande >= date_min)

    if date_max is not None:
        stmt = stmt.where(Commande.date_commande <= date_max)

    if numero is not None:
        stmt = stmt.where(Commande.numero.ilike(f"%{numero.strip()}%"))

    if en_retard is True:
        stmt = stmt.where(
            Commande.statut.not_in([StatutCommande.LIVREE, StatutCommande.ANNULEE]),
            Commande.date_livraison_prevue < date.today(),
        )
    elif en_retard is False:
        stmt = stmt.where(
            or_(
                Commande.statut.in_([StatutCommande.LIVREE, StatutCommande.ANNULEE]),
                Commande.date_livraison_prevue >= date.today(),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()

    stmt = stmt.order_by(Commande.date_commande.desc(), Commande.id.desc()).limit(limit).offset(offset)
    items = db.execute(stmt).unique().scalars().all()
    return items, total


def update_commande(
    db: Session,
    commande: Commande,
    cmd_in: CommandeUpdate,
) -> Commande:
    """
    Modifie mesure_id, date_livraison_prevue, remise, notes et recalcule les montants (Route 27).
    Règles : 409 si livrée ou annulée (RG12).
    """
    if commande.statut in (StatutCommande.LIVREE, StatutCommande.ANNULEE):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une commande livrée ou annulée ne peut plus être modifiée (RG12).",
        )

    if cmd_in.mesure_id is not None:
        mesure = db.get(Mesure, cmd_in.mesure_id)
        if mesure is None or mesure.client_id != commande.client_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Les mesures rattachées doivent appartenir au client de la commande (RG9).",
            )
        commande.mesure_id = cmd_in.mesure_id

    if cmd_in.date_livraison_prevue is not None:
        if cmd_in.date_livraison_prevue < commande.date_commande:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La date de livraison prévue ne peut pas précéder la date de commande (RG8).",
            )
        commande.date_livraison_prevue = cmd_in.date_livraison_prevue

    if cmd_in.notes is not None:
        commande.notes = cmd_in.notes.strip() if cmd_in.notes else None

    if cmd_in.remise is not None:
        recalculer_montants(commande, nouvelle_remise=cmd_in.remise)

    db.commit()
    db.refresh(commande)
    return commande


def changer_statut_commande(
    db: Session,
    commande: Commande,
    nouveau_statut: StatutCommande,
    commentaire: Optional[str],
    current_user: Utilisateur,
) -> Commande:
    """
    Fait évoluer le statut d'une commande selon le workflow strict (Route 28).
    Applique les règles RG12, RG13, RG14, RG15.
    """
    ancien_statut = commande.statut

    # RG12 : livrée ou annulée non modifiable
    if ancien_statut in (StatutCommande.LIVREE, StatutCommande.ANNULEE):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La commande est en statut final '{ancien_statut.value}' et ne peut plus évoluer (RG12).",
        )

    # RG13 : statut identique refusé
    if nouveau_statut == ancien_statut:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La commande est déjà dans le statut '{ancien_statut.value}' (RG13).",
        )

    # RG13 : passage à livrée direct interdit
    if nouveau_statut == StatutCommande.LIVREE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Le statut 'livree' ne peut pas être posé par cette route. Il résulte de la confirmation de livraison (RG13).",
        )

    # Vérification de la matrice des transitions
    transitions_possibles = TRANSITIONS_AUTORISEES.get(ancien_statut, [])
    if nouveau_statut not in transitions_possibles:
        possibles_str = ", ".join(s.value for s in transitions_possibles) if transitions_possibles else "aucun"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transition interdite : {ancien_statut.value} → {nouveau_statut.value}. Statuts possibles : {possibles_str}.",
        )

    # RG14 : restrictions sur l'annulation
    if nouveau_statut == StatutCommande.ANNULEE:
        if current_user.role == RoleUtilisateur.TAILLEUR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Le tailleur ne peut pas annuler une commande (RG14).",
            )
        if commande.montant_paye > 0 and (not commentaire or not commentaire.strip()):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Annuler une commande qui a reçu un acompte exige un commentaire expliquant "
                    "le sort de l'argent : remboursement, avoir... (RG14)."
                ),
            )

    # Application du statut
    commande.statut = nouveau_statut

    # RG15 : Enregistrement dans l'historique
    historique_entry = HistoriqueStatut(
        commande_id=commande.id,
        ancien_statut=ancien_statut.value,
        nouveau_statut=nouveau_statut.value,
        commentaire=commentaire.strip() if commentaire else None,
        utilisateur_id=current_user.id,
    )
    commande.historique.append(historique_entry)

    db.commit()
    db.refresh(commande)
    return commande


def add_ligne_commande(
    db: Session,
    commande: Commande,
    ligne_in: LigneCommandeCreate,
) -> Commande:
    """
    Ajoute une prestation à une commande (Route 30).
    Règle RG10 : possible uniquement tant que la commande est 'en_attente'.
    """
    if commande.statut != StatutCommande.EN_ATTENTE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Les lignes d'une commande ne sont modifiables que tant qu'elle est 'en_attente' (RG10).",
        )

    tv = db.get(TypeVetement, ligne_in.type_vetement_id)
    if tv is None or not tv.actif:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La prestation ID {ligne_in.type_vetement_id} est inactive ou introuvable (RG6).",
        )

    prix_u = ligne_in.prix_unitaire if ligne_in.prix_unitaire is not None else tv.prix_base
    nouvelle_ligne = LigneCommande(
        commande_id=commande.id,
        type_vetement_id=tv.id,
        description=ligne_in.description.strip() if ligne_in.description else None,
        quantite=ligne_in.quantite,
        prix_unitaire=prix_u,
    )
    commande.lignes.append(nouvelle_ligne)
    recalculer_montants(commande)

    db.commit()
    db.refresh(commande)
    return commande


def delete_ligne_commande(
    db: Session,
    commande: Commande,
    ligne_id: int,
) -> Commande:
    """
    Retire une prestation d'une commande (Route 31).
    Règles RG10 : commande en attente, garde toujours au moins une ligne.
    """
    if commande.statut != StatutCommande.EN_ATTENTE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Les lignes d'une commande ne sont modifiables que tant qu'elle est 'en_attente' (RG10).",
        )

    if len(commande.lignes) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une commande doit toujours conserver au moins une ligne (RG10).",
        )

    ligne_a_supprimer = None
    for ligne in commande.lignes:
        if ligne.id == ligne_id:
            ligne_a_supprimer = ligne
            break

    if ligne_a_supprimer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune ligne de commande trouvée avec l'identifiant {ligne_id}.",
        )

    commande.lignes.remove(ligne_a_supprimer)
    db.delete(ligne_a_supprimer)
    recalculer_montants(commande)

    db.commit()
    db.refresh(commande)
    return commande


def format_commande_read(commande: Commande) -> CommandeRead:
    """Construit le schéma détaillé de lecture d'une commande."""
    client_nom = f"{commande.client.prenom} {commande.client.nom}" if commande.client else ""
    lignes_dto = [
        LigneCommandeRead(
            id=ligne.id,
            commande_id=ligne.commande_id,
            type_vetement_id=ligne.type_vetement_id,
            type_vetement_nom=ligne.type_vetement.nom if ligne.type_vetement else "",
            description=ligne.description,
            quantite=ligne.quantite,
            prix_unitaire=ligne.prix_unitaire,
            sous_total=ligne.sous_total,
        )
        for ligne in commande.lignes
    ]
    historique_dto = [
        HistoriqueStatutRead(
            id=h.id,
            ancien_statut=h.ancien_statut,
            nouveau_statut=h.nouveau_statut,
            commentaire=h.commentaire,
            utilisateur_id=h.utilisateur_id,
            date_changement=h.date_changement,
        )
        for h in commande.historique
    ]

    return CommandeRead(
        id=commande.id,
        numero=commande.numero,
        client_id=commande.client_id,
        client_nom=client_nom,
        mesure_id=commande.mesure_id,
        statut=commande.statut,
        date_commande=commande.date_commande,
        date_livraison_prevue=commande.date_livraison_prevue,
        date_livraison_reelle=commande.date_livraison_reelle,
        remise=commande.remise,
        montant_total=commande.montant_total,
        montant_paye=commande.montant_paye,
        solde=commande.solde,
        en_retard=commande.en_retard,
        notes=commande.notes,
        cree_par_id=commande.cree_par_id,
        created_at=commande.created_at,
        updated_at=commande.updated_at,
        lignes=lignes_dto,
        historique=historique_dto,
    )


def format_commande_list_item(commande: Commande) -> CommandeListItem:
    """Construit un élément résumé pour la liste paginée."""
    client_nom = f"{commande.client.prenom} {commande.client.nom}" if commande.client else ""
    return CommandeListItem(
        id=commande.id,
        numero=commande.numero,
        client_id=commande.client_id,
        client_nom=client_nom,
        statut=commande.statut,
        date_commande=commande.date_commande,
        date_livraison_prevue=commande.date_livraison_prevue,
        montant_total=commande.montant_total,
        montant_paye=commande.montant_paye,
        solde=commande.solde,
        en_retard=commande.en_retard,
    )
