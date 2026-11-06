import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GenreClient(str, enum.Enum):
    """Genres acceptés pour les clients."""

    HOMME = "homme"
    FEMME = "femme"
    ENFANT = "enfant"


class Client(Base):
    """Représente un client de l'atelier de couture."""

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    nom: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    prenom: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    telephone: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True,
        nullable=False,
    )

    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    adresse: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    genre: Mapped[GenreClient] = mapped_column(
        Enum(
            GenreClient,
            name="genre_client",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
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

    def __repr__(self) -> str:
        return (
            f"Client(id={self.id}, "
            f"nom={self.nom!r}, "
            f"prenom={self.prenom!r}, "
            f"telephone={self.telephone!r})"
        )
