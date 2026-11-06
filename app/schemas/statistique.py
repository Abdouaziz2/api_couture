from datetime import date
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.commande import StatutCommande


class TableauDeBord(BaseModel):
    """Indicateurs clés du tableau de bord atelier (Route 39)."""

    chiffre_affaires_mois: int = Field(..., description="Chiffre d'affaires facturé ce mois (FCFA)")
    encaisse_mois: int = Field(..., description="Montant total effectivement encaissé ce mois (FCFA)")
    nb_commandes_mois: int = Field(..., description="Nombre total de commandes passées ce mois")
    reste_a_encaisser: int = Field(..., description="Montant total des soldes restant dus (commandes non annulées)")
    commandes_par_statut: Dict[str, int] = Field(..., description="Répartition des commandes par statut")
    nb_commandes_en_retard: int = Field(..., description="Commandes dont la date prévue est dépassée et non livrées/annulées")
    commandes_pretes_a_livrer: int = Field(..., description="Commandes terminées prêtes pour remise client")
    livraisons_du_jour: int = Field(..., description="Livraisons planifiées pour la date d'aujourd'hui")


class ChiffreAffairesPoint(BaseModel):
    """Point d'évolution du chiffre d'affaires (Route 40)."""

    periode: str = Field(..., description="Date (YYYY-MM-DD) ou Mois (YYYY-MM)")
    montant_total: int = Field(..., description="Total facturé en FCFA")
    montant_encaisse: int = Field(..., description="Total encaissé en FCFA")
    nb_commandes: int = Field(..., description="Nombre de commandes sur la période")


class StatTypeVetement(BaseModel):
    """Performance par prestation du catalogue (Route 41)."""

    type_vetement_id: int
    nom: str
    quantite_commandee: int
    chiffre_affaires: int

    model_config = ConfigDict(from_attributes=True)


class TopClientItem(BaseModel):
    """Statistiques sur un client fidèle (Route 42)."""

    client_id: int
    nom_complet: str
    telephone: str
    nb_commandes: int
    chiffre_affaires_total: int
    solde_du_total: int

    model_config = ConfigDict(from_attributes=True)


class ImpayeItem(BaseModel):
    """Détail d'une commande avec solde restant dû (Route 43)."""

    commande_id: int
    numero_commande: str
    client_nom: str
    client_telephone: str
    montant_total: int
    montant_paye: int
    solde: int
    date_livraison_prevue: date
    statut: StatutCommande

    model_config = ConfigDict(from_attributes=True)
