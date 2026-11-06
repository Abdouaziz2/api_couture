from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.utilisateur import RoleUtilisateur

EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"


class UtilisateurBase(BaseModel):
    """Propriétés communes d'un utilisateur."""

    email: str = Field(
        ...,
        pattern=EMAIL_REGEX,
        description="Adresse e-mail valide",
        examples=["tailleur@atelier.sn"],
    )
    nom_complet: str = Field(..., min_length=2, max_length=150, examples=["Mamadou Diallo"])
    role: RoleUtilisateur


class UtilisateurCreate(UtilisateurBase):
    """Schéma pour la création d'un utilisateur (RG21: mot de passe min 8 car)."""

    mot_de_passe: str = Field(
        ...,
        min_length=8,
        description="Mot de passe en clair (minimum 8 caractères)",
        examples=["SecretPass123!"],
    )


class UtilisateurUpdate(BaseModel):
    """Schéma pour la mise à jour partielle (PATCH) d'un utilisateur."""

    nom_complet: Optional[str] = Field(None, min_length=2, max_length=150)
    role: Optional[RoleUtilisateur] = None
    actif: Optional[bool] = None
    mot_de_passe: Optional[str] = Field(
        None,
        min_length=8,
        description="Nouveau mot de passe en clair (minimum 8 caractères)",
    )


class UtilisateurRead(UtilisateurBase):
    """Schéma de lecture sécurisé (sans hash de mot de passe)."""

    id: int
    actif: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
