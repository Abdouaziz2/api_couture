from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.commande import StatutCommande


class LigneCommandeCreate(BaseModel):
    """Ajout d'une prestation dans une commande."""

    type_vetement_id: int = Field(..., description="ID de la prestation du catalogue")
    description: Optional[str] = Field(None, description="Précisions sur le tissu ou le modèle")
    quantite: int = Field(1, ge=1, description="Quantité d'articles à confectionner")
    prix_unitaire: Optional[int] = Field(
        None,
        ge=0,
        description="Prix négocié en FCFA. Si omis, prend le prix de base du catalogue (RG6).",
    )


class LigneCommandeRead(BaseModel):
    """Lecture d'une ligne de commande avec son sous-total."""

    id: int
    commande_id: int
    type_vetement_id: int
    type_vetement_nom: str
    description: Optional[str]
    quantite: int
    prix_unitaire: int
    sous_total: int

    model_config = ConfigDict(from_attributes=True)


class HistoriqueStatutRead(BaseModel):
    """Ligne chronologique de changement de statut (RG15)."""

    id: int
    ancien_statut: Optional[str]
    nouveau_statut: str
    commentaire: Optional[str]
    utilisateur_id: int
    date_changement: datetime

    model_config = ConfigDict(from_attributes=True)


class CommandeCreate(BaseModel):
    """Schéma pour la création d'une commande (Route 24)."""

    client_id: int
    mesure_id: Optional[int] = None
    lignes: List[LigneCommandeCreate] = Field(..., min_length=1, description="Au moins une ligne requise (RG10)")
    remise: int = Field(0, ge=0, description="Remise accordée en FCFA (défaut: 0)")
    date_livraison_prevue: Optional[date] = Field(
        None,
        description="Date de livraison convenue. Si omise, calculée selon les délais catalogue (RG8).",
    )
    notes: Optional[str] = None


class CommandeUpdate(BaseModel):
    """Modification partielle d'une commande (Route 27)."""

    mesure_id: Optional[int] = None
    date_livraison_prevue: Optional[date] = None
    remise: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


class ChangementStatutRequest(BaseModel):
    """Demande d'évolution du statut d'une commande (Route 28)."""

    statut: StatutCommande
    commentaire: Optional[str] = Field(
        None,
        description="Commentaire explicatif (obligatoire pour annulation avec acompte - RG14)",
    )


class CommandeListItem(BaseModel):
    """Élément d'une liste paginée de commandes (Route 25)."""

    id: int
    numero: str
    client_id: int
    client_nom: str
    statut: StatutCommande
    date_commande: date
    date_livraison_prevue: date
    montant_total: int
    montant_paye: int
    solde: int
    en_retard: bool

    model_config = ConfigDict(from_attributes=True)


class CommandePagination(BaseModel):
    """Format standard de pagination pour les commandes."""

    items: List[CommandeListItem]
    total: int
    limit: int
    offset: int


class CommandeRead(BaseModel):
    """Détail complet d'une commande (Route 26)."""

    id: int
    numero: str
    client_id: int
    client_nom: str
    mesure_id: Optional[int]
    statut: StatutCommande
    date_commande: date
    date_livraison_prevue: date
    date_livraison_reelle: Optional[date]
    remise: int
    montant_total: int
    montant_paye: int
    solde: int
    en_retard: bool
    notes: Optional[str]
    cree_par_id: int
    created_at: datetime
    updated_at: datetime
    lignes: List[LigneCommandeRead]
    historique: List[HistoriqueStatutRead]

    model_config = ConfigDict(from_attributes=True)
