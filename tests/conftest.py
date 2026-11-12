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
from collections.abc import Callable, Iterator

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
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


# =============================================================================
# API
# =============================================================================


@pytest.fixture
def app(engine: Engine) -> FastAPI:
    """Application FastAPI branchée sur la base de test du test en cours."""
    from backend.api.deps import get_db
    from backend.main import create_app

    test_app = create_app()
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def _test_db() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    test_app.dependency_overrides[get_db] = _test_db
    return test_app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """Client HTTP de test ; les erreurs imprévues deviennent des réponses 500."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def auth_headers() -> Callable[[int], dict[str, str]]:
    """Fabrique l'en-tête Authorization d'un utilisateur : auth_headers(user.id)."""
    from backend.core.clock import system_clock
    from backend.core.security import create_access_token

    def _headers(user_id: int) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(user_id, system_clock())}"}

    return _headers
