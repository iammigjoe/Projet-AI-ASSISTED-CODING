"""
===============================================================================
Schémas : auth
===============================================================================
Objectif :
    Ce qui entre et sort des routes /auth.

Responsabilités :
    - Normaliser l'email et vérifier le fuseau horaire dès l'entrée.
    - Ne jamais renvoyer de mot de passe ni de hachage.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.api.schemas.common import EmailAddress, Password, TimezoneName
from backend.db.models.user import DEFAULT_TIMEZONE

# =============================================================================
# API publique
# =============================================================================


class RegisterRequest(BaseModel):
    """Création du compte unique (inscription fermée ensuite)."""

    model_config = ConfigDict(extra="forbid")

    email: EmailAddress
    password: Password
    timezone: TimezoneName = DEFAULT_TIMEZONE


class LoginRequest(BaseModel):
    """Identifiants de connexion."""

    model_config = ConfigDict(extra="forbid")

    email: EmailAddress
    password: Password


class RefreshRequest(BaseModel):
    """Jeton de rafraîchissement à échanger contre une nouvelle paire de jetons."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1, max_length=2048)


class TokenPairRead(BaseModel):
    """Paire de jetons renvoyée après inscription, connexion ou rafraîchissement."""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105  # type de jeton, pas un secret
    expires_in: int = Field(description="Durée de validité du jeton d'accès, en secondes.")


class UserRead(BaseModel):
    """Compte de l'utilisateur connecté, sans aucun secret."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    timezone: str
