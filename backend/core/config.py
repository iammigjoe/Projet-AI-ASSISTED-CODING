"""
===============================================================================
Module : config
===============================================================================
Objectif :
    Lire la configuration de l'application dans l'environnement et le fichier
    .env, une seule fois, et la valider au démarrage.

Responsabilités :
    - Seul endroit du backend qui lit des variables d'environnement.
    - Refuser de démarrer avec un secret absent, vide ou trop court.
    - Exposer les réglages sous forme typée (Path, int, SecretStr).

Utilisé par :
    backend.db.session, backend.core.security, backend.main, et tout module
    qui a besoin d'un réglage, via get_settings().

Exemple d'utilisation :
    settings = get_settings()
    engine = create_engine(settings.database_url)

Lot :
    A (socle et sécurité)
===============================================================================
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from cryptography.fernet import Fernet
from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# =============================================================================
# Constantes
# =============================================================================

MIN_JWT_SECRET_LENGTH = 32

# =============================================================================
# API publique
# =============================================================================


class Settings(BaseSettings):
    """Réglages de l'application, lus dans l'environnement puis dans .env."""

    model_config = SettingsConfigDict(
        env_prefix="MYPLAN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "sqlite:///./data/myplan.db"
    storage_dir: Path = Path("./storage")
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, gt=0)

    jwt_secret_key: SecretStr
    jwt_access_ttl_min: int = Field(default=15, gt=0)
    jwt_refresh_ttl_days: int = Field(default=7, gt=0)
    fernet_key: SecretStr

    # Liste séparée par des virgules : « http://localhost:8501,https://myplan.fr ».
    cors_origins: str = "http://localhost:8501"
    api_base_url: str = "http://localhost:8000"

    # Les variables des services externes gardent le nom attendu par leur
    # bibliothèque, sans préfixe (conventions §9).
    google_client_id: str = Field(default="", validation_alias=AliasChoices("GOOGLE_CLIENT_ID"))
    google_client_secret: SecretStr = Field(
        default=SecretStr(""), validation_alias=AliasChoices("GOOGLE_CLIENT_SECRET")
    )
    google_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/google/callback",
        validation_alias=AliasChoices("GOOGLE_REDIRECT_URI"),
    )
    anthropic_api_key: SecretStr = Field(
        default=SecretStr(""), validation_alias=AliasChoices("ANTHROPIC_API_KEY")
    )

    @field_validator("jwt_secret_key")
    @classmethod
    def _check_jwt_secret(cls, value: SecretStr) -> SecretStr:
        """Refuse un secret JWT trop court pour signer des jetons sûrs."""
        if len(value.get_secret_value()) < MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"MYPLAN_JWT_SECRET_KEY doit faire au moins {MIN_JWT_SECRET_LENGTH} caractères "
                '(générer : python -c "import secrets; print(secrets.token_hex(32))")'
            )
        return value

    @field_validator("fernet_key")
    @classmethod
    def _check_fernet_key(cls, value: SecretStr) -> SecretStr:
        """Refuse une clé que Fernet ne saurait pas utiliser."""
        try:
            Fernet(value.get_secret_value())
        except ValueError as error:
            raise ValueError(
                "MYPLAN_FERNET_KEY n'est pas une clé Fernet valide (générer : python -c "
                '"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")'
            ) from error
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        """Origines autorisées par CORS, sans espaces ni entrées vides."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Renvoie les réglages, lus et validés une seule fois par processus.

    Returns:
        Les réglages de l'application.

    Raises:
        pydantic.ValidationError: Si un réglage obligatoire est absent ou invalide ;
            le message nomme la variable en cause.
    """
    return Settings()  # type: ignore[call-arg]  # valeurs fournies par l'environnement
