from datetime import date
from typing import Dict, List, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.client import Client
from app.models.commande import Commande, LigneCommande, StatutCommande
from app.models.livraison import Livraison, StatutLivraison
from app.models.paiement import Paiement
from app.models.type_vetement import TypeVetement
from app.schemas.statistique import (
    ChiffreAffairesPoint,
    ImpayeItem,
    StatTypeVetement,
    TableauDeBord,
    TopClientItem,
)


def get_tableau_de_bord(db: Session) -> TableauDeBord:
    """Calcule les indicateurs globaux du tableau de bord (Route 39)."""
    today = date.today()
    debut_mois = date(today.year, today.month, 1)
    if today.month == 12:
        fin_mois = date(today.year + 1, 1, 1)
    else:
        fin_mois = date(today.year, today.month + 1, 1)

    # Chiffre d'affaires du mois (commandes créées ce mois non annulées)
    stmt_ca = select(
        func.coalesce(func.sum(Commande.montant_total), 0)
    ).where(
        Commande.statut != StatutCommande.ANNULEE,
        Commande.date_commande >= debut_mois,
        Commande.date_commande < fin_mois,
    )
    ca_mois = db.execute(stmt_ca).scalar_one()

    # Montant encaissé ce mois
    stmt_encaisse = select(
        func.coalesce(func.sum(Paiement.montant), 0)
    ).where(
        Paiement.date_paiement >= debut_mois,
        Paiement.date_paiement < fin_mois,
    )
    encaisse_mois = db.execute(stmt_encaisse).scalar_one()

    # Nombre de commandes du mois
    stmt_nb_cmd = select(func.count(Commande.id)).where(
        Commande.date_commande >= debut_mois,
        Commande.date_commande < fin_mois,
    )
    nb_cmd_mois = db.execute(stmt_nb_cmd).scalar_one()

    # Reste à encaisser global (sur toutes les commandes actives non soldées)
    stmt_reste = select(
        func.coalesce(func.sum(Commande.montant_total - Commande.montant_paye), 0)
    ).where(
        Commande.statut != StatutCommande.ANNULEE,
        Commande.montant_total > Commande.montant_paye,
    )
    reste_a_encaisser = db.execute(stmt_reste).scalar_one()

    # Répartition des commandes par statut
    stats_statuts: Dict[str, int] = {st.value: 0 for st in StatutCommande}
    stmt_repart = select(Commande.statut, func.count(Commande.id)).group_by(Commande.statut)
    for statut_enum, count in db.execute(stmt_repart).all():
        stats_statuts[statut_enum.value] = count

    # Nombre de commandes en retard (RG11)
    stmt_retard = select(func.count(Commande.id)).where(
        Commande.date_livraison_prevue < today,
        Commande.statut.not_in([StatutCommande.LIVREE, StatutCommande.ANNULEE]),
    )
    nb_en_retard = db.execute(stmt_retard).scalar_one()

    # Commandes prêtes à livrer (statut 'terminee')
    stmt_pretes = select(func.count(Commande.id)).where(
        Commande.statut == StatutCommande.TERMINEE
    )
    commandes_pretes = db.execute(stmt_pretes).scalar_one()

    # Livraisons du jour (planifiées pour aujourd'hui)
    stmt_liv_jour = select(func.count(Livraison.id)).where(
        Livraison.date_prevue == today,
        Livraison.statut == StatutLivraison.PLANIFIEE,
    )
    livraisons_du_jour = db.execute(stmt_liv_jour).scalar_one()

    return TableauDeBord(
        chiffre_affaires_mois=ca_mois,
        encaisse_mois=encaisse_mois,
        nb_commandes_mois=nb_cmd_mois,
        reste_a_encaisser=reste_a_encaisser,
        commandes_par_statut=stats_statuts,
        nb_commandes_en_retard=nb_en_retard,
        commandes_pretes_a_livrer=commandes_pretes,
        livraisons_du_jour=livraisons_du_jour,
    )


def get_chiffre_affaires_evolution(
    db: Session,
    periode: str = "mois",
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
) -> List[ChiffreAffairesPoint]:
    """Calcule l'évolution du chiffre d'affaires et des encaissements par jour ou mois (Route 40)."""
    fmt = "YYYY-MM" if periode == "mois" else "YYYY-MM-DD"

    # Commandes groupées par date
    stmt_cmd = (
        select(
            func.to_char(Commande.date_commande, fmt).label("cle_periode"),
            func.coalesce(func.sum(Commande.montant_total), 0).label("total_facture"),
            func.count(Commande.id).label("nb_cmd"),
        )
        .where(Commande.statut != StatutCommande.ANNULEE)
        .group_by("cle_periode")
        .order_by("cle_periode")
    )
    if date_debut:
        stmt_cmd = stmt_cmd.where(Commande.date_commande >= date_debut)
    if date_fin:
        stmt_cmd = stmt_cmd.where(Commande.date_commande <= date_fin)

    res_cmd = db.execute(stmt_cmd).all()

    # Paiements groupés par date
    stmt_pay = (
        select(
            func.to_char(Paiement.date_paiement, fmt).label("cle_periode"),
            func.coalesce(func.sum(Paiement.montant), 0).label("total_encaisse"),
        )
        .group_by("cle_periode")
        .order_by("cle_periode")
    )
    if date_debut:
        stmt_pay = stmt_pay.where(Paiement.date_paiement >= date_debut)
    if date_fin:
        stmt_pay = stmt_pay.where(Paiement.date_paiement <= date_fin)

    res_pay = db.execute(stmt_pay).all()
    encaissements_par_periode = {row.cle_periode: row.total_encaisse for row in res_pay}

    points: Dict[str, ChiffreAffairesPoint] = {}

    for row in res_cmd:
        points[row.cle_periode] = ChiffreAffairesPoint(
            periode=row.cle_periode,
            montant_total=row.total_facture,
            montant_encaisse=encaissements_par_periode.get(row.cle_periode, 0),
            nb_commandes=row.nb_cmd,
        )

    for cle_per, total_enc in encaissements_par_periode.items():
        if cle_per not in points:
            points[cle_per] = ChiffreAffairesPoint(
                periode=cle_per,
                montant_total=0,
                montant_encaisse=total_enc,
                nb_commandes=0,
            )

    return sorted(points.values(), key=lambda p: p.periode)


def get_stats_types_vetement(db: Session) -> List[StatTypeVetement]:
    """Calcule la popularité et le chiffre d'affaires par type de vêtement (Route 41)."""
    stmt = (
        select(
            TypeVetement.id.label("type_vetement_id"),
            TypeVetement.nom.label("nom"),
            func.coalesce(func.sum(LigneCommande.quantite), 0).label("quantite_commandee"),
            func.coalesce(
                func.sum(LigneCommande.quantite * LigneCommande.prix_unitaire), 0
            ).label("chiffre_affaires"),
        )
        .join(LigneCommande, LigneCommande.type_vetement_id == TypeVetement.id, isouter=True)
        .join(
            Commande,
            (Commande.id == LigneCommande.commande_id) & (Commande.statut != StatutCommande.ANNULEE),
            isouter=True,
        )
        .group_by(TypeVetement.id, TypeVetement.nom)
        .order_by(desc("chiffre_affaires"), desc("quantite_commandee"))
    )

    rows = db.execute(stmt).all()
    return [
        StatTypeVetement(
            type_vetement_id=row.type_vetement_id,
            nom=row.nom,
            quantite_commandee=row.quantite_commandee,
            chiffre_affaires=row.chiffre_affaires,
        )
        for row in rows
    ]


def get_top_clients(db: Session, limite: int = 10) -> List[TopClientItem]:
    """Renvoie les meilleurs clients classés par chiffre d'affaires total (Route 42)."""
    stmt = (
        select(
            Client.id.label("client_id"),
            (Client.prenom + " " + Client.nom).label("nom_complet"),
            Client.telephone.label("telephone"),
            func.count(Commande.id).label("nb_commandes"),
            func.coalesce(func.sum(Commande.montant_total), 0).label("chiffre_affaires_total"),
            func.coalesce(
                func.sum(Commande.montant_total - Commande.montant_paye), 0
            ).label("solde_du_total"),
        )
        .join(Commande, Commande.client_id == Client.id)
        .where(Commande.statut != StatutCommande.ANNULEE)
        .group_by(Client.id, Client.nom, Client.prenom, Client.telephone)
        .order_by(desc("chiffre_affaires_total"), desc("nb_commandes"))
        .limit(limite)
    )

    rows = db.execute(stmt).all()
    return [
        TopClientItem(
            client_id=row.client_id,
            nom_complet=row.nom_complet,
            telephone=row.telephone,
            nb_commandes=row.nb_commandes,
            chiffre_affaires_total=row.chiffre_affaires_total,
            solde_du_total=row.solde_du_total,
        )
        for row in rows
    ]


def get_impayes(db: Session) -> List[ImpayeItem]:
    """Liste les commandes non annulées ayant un solde impayé, ordonnées par urgence (Route 43)."""
    stmt = (
        select(Commande)
        .options(joinedload(Commande.client))
        .where(
            Commande.statut != StatutCommande.ANNULEE,
            Commande.montant_total > Commande.montant_paye,
        )
        .order_by(Commande.date_livraison_prevue.asc(), Commande.id.asc())
    )

    commandes = db.execute(stmt).scalars().all()
    results: List[ImpayeItem] = []
    for cmd in commandes:
        cli = cmd.client
        nom_client = f"{cli.prenom} {cli.nom}".strip() if cli else "Client inconnu"
        tel_client = cli.telephone if cli else ""
        results.append(
            ImpayeItem(
                commande_id=cmd.id,
                numero_commande=cmd.numero,
                client_nom=nom_client,
                client_telephone=tel_client,
                montant_total=cmd.montant_total,
                montant_paye=cmd.montant_paye,
                solde=cmd.solde,
                date_livraison_prevue=cmd.date_livraison_prevue,
                statut=cmd.statut,
            )
        )
    return results
