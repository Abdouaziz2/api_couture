from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TypeVetementBase(BaseModel):
    """Propriétés communes d'une prestation de catalogue."""

    nom: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Nom unique de la prestation",
        examples=["Boubou"],
    )
    description: Optional[str] = Field(
        None,
        description="Description facultative de la prestation",
        examples=["Boubou homme en bazin ou brodé"],
    )
    prix_base: int = Field(
        ...,
        ge=0,
        description="Prix de base en FCFA (entier positif ou nul)",
        examples=[35000],
    )
    delai_jours: int = Field(
        ...,
        ge=1,
        description="Délai moyen de confection en jours (au moins 1 jour)",
        examples=[10],
    )


class TypeVetementCreate(TypeVetementBase):
    """Schéma pour l'ajout d'une prestation au catalogue."""
    pass


class TypeVetementUpdate(BaseModel):
    """Schéma pour la modification partielle d'une prestation (PATCH)."""

    nom: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None
    prix_base: Optional[int] = Field(None, ge=0)
    delai_jours: Optional[int] = Field(None, ge=1)
    actif: Optional[bool] = None


class TypeVetementRead(TypeVetementBase):
    """Schéma de lecture d'une prestation du catalogue."""

    id: int
    actif: bool

    model_config = ConfigDict(from_attributes=True)
