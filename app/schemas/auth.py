from pydantic import BaseModel


class Token(BaseModel):
    """Schéma de réponse pour la connexion OAuth2."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """Données contenues dans le payload JWT."""

    sub: str
    exp: int

