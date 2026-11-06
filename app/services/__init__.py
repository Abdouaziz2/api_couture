from app.services.auth import authenticate_user
from app.services.client import (
    create_client,
    delete_client,
    get_client_by_id,
    get_client_by_telephone,
    get_client_resume,
    list_clients,
    normaliser_telephone,
    update_client,
)
from app.services.mesure import (
    create_mesure,
    delete_mesure,
    get_derniere_mesure_client,
    get_mesure_by_id,
    list_mesures_client,
    update_mesure,
)
from app.services.type_vetement import (
    create_type_vetement,
    get_type_vetement_by_id,
    get_type_vetement_by_nom,
    list_types_vetement,
    update_type_vetement,
)
from app.services.utilisateur import (
    create_utilisateur,
    get_utilisateur_by_email,
    get_utilisateur_by_id,
    list_utilisateurs,
    update_utilisateur,
)

__all__ = [
    "authenticate_user",
    "create_client",
    "create_mesure",
    "create_type_vetement",
    "create_utilisateur",
    "delete_client",
    "delete_mesure",
    "get_client_by_email",
    "get_client_by_id",
    "get_client_by_telephone",
    "get_client_resume",
    "get_derniere_mesure_client",
    "get_mesure_by_id",
    "get_type_vetement_by_id",
    "get_type_vetement_by_nom",
    "list_clients",
    "list_mesures_client",
    "list_types_vetement",
    "list_utilisateurs",
    "normaliser_telephone",
    "update_client",
    "update_mesure",
    "update_type_vetement",
    "update_utilisateur",
]
