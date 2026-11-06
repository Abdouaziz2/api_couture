from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


CHAMPS_MESURES = [
    "taille_cm",
    "tour_cou",
    "carrure_dos",
    "longueur_epaule",
    "tour_poitrine",
    "tour_taille",
    "tour_bassin",
    "longueur_manche",
    "tour_bras",
    "tour_poignet",
    "longueur_dos",
    "longueur_haut",
    "longueur_pantalon",
    "tour_cuisse",
    "tour_genou",
    "bas_pantalon",
    "entrejambe",
    "longueur_robe",
]


class Mesure(Base):
    """Représente une prise de mesures pour un client."""

    __tablename__ = "mesures"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    prise_par_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateurs.id"),
        nullable=False,
        index=True,
    )

    date_prise: Mapped[date] = mapped_column(
        Date,
        server_default=func.current_date(),
        nullable=False,
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Les 18 mesures facultatives en cm (nombres à virgule flottante)
    taille_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tour_cou: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    carrure_dos: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longueur_epaule: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tour_poitrine: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tour_taille: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tour_bassin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longueur_manche: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tour_bras: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tour_poignet: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longueur_dos: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longueur_haut: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longueur_pantalon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tour_cuisse: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tour_genou: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bas_pantalon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    entrejambe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longueur_robe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

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

    # Relations
    client = relationship("Client", backref="mesures")
    prise_par = relationship("Utilisateur")

    def __repr__(self) -> str:
        return (
            f"Mesure(id={self.id}, "
            f"client_id={self.client_id}, "
            f"date_prise={self.date_prise})"
        )
