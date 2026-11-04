
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Informations générales de l'application
    APP_NAME: str = "API Atelier de Couture"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Configuration de la base de données
    DATABASE_URL: str

    # Configuration de sécurité JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Lecture du fichier .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()