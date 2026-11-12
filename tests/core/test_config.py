"""
===============================================================================
Tests : config
===============================================================================
Objectif :
    Vérifier que la configuration refuse les secrets absents ou invalides, et
    lit correctement les variables sans préfixe des services externes.

Lot :
    A (socle et sécurité)
===============================================================================
"""

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from backend.core.config import Settings

VALID_SECRET = "x" * 32


def _settings(monkeypatch: pytest.MonkeyPatch, **env: str) -> Settings:
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_with_valid_secrets_loads_defaults(monkeypatch):
    settings = _settings(
        monkeypatch,
        MYPLAN_JWT_SECRET_KEY=VALID_SECRET,
        MYPLAN_FERNET_KEY=Fernet.generate_key().decode(),
    )

    assert settings.jwt_access_ttl_min == 15
    assert settings.max_upload_bytes == 20 * 1024 * 1024


def test_settings_without_jwt_secret_raises(monkeypatch):
    monkeypatch.delenv("MYPLAN_JWT_SECRET_KEY", raising=False)

    with pytest.raises(ValidationError, match="jwt_secret_key"):
        _settings(monkeypatch, MYPLAN_FERNET_KEY=Fernet.generate_key().decode())


def test_settings_with_short_jwt_secret_raises(monkeypatch):
    with pytest.raises(ValidationError, match="au moins 32"):
        _settings(
            monkeypatch,
            MYPLAN_JWT_SECRET_KEY="short",
            MYPLAN_FERNET_KEY=Fernet.generate_key().decode(),
        )


def test_settings_with_invalid_fernet_key_raises(monkeypatch):
    with pytest.raises(ValidationError, match="Fernet"):
        _settings(monkeypatch, MYPLAN_JWT_SECRET_KEY=VALID_SECRET, MYPLAN_FERNET_KEY="not-a-key")


def test_settings_reads_external_variables_without_prefix(monkeypatch):
    settings = _settings(
        monkeypatch,
        MYPLAN_JWT_SECRET_KEY=VALID_SECRET,
        MYPLAN_FERNET_KEY=Fernet.generate_key().decode(),
        GOOGLE_CLIENT_ID="client-123",
    )

    assert settings.google_client_id == "client-123"


def test_cors_origin_list_splits_and_strips(monkeypatch):
    settings = _settings(
        monkeypatch,
        MYPLAN_JWT_SECRET_KEY=VALID_SECRET,
        MYPLAN_FERNET_KEY=Fernet.generate_key().decode(),
        MYPLAN_CORS_ORIGINS=" http://a.test , ,http://b.test",
    )

    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]
