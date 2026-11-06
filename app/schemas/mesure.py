from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.mesure import CHAMPS_MESURES


class MesureBase(BaseModel):
    """Schéma de base comportant les 18 mesures corporelles en cm."""

    notes: Optional[str] = Field(None, description="Remarques particulières sur la prise de mesures")
    date_prise: Optional[date] = Field(None, description="Date de la prise de mesures (aujourd'hui par défaut)")

    taille_cm: Optional[float] = Field(None, gt=0, le=300, description="Taille globale en cm")
    tour_cou: Optional[float] = Field(None, gt=0, le=300, description="Tour de cou en cm")
    carrure_dos: Optional[float] = Field(None, gt=0, le=300, description="Carrure dos en cm")
    longueur_epaule: Optional[float] = Field(None, gt=0, le=300, description="Longueur épaule en cm")
    tour_poitrine: Optional[float] = Field(None, gt=0, le=300, description="Tour de poitrine en cm")
    tour_taille: Optional[float] = Field(None, gt=0, le=300, description="Tour de taille en cm")
    tour_bassin: Optional[float] = Field(None, gt=0, le=300, description="Tour de bassin en cm")
    longueur_manche: Optional[float] = Field(None, gt=0, le=300, description="Longueur de manche en cm")
    tour_bras: Optional[float] = Field(None, gt=0, le=300, description="Tour de bras en cm")
    tour_poignet: Optional[float] = Field(None, gt=0, le=300, description="Tour de poignet en cm")
    longueur_dos: Optional[float] = Field(None, gt=0, le=300, description="Longueur de dos en cm")
    longueur_haut: Optional[float] = Field(None, gt=0, le=300, description="Longueur de haut / chemise en cm")
    longueur_pantalon: Optional[float] = Field(None, gt=0, le=300, description="Longueur de pantalon en cm")
    tour_cuisse: Optional[float] = Field(None, gt=0, le=300, description="Tour de cuisse en cm")
    tour_genou: Optional[float] = Field(None, gt=0, le=300, description="Tour de genou en cm")
    bas_pantalon: Optional[float] = Field(None, gt=0, le=300, description="Largeur bas de pantalon en cm")
    entrejambe: Optional[float] = Field(None, gt=0, le=300, description="Longueur entrejambe en cm")
    longueur_robe: Optional[float] = Field(None, gt=0, le=300, description="Longueur de robe en cm")


class MesureCreate(MesureBase):
    """
    Schéma pour l'enregistrement d'une nouvelle prise de mesures.
    Règle RG2 : au moins une mesure doit être renseignée.
    """

    @model_validator(mode="after")
    def validate_au_moins_une_mesure(self) -> "MesureCreate":
        a_au_moins_une = any(getattr(self, champ) is not None for champ in CHAMPS_MESURES)
        if not a_au_moins_une:
            raise ValueError(
                "Une prise de mesures doit contenir au moins une mesure corporelle (RG2)."
            )
        return self


class MesureUpdate(BaseModel):
    """Schéma pour la correction d'une prise de mesures existante (PATCH)."""

    notes: Optional[str] = None
    date_prise: Optional[date] = None

    taille_cm: Optional[float] = Field(None, gt=0, le=300)
    tour_cou: Optional[float] = Field(None, gt=0, le=300)
    carrure_dos: Optional[float] = Field(None, gt=0, le=300)
    longueur_epaule: Optional[float] = Field(None, gt=0, le=300)
    tour_poitrine: Optional[float] = Field(None, gt=0, le=300)
    tour_taille: Optional[float] = Field(None, gt=0, le=300)
    tour_bassin: Optional[float] = Field(None, gt=0, le=300)
    longueur_manche: Optional[float] = Field(None, gt=0, le=300)
    tour_bras: Optional[float] = Field(None, gt=0, le=300)
    tour_poignet: Optional[float] = Field(None, gt=0, le=300)
    longueur_dos: Optional[float] = Field(None, gt=0, le=300)
    longueur_haut: Optional[float] = Field(None, gt=0, le=300)
    longueur_pantalon: Optional[float] = Field(None, gt=0, le=300)
    tour_cuisse: Optional[float] = Field(None, gt=0, le=300)
    tour_genou: Optional[float] = Field(None, gt=0, le=300)
    bas_pantalon: Optional[float] = Field(None, gt=0, le=300)
    entrejambe: Optional[float] = Field(None, gt=0, le=300)
    longueur_robe: Optional[float] = Field(None, gt=0, le=300)


class MesureRead(MesureBase):
    """Schéma de lecture complet d'une prise de mesures."""

    id: int
    client_id: int
    prise_par_id: int
    date_prise: date
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
