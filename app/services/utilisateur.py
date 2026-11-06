from typing import Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.utilisateur import RoleUtilisateur, Utilisateur
from app.schemas.utilisateur import UtilisateurCreate, UtilisateurUpdate


def get_utilisateur_by_id(db: Session, user_id: int) -> Optional[Utilisateur]:
    """Récupère un utilisateur par son identifiant unique."""
    return db.get(Utilisateur, user_id)


def get_utilisateur_by_email(db: Session, email: str) -> Optional[Utilisateur]:
    """Récupère un utilisateur par son adresse e-mail (insensible à la casse)."""
    stmt = select(Utilisateur).where(Utilisateur.email == email.strip().lower())
    return db.execute(stmt).scalar_one_or_none()


def list_utilisateurs(db: Session) -> Sequence[Utilisateur]:
    """Récupère la liste de tous les utilisateurs, triés par nom complet."""
    stmt = select(Utilisateur).order_by(Utilisateur.nom_complet.asc())
    return db.execute(stmt).scalars().all()


def create_utilisateur(db: Session, user_in: UtilisateurCreate) -> Utilisateur:
    """
    Crée un nouvel utilisateur.
    Vérifie l'unicité de l'email (conforme à l'exigence 409 si doublon).
    Hache le mot de passe avec Argon2 (conforme RG21).
    """
    clean_email = user_in.email.strip().lower()
    existing_user = get_utilisateur_by_email(db, clean_email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"L'adresse e-mail '{clean_email}' est déjà utilisée par un autre compte.",
        )

    nouvel_utilisateur = Utilisateur(
        email=clean_email,
        nom_complet=user_in.nom_complet.strip(),
        mot_de_passe_hash=hash_password(user_in.mot_de_passe),
        role=user_in.role,
        actif=True,
    )
    db.add(nouvel_utilisateur)
    db.commit()
    db.refresh(nouvel_utilisateur)
    return nouvel_utilisateur


def update_utilisateur(
    db: Session,
    user_db: Utilisateur,
    user_in: UtilisateurUpdate,
    current_user: Utilisateur,
) -> Utilisateur:
    """
    Modifie un utilisateur existant en appliquant la règle de gestion RG24 :
    Un administrateur ne peut ni se désactiver lui-même ni retirer son propre rôle d'administrateur (409).
    """
    # Application de la règle RG24
    if current_user.id == user_db.id:
        if user_in.actif is False:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Action refusée : un administrateur ne peut pas se désactiver lui-même.",
            )
        if user_in.role is not None and user_in.role != RoleUtilisateur.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Action refusée : un administrateur ne peut pas retirer son propre rôle d'administrateur.",
            )

    if user_in.nom_complet is not None:
        user_db.nom_complet = user_in.nom_complet.strip()

    if user_in.role is not None:
        user_db.role = user_in.role

    if user_in.actif is not None:
        user_db.actif = user_in.actif

    if user_in.mot_de_passe is not None:
        user_db.mot_de_passe_hash = hash_password(user_in.mot_de_passe)

    db.commit()
    db.refresh(user_db)
    return user_db

