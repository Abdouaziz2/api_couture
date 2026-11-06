import os
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.utilisateur import RoleUtilisateur, Utilisateur


def seed_admin(db: Session) -> None:
    """Crée le compte administrateur initial si aucun administrateur n'existe."""
    admin_email = os.getenv("ADMIN_EMAIL", "admin@atelier.sn").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin1234!")
    admin_nom = os.getenv("ADMIN_NOM", "Mamadou (Patron)")

    existing = db.execute(
        select(Utilisateur).where(Utilisateur.email == admin_email)
    ).scalar_one_or_none()

    if existing:
        print(f"ℹ️ L'administrateur '{admin_email}' existe déjà.")
        return

    admin = Utilisateur(
        email=admin_email,
        nom_complet=admin_nom,
        mot_de_passe_hash=hash_password(admin_password),
        role=RoleUtilisateur.ADMIN,
        actif=True,
    )
    db.add(admin)
    db.commit()
    print(f"✅ Administrateur initial créé avec succès : {admin_email} / [MOT DE PASSE CONFIGURÉ]")


def main() -> None:
    """Point d'entrée du script d'initialisation (python -m app.seed)."""
    print("🌱 Démarrage de l'initialisation des données (seeding)...")
    db = SessionLocal()
    try:
        seed_admin(db)
        print("🎉 Initialisation terminée avec succès !")
    except Exception as exc:
        print(f"❌ Erreur lors de l'initialisation : {exc}", file=sys.stderr)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

