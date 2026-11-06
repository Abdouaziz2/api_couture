from app.routers.auth import router as auth_router
from app.routers.catalogue import router as catalogue_router
from app.routers.client import router as client_router
from app.routers.mesure import router as mesure_router
from app.routers.utilisateur import router as utilisateur_router

__all__ = [
    "auth_router",
    "catalogue_router",
    "client_router",
    "mesure_router",
    "utilisateur_router",
]
