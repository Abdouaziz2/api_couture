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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ModePaiement(str, enum.Enum):
    """Modes de règlement acceptés par l'atelier."""

    ESPECES = "especes"
    WAVE = "wave"
    ORANGE_MONEY = "orange_money"
    VIREMENT = "virement"
    CHEQUE = "cheque"


class Paiement(Base):
    """Enregistrement d'un acompte ou d'un solde sur une commande."""

    __tablename__ = "paiements"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    commande_id: Mapped[int] = mapped_column(
        ForeignKey("commandes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    montant: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Montant réglé en FCFA (strictement positif)",
    )

    mode: Mapped[ModePaiement] = mapped_column(
        Enum(
            ModePaiement,
            name="mode_paiement",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )

    reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Référence de transaction Wave, OM, virement ou numéro de chèque",
    )

    date_paiement: Mapped[date] = mapped_column(
        Date,
        server_default=func.current_date(),
        nullable=False,
    )

    enregistre_par_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateurs.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relations
    commande = relationship("Commande", backref="paiements")
    enregistre_par = relationship("Utilisateur")

    def __repr__(self) -> str:
        return (
            f"Paiement(id={self.id}, "
            f"commande_id={self.commande_id}, "
            f"montant={self.montant}, "
            f"mode={self.mode.value!r})"
        )
