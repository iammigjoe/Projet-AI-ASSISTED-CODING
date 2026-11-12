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
from pydantic import Field, SecretStr, field_validator
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
    # Noms d'hôte acceptés dans l'en-tête Host, séparés par des virgules.
    allowed_hosts: str = "localhost,127.0.0.1"

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
        return _split_list(self.cors_origins)

    @property
    def max_request_bytes(self) -> int:
        """Taille maximale d'un corps de requête : un upload, plus l'enveloppe multipart."""
        return self.max_upload_bytes + 1024 * 1024

    @property
    def allowed_host_list(self) -> list[str]:
        """Noms d'hôte acceptés, sans espaces ni entrées vides."""
        return _split_list(self.allowed_hosts)


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


# =============================================================================
# Fonctions internes
# =============================================================================


def _split_list(value: str) -> list[str]:
    """Découpe une liste séparée par des virgules, sans espaces ni entrées vides."""
    return [item.strip() for item in value.split(",") if item.strip()]
