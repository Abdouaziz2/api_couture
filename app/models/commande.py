import enum
from datetime import date, datetime
from typing import List, Optional

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


class StatutCommande(str, enum.Enum):
    """Statuts du cycle de confection et de livraison."""

    EN_ATTENTE = "en_attente"
    EN_COUPE = "en_coupe"
    EN_COUTURE = "en_couture"
    ESSAYAGE = "essayage"
    RETOUCHES = "retouches"
    TERMINEE = "terminee"
    LIVREE = "livree"
    ANNULEE = "annulee"


# Transitions autorisées selon la matrice du workflow (Section 6)
TRANSITIONS_AUTORISEES = {
    StatutCommande.EN_ATTENTE: [StatutCommande.EN_COUPE, StatutCommande.ANNULEE],
    StatutCommande.EN_COUPE: [StatutCommande.EN_COUTURE, StatutCommande.ANNULEE],
    StatutCommande.EN_COUTURE: [StatutCommande.ESSAYAGE, StatutCommande.TERMINEE, StatutCommande.ANNULEE],
    StatutCommande.ESSAYAGE: [StatutCommande.RETOUCHES, StatutCommande.TERMINEE, StatutCommande.ANNULEE],
    StatutCommande.RETOUCHES: [StatutCommande.ESSAYAGE, StatutCommande.TERMINEE, StatutCommande.ANNULEE],
    StatutCommande.TERMINEE: [StatutCommande.LIVREE],  # Uniquement via confirmation livraison
    StatutCommande.LIVREE: [],
    StatutCommande.ANNULEE: [],
}


class Commande(Base):
    """Représente une commande de confection ou de retouche."""

    __tablename__ = "commandes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    numero: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Numéro au format CMD-AAAA-NNNNN",
    )

    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id"),
        nullable=False,
        index=True,
    )

    mesure_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("mesures.id"),
        nullable=True,
        index=True,
    )

    statut: Mapped[StatutCommande] = mapped_column(
        Enum(
            StatutCommande,
            name="statut_commande",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=StatutCommande.EN_ATTENTE,
        nullable=False,
        index=True,
    )

    date_commande: Mapped[date] = mapped_column(
        Date,
        server_default=func.current_date(),
        nullable=False,
    )

    date_livraison_prevue: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    date_livraison_reelle: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )

    remise: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Remise globale en FCFA",
    )

    montant_total: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Montant total après remise en FCFA",
    )

    montant_paye: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total des paiements validés en FCFA",
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    cree_par_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateurs.id"),
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

    # Relations
    client = relationship("Client", backref="commandes")
    mesure = relationship("Mesure")
    cree_par = relationship("Utilisateur")
    lignes: Mapped[List["LigneCommande"]] = relationship(
        "LigneCommande",
        back_populates="commande",
        cascade="all, delete-orphan",
        order_by="LigneCommande.id",
    )
    historique: Mapped[List["HistoriqueStatut"]] = relationship(
        "HistoriqueStatut",
        back_populates="commande",
        cascade="all, delete-orphan",
        order_by="HistoriqueStatut.date_changement.asc()",
    )

    @property
    def solde(self) -> int:
        """Solde restant dû (total - payé)."""
        return max(0, self.montant_total - self.montant_paye)

    @property
    def en_retard(self) -> bool:
        """Conforme RG11 : en retard si date prévue dépassée et statut != livrée ni annulée."""
        if self.statut in (StatutCommande.LIVREE, StatutCommande.ANNULEE):
            return False
        return self.date_livraison_prevue < date.today()

    def __repr__(self) -> str:
        return (
            f"Commande(id={self.id}, "
            f"numero={self.numero!r}, "
            f"statut={self.statut.value!r}, "
            f"total={self.montant_total})"
        )


class LigneCommande(Base):
    """Prestation incluse dans une commande."""

    __tablename__ = "lignes_commande"

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

    type_vetement_id: Mapped[int] = mapped_column(
        ForeignKey("types_vetement.id"),
        nullable=False,
        index=True,
    )

    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Précision sur le modèle ou le tissu",
    )

    quantite: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    prix_unitaire: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Prix négocié ou prix de base du catalogue en FCFA",
    )

    # Relations
    commande: Mapped["Commande"] = relationship("Commande", back_populates="lignes")
    type_vetement = relationship("TypeVetement")

    @property
    def sous_total(self) -> int:
        """Sous-total de la ligne (quantité × prix unitaire)."""
        return self.quantite * self.prix_unitaire

    def __repr__(self) -> str:
        return (
            f"LigneCommande(id={self.id}, "
            f"commande_id={self.commande_id}, "
            f"quantite={self.quantite}, "
            f"prix_unitaire={self.prix_unitaire})"
        )


class HistoriqueStatut(Base):
    """Historisation de chaque changement de statut d'une commande (RG15)."""

    __tablename__ = "historique_statuts"

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

    ancien_statut: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Statut précédent (vide lors de la création)",
    )

    nouveau_statut: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    commentaire: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    utilisateur_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateurs.id"),
        nullable=False,
    )

    date_changement: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relations
    commande: Mapped["Commande"] = relationship("Commande", back_populates="historique")
    utilisateur = relationship("Utilisateur")

    def __repr__(self) -> str:
        return (
            f"HistoriqueStatut(id={self.id}, "
            f"commande_id={self.commande_id}, "
            f"{self.ancien_statut} -> {self.nouveau_statut})"
        )
