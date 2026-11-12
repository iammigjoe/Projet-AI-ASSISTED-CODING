"""
===============================================================================
Tests : conftest
===============================================================================
Objectif :
    Fixtures communes à tous les lots : configuration de test, base SQLite en
    mémoire, client HTTP de l'API.

Responsabilités :
    - Fixer des variables d'environnement de test avant tout import de l'application,
      pour qu'aucun test ne lise le .env d'un développeur.
    - Fournir une base neuve et vide à chaque test.

Lot :
    A (socle et sécurité)
===============================================================================
"""

import os
from collections.abc import Iterator

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

# =============================================================================
# Environnement de test
# =============================================================================

# Posé avant tout import du backend : get_settings() lit l'environnement une
# seule fois, et un .env de développeur ne doit jamais influencer les tests.
os.environ.update(
    {
        "MYPLAN_ENV": "test",
        "MYPLAN_DATABASE_URL": "sqlite://",
        "MYPLAN_JWT_SECRET_KEY": "test-secret-key-that-is-long-enough-0123456789",
        "MYPLAN_FERNET_KEY": Fernet.generate_key().decode(),
    }
)

# =============================================================================
# Base de données
# =============================================================================


@pytest.fixture
def engine() -> Iterator[Engine]:
    """Base SQLite en mémoire, neuve pour chaque test, avec toutes les tables."""
    import backend.db.models  # noqa: F401  # enregistre toutes les tables
    from backend.db.base import Base
    from backend.db.session import make_engine

    test_engine = make_engine("sqlite://")
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    """Session sur la base de test ; ce qui n'est pas commité est annulé."""
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.rollback()
    session.close()
