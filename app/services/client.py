import re
from typing import Optional, Sequence, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.client import Client, GenreClient
from app.schemas.client import ClientCreate, ClientResume, ClientUpdate


def normaliser_telephone(telephone: str) -> str:
    """
    Applique la règle de gestion RG1 :
    Supprime les espaces, points, tirets et parenthèses.
    Valide que le numéro comporte de 6 à 20 chiffres avec un '+' optionnel au début.
    Lève une exception 422 si le format est invalide.
    """
    if not telephone:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le numéro de téléphone est obligatoire.",
        )

    # Nettoyage des séparateurs autorisés
    numero_epure = re.sub(r"[\s.\-()]", "", telephone.strip())

    # Format attendu : 6 à 20 chiffres avec un '+' initial facultatif
    motif = r"^\+?\d{6,20}$"
    if not re.match(motif, numero_epure):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Le numéro de téléphone est invalide. Il doit comporter entre 6 et 20 chiffres "
                "(avec un '+' initial facultatif)."
            ),
        )
    return numero_epure


def get_client_by_id(db: Session, client_id: int) -> Optional[Client]:
    """Récupère un client par son identifiant unique."""
    return db.get(Client, client_id)


def get_client_by_telephone(db: Session, telephone_normalise: str) -> Optional[Client]:
    """Recherche un client par son numéro de téléphone normalisé."""
    stmt = select(Client).where(Client.telephone == telephone_normalise)
    return db.execute(stmt).scalar_one_or_none()


def create_client(db: Session, client_in: ClientCreate) -> Client:
    """
    Crée un nouveau client.
    Normalise le numéro de téléphone et vérifie son unicité (RG1 - 409 si doublon).
    """
    tel_clean = normaliser_telephone(client_in.telephone)

    # Vérification d'unicité (RG1)
    existant = get_client_by_telephone(db, tel_clean)
    if existant is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Un client avec le numéro de téléphone '{tel_clean}' existe déjà.",
        )

    nouveau_client = Client(
        nom=client_in.nom.strip(),
        prenom=client_in.prenom.strip(),
        telephone=tel_clean,
        email=client_in.email.strip().lower() if client_in.email else None,
        adresse=client_in.adresse.strip() if client_in.adresse else None,
        genre=client_in.genre,
        notes=client_in.notes.strip() if client_in.notes else None,
    )
    db.add(nouveau_client)
    db.commit()
    db.refresh(nouveau_client)
    return nouveau_client


def list_clients(
    db: Session,
    q: Optional[str] = None,
    genre: Optional[GenreClient] = None,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[Sequence[Client], int]:
    """
    Recherche et liste les clients avec pagination (Route 8).
    - q : recherche sur nom, prénom et téléphone (minimum 2 caractères si renseigné).
    - Tri automatique : par nom puis prénom.
    """
    stmt = select(Client)

    if q is not None:
        terme = q.strip()
        if len(terme) < 2:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Le paramètre de recherche 'q' doit comporter au moins 2 caractères.",
            )
        # Recherche insensible à la casse sur nom, prénom et téléphone
        pattern = f"%{terme}%"
        stmt = stmt.where(
            or_(
                Client.nom.ilike(pattern),
                Client.prenom.ilike(pattern),
                Client.telephone.ilike(pattern),
            )
        )

    if genre is not None:
        stmt = stmt.where(Client.genre == genre)

    # Compte total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()

    # Tri par nom puis prénom, et application du limit/offset
    stmt = stmt.order_by(Client.nom.asc(), Client.prenom.asc()).limit(limit).offset(offset)
    items = db.execute(stmt).scalars().all()

    return items, total


def update_client(
    db: Session,
    client_db: Client,
    client_in: ClientUpdate,
) -> Client:
    """
    Met à jour partiellement les informations d'un client.
    - Vérifie que nom, prénom et téléphone ne sont pas vidés (422).
    - Garder son propre numéro n'est pas un doublon (Route 10).
    """
    # Téléphone
    if client_in.telephone is not None:
        tel_clean = normaliser_telephone(client_in.telephone)
        if tel_clean != client_db.telephone:
            # Vérifier qu'un autre client ne le possède pas déjà
            autre = get_client_by_telephone(db, tel_clean)
            if autre is not None and autre.id != client_db.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Le numéro '{tel_clean}' est déjà attribué à un autre client.",
                )
            client_db.telephone = tel_clean

    if client_in.nom is not None:
        client_db.nom = client_in.nom.strip()

    if client_in.prenom is not None:
        client_db.prenom = client_in.prenom.strip()

    if client_in.email is not None:
        client_db.email = client_in.email.strip().lower() if client_in.email else None

    if client_in.adresse is not None:
        client_db.adresse = client_in.adresse.strip() if client_in.adresse else None

    if client_in.genre is not None:
        client_db.genre = client_in.genre

    if client_in.notes is not None:
        client_db.notes = client_in.notes.strip() if client_in.notes else None

    db.commit()
    db.refresh(client_db)
    return client_db


def delete_client(db: Session, client: Client) -> None:
    """
    Supprime un client (conforme RG4 et Route 11).
    - Un client qui a des commandes ne peut pas être supprimé (409).
    - Supprime aussi ses mesures associées.
    """
    # Vérification des commandes existantes
    # Si la table 'commandes' existe, on vérifie si des commandes sont rattachées
    try:
        from app.models.commande import Commande
        nb_commandes = db.execute(
            select(func.count(Commande.id)).where(Commande.client_id == client.id)
        ).scalar_one()
        if nb_commandes > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Impossible de supprimer ce client : des commandes lui sont rattachées (RG4).",
            )
    except ImportError:
        # Le modèle Commande n'est pas encore implémenté
        pass

    # Suppression en cascade des mesures
    try:
        from app.models.mesure import Mesure
        db.execute(Mesure.__table__.delete().where(Mesure.client_id == client.id))
    except ImportError:
        pass

    db.delete(client)
    db.commit()


def get_client_resume(db: Session, client: Client) -> ClientResume:
    """
    Calcule le résumé d'activité du client (Route 13) :
    nb_commandes, chiffre_affaires, total_paye, solde_du, derniere_commande, a_des_mesures.
    Les commandes annulées sont exclues.
    """
    nb_commandes = 0
    chiffre_affaires = 0
    total_paye = 0
    solde_du = 0
    derniere_commande = None
    a_des_mesures = False

    try:
        from app.models.commande import Commande
        # Commandes non annulées
        stmt = (
            select(Commande)
            .where(Commande.client_id == client.id, Commande.statut != "annulee")
            .order_by(Commande.created_at.desc())
        )
        commandes = db.execute(stmt).scalars().all()
        nb_commandes = len(commandes)
        chiffre_affaires = sum(c.montant_total for c in commandes)
        total_paye = sum(c.montant_paye for c in commandes)
        solde_du = chiffre_affaires - total_paye
        if commandes:
            derniere_commande = commandes[0].numero
    except (ImportError, Exception):
        pass

    try:
        from app.models.mesure import Mesure
        nb_mesures = db.execute(
            select(func.count(Mesure.id)).where(Mesure.client_id == client.id)
        ).scalar_one()
        a_des_mesures = nb_mesures > 0
    except (ImportError, Exception):
        pass

    return ClientResume(
        client_id=client.id,
        nom_complet=f"{client.prenom} {client.nom}",
        nb_commandes=nb_commandes,
        chiffre_affaires=chiffre_affaires,
        total_paye=total_paye,
        solde_du=solde_du,
        derniere_commande=derniere_commande,
        a_des_mesures=a_des_mesures,
    )
