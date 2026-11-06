from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.livraison import ModeLivraison, StatutLivraison


class LivraisonPlanification(BaseModel):
    """Schéma de planification ou replanification d'une livraison (Route 35)."""

    mode: ModeLivraison = Field(
        ...,
        description="Mode de remise : retrait_atelier ou domicile",
        examples=[ModeLivraison.DOMICILE],
    )
    date_prevue: date = Field(
        ...,
        description="Date convenue pour la livraison ou le retrait",
    )
    adresse: Optional[str] = Field(
        None,
        description="Adresse de livraison (obligatoire pour mode domicile - RG18)",
        examples=["Almadies, Villa 12, Dakar"],
    )
    livreur: Optional[str] = Field(
        None,
        description="Nom du livreur ou de l'agence de livraison",
        examples=["Express Dakar"],
    )
    notes: Optional[str] = Field(
        None,
        description="Instructions particulières de livraison",
    )

    @model_validator(mode="after")
    def validate_adresse_domicile(self) -> "LivraisonPlanification":
        if self.mode == ModeLivraison.DOMICILE and (not self.adresse or not self.adresse.strip()):
            raise ValueError("Une livraison à domicile exige obligatoirement une adresse (RG18).")
        return self


class LivraisonConfirmation(BaseModel):
    """Schéma pour la confirmation de livraison (Route 37)."""

    date_effective: Optional[date] = Field(
        None,
        description="Date réelle de remise du vêtement (date du jour par défaut)",
    )
    autoriser_solde_impaye: bool = Field(
        False,
        description="Permet de confirmer la livraison même si le solde n'est pas intégralement payé (RG19)",
    )


class LivraisonRead(BaseModel):
    """Lecture détaillée d'une livraison."""

    id: int
    commande_id: int
    mode: ModeLivraison
    adresse: Optional[str]
    livreur: Optional[str]
    date_prevue: date
    date_effective: Optional[date]
    statut: StatutLivraison
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LivraisonTourneeItem(BaseModel):
    """Élément de la liste de tournée de livraison (Route 38)."""

    id: int
    commande_id: int
    numero_commande: str
    client_nom: str
    client_telephone: str
    solde_commande: int
    mode: ModeLivraison
    adresse: Optional[str]
    livreur: Optional[str]
    date_prevue: date
    date_effective: Optional[date]
    statut: StatutLivraison
    notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)
