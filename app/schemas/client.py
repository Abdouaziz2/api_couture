from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.client import GenreClient
from app.schemas.utilisateur import EMAIL_REGEX


class ClientBase(BaseModel):
    """Propriétés communes d'un client."""

    nom: str = Field(..., min_length=1, max_length=100, examples=["Diop"])
    prenom: str = Field(..., min_length=1, max_length=100, examples=["Fatou"])
    telephone: str = Field(..., examples=["77 123 45 67"])
    email: Optional[str] = Field(
        None,
        pattern=EMAIL_REGEX,
        description="Adresse email facultative du client",
        examples=["fatou.diop@example.com"],
    )
    adresse: Optional[str] = Field(
        None,
        max_length=255,
        examples=["Medina, Rue 6 x 11, Dakar"],
    )
    genre: GenreClient = Field(..., examples=[GenreClient.FEMME])
    notes: Optional[str] = Field(
        None,
        description="Notes particulières sur le client ou ses préférences",
    )


class ClientCreate(ClientBase):
    """Schéma pour la création d'un client."""
    pass


class ClientUpdate(BaseModel):
    """
    Schéma pour la modification partielle d'un client (PATCH).
    Règle : nom, prenom et telephone ne peuvent pas être vidés (422).
    """

    nom: Optional[str] = Field(None, min_length=1, max_length=100)
    prenom: Optional[str] = Field(None, min_length=1, max_length=100)
    telephone: Optional[str] = Field(None, min_length=1)
    email: Optional[str] = Field(None, pattern=EMAIL_REGEX)
    adresse: Optional[str] = Field(None, max_length=255)
    genre: Optional[GenreClient] = None
    notes: Optional[str] = None

    @field_validator("nom", "prenom", "telephone")
    @classmethod
    def validate_non_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Ce champ ne peut pas être vide.")
        return v


class ClientRead(ClientBase):
    """Schéma de lecture d'un client."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClientPagination(BaseModel):
    """Format standardisé de pagination pour la liste des clients."""

    items: list[ClientRead]
    total: int
    limit: int
    offset: int


class ClientResume(BaseModel):
    """Résumé d'activité d'un client (commandes non annulées, solde et mesures)."""

    client_id: int
    nom_complet: str
    nb_commandes: int
    chiffre_affaires: int
    total_paye: int
    solde_du: int
    derniere_commande: Optional[str] = None
    a_des_mesures: bool
