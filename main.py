from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.routers import (
    auth_router,
    catalogue_router,
    client_router,
    commande_router,
    mesure_router,
    paiement_router,
    utilisateur_router,
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API REST sécurisée de gestion pour l'atelier de couture de Mamadou à Dakar.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

# Configuration CORS pour autoriser l'accès depuis d'éventuels frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route de santé (hors préfixe, conforme à la spécification N°44)
@app.get(
    "/health",
    tags=["Santé"],
    summary="Contrôle de santé du service",
    description="Vérifie la disponibilité de l'API et la connexion effective à PostgreSQL.",
)
def health_check() -> dict[str, str]:
    """Répond {'status': 'ok'} après avoir vérifié que la base répond."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Base de données inaccessible : {exc}",
        )


# Enregistrement des routeurs préfixés par /api/v1
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(utilisateur_router, prefix=settings.API_V1_PREFIX)
app.include_router(client_router, prefix=settings.API_V1_PREFIX)
app.include_router(catalogue_router, prefix=settings.API_V1_PREFIX)
app.include_router(mesure_router, prefix=settings.API_V1_PREFIX)
app.include_router(commande_router, prefix=settings.API_V1_PREFIX)
app.include_router(paiement_router, prefix=settings.API_V1_PREFIX)
