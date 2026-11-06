import os
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.type_vetement import TypeVetement
from app.models.utilisateur import RoleUtilisateur, Utilisateur

# Catalogue initial défini dans l'Annexe B
CATALOGUE_INITIAL = [
    {
        "nom": "Boubou",
        "description": "Boubou homme en bazin ou brodé",
        "prix_base": 35000,
        "delai_jours": 10,
    },
    {
        "nom": "Costume 2 pièces",
        "description": "Veste et pantalon",
        "prix_base": 85000,
        "delai_jours": 14,
    },
    {
        "nom": "Robe",
        "description": "Robe sur mesure",
        "prix_base": 30000,
        "delai_jours": 7,
    },
    {
        "nom": "Ensemble wax",
        "description": "Tenue deux pièces en wax",
        "prix_base": 25000,
        "delai_jours": 7,
    },
    {
        "nom": "Chemise",
        "description": "Chemise sur mesure",
        "prix_base": 15000,
        "delai_jours": 5,
    },
    {
        "nom": "Pantalon",
        "description": "Pantalon sur mesure",
        "prix_base": 12000,
        "delai_jours": 4,
    },
    {
        "nom": "Retouche",
        "description": "Ourlet, rétrécissement, remplacement de fermeture",
        "prix_base": 3000,
        "delai_jours": 2,
    },
]


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


def seed_catalogue(db: Session) -> None:
    """Insère les prestations de départ du catalogue (Annexe B) si absentes."""
    nb_ajoutes = 0
    for item in CATALOGUE_INITIAL:
        existing = db.execute(
            select(TypeVetement).where(TypeVetement.nom == item["nom"])
        ).scalar_one_or_none()

        if existing is None:
            prestation = TypeVetement(
                nom=item["nom"],
                description=item["description"],
                prix_base=item["prix_base"],
                delai_jours=item["delai_jours"],
                actif=True,
            )
            db.add(prestation)
            nb_ajoutes += 1

    if nb_ajoutes > 0:
        db.commit()
        print(f"✅ Catalogue initial initialisé : {nb_ajoutes} prestation(s) ajoutée(s).")
    else:
        print("ℹ️ Les prestations du catalogue initial sont déjà présentes.")


def main() -> None:
    """Point d'entrée du script d'initialisation (python -m app.seed)."""
    print("🌱 Démarrage de l'initialisation des données (seeding)...")
    db = SessionLocal()
    try:
        seed_admin(db)
        seed_catalogue(db)
        print("🎉 Initialisation terminée avec succès !")
    except Exception as exc:
        print(f"❌ Erreur lors de l'initialisation : {exc}", file=sys.stderr)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
