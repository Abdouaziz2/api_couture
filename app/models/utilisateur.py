import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RoleUtilisateur(str, enum.Enum):
    """Rôles disponibles dans l'application."""

    ADMIN = "admin"
    ACCUEIL = "accueil"
    TAILLEUR = "tailleur"


class Utilisateur(Base):
    """Représente un membre du personnel de l'atelier."""

    __tablename__ = "utilisateurs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    nom_complet: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    mot_de_passe_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[RoleUtilisateur] = mapped_column(
        Enum(
            RoleUtilisateur,
            name="role_utilisateur",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )

    actif: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
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
            f"Utilisateur(id={self.id}, "
            f"email={self.email!r}, "
            f"role={self.role.value!r})"
        )
