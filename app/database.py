
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings


# Classe de base de tous nos modèles SQLAlchemy
class Base(DeclarativeBase):
    pass


# Moteur de connexion à PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)


# Fabrique de sessions SQLAlchemy
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


# Dépendance FastAPI pour obtenir une session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()