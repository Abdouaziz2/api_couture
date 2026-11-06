from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.paiement import ModePaiement


class PaiementCreate(BaseModel):
    """Schéma d'encaissement d'un acompte ou d'un solde (Route 32)."""

    montant: int = Field(
        ...,
        gt=0,
        description="Montant versé en FCFA (doit être strictement positif - RG16)",
        examples=[25000],
    )
    mode: ModePaiement = Field(
        ...,
        description="Mode de règlement (especes, wave, orange_money, virement, cheque)",
        examples=[ModePaiement.WAVE],
    )
    reference: Optional[str] = Field(
        None,
        max_length=100,
        description="Référence de transaction ou numéro de reçu",
        examples=["TXN-WAVE-89234"],
    )
    date_paiement: Optional[date] = Field(
        None,
        description="Date de paiement (date du jour par défaut, ne peut être future - RG16)",
    )


class PaiementRead(BaseModel):
    """Lecture d'un paiement enregistré."""

    id: int
    commande_id: int
    montant: int
    mode: ModePaiement
    reference: Optional[str]
    date_paiement: date
    enregistre_par_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
