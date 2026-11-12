"""
===============================================================================
Tests : init_env
===============================================================================
Objectif :
    Vérifier que le script de démarrage remplit les clés secrètes avec des
    valeurs que la configuration accepte.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from pathlib import Path

from cryptography.fernet import Fernet

from backend.core.config import MIN_JWT_SECRET_LENGTH
from scripts.init_env import build_env

EXAMPLE = (Path(__file__).resolve().parents[2] / ".env.example").read_text(encoding="utf-8")


def _values(content: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in content.splitlines() if "=" in line)


def test_build_env_fills_secrets_with_valid_keys():
    values = _values(build_env(EXAMPLE))

    assert len(values["MYPLAN_JWT_SECRET_KEY"]) >= MIN_JWT_SECRET_LENGTH
    Fernet(values["MYPLAN_FERNET_KEY"])


def test_build_env_keeps_other_settings():
    assert _values(build_env(EXAMPLE))["MYPLAN_ENV"] == "dev"


def test_build_env_generates_new_secrets_each_time():
    first = _values(build_env(EXAMPLE))["MYPLAN_JWT_SECRET_KEY"]
    second = _values(build_env(EXAMPLE))["MYPLAN_JWT_SECRET_KEY"]

    assert first != second
