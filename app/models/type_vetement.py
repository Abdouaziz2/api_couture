from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TypeVetement(Base):
    """Représente une prestation de couture dans le catalogue."""

    __tablename__ = "types_vetement"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    nom: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=False,
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    prix_base: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Prix de base en FCFA (entier)",
    )

    delai_jours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Délai estimé de confection en jours",
    )

    actif: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"TypeVetement(id={self.id}, "
            f"nom={self.nom!r}, "
            f"prix_base={self.prix_base}, "
            f"delai_jours={self.delai_jours}, "
            f"actif={self.actif})"
        )
