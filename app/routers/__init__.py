from app.routers.auth import router as auth_router
from app.routers.utilisateur import router as utilisateur_router

__all__ = [
    "auth_router",
    "utilisateur_router",
]

