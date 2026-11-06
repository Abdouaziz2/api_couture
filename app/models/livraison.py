import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ModeLivraison(str, enum.Enum):
    """Modes de livraison disponibles."""

    RETRAIT_ATELIER = "retrait_atelier"
    DOMICILE = "domicile"


class StatutLivraison(str, enum.Enum):
    """Statuts d'une livraison."""

    PLANIFIEE = "planifiee"
    LIVREE = "livree"


class Livraison(Base):
    """Représente la livraison (ou retrait) d'une commande (unique par commande)."""

    __tablename__ = "livraisons"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    commande_id: Mapped[int] = mapped_column(
        ForeignKey("commandes.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    mode: Mapped[ModeLivraison] = mapped_column(
        Enum(
            ModeLivraison,
            name="mode_livraison",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )

    adresse: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Obligatoire pour livraison à domicile (RG18)",
    )

    livreur: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="Nom ou prestataire en charge de la livraison",
    )

    date_prevue: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    date_effective: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Date réelle de remise du vêtement (RG20)",
    )

    statut: Mapped[StatutLivraison] = mapped_column(
        Enum(
            StatutLivraison,
            name="statut_livraison",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=StatutLivraison.PLANIFIEE,
        nullable=False,
        index=True,
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relation 1-to-1 avec Commande
    commande = relationship("Commande", backref="livraison", uselist=False)

    def __repr__(self) -> str:
        return (
            f"Livraison(id={self.id}, "
            f"commande_id={self.commande_id}, "
            f"mode={self.mode.value!r}, "
            f"statut={self.statut.value!r})"
        )
