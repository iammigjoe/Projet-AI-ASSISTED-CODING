"""
===============================================================================
Module : session
===============================================================================
Objectif :
    Créer le moteur SQLAlchemy et les sessions, avec les réglages SQLite dont
    dépendent l'intégrité et la concurrence.

Responsabilités :
    - À chaque connexion : PRAGMA foreign_keys = ON (sans lui, SQLite ignore les
      clés étrangères et les ON DELETE CASCADE), journal_mode = WAL,
      busy_timeout = 5000.
    - Créer le dossier de la base SQLite s'il n'existe pas.
    - Fournir une fabrique de sessions unique pour l'application.

Utilisé par :
    backend.api.deps (get_db), backend/db/migrations/env.py, tests/conftest.py

Exemple d'utilisation :
    with get_session_factory()() as session:
        session.execute(select(User))

Lot :
    A (socle et sécurité)
===============================================================================
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.core.config import get_settings

# =============================================================================
# Constantes
# =============================================================================

SQLITE_PRAGMAS = (
    "PRAGMA foreign_keys = ON",
    "PRAGMA journal_mode = WAL",
    "PRAGMA busy_timeout = 5000",
)

# =============================================================================
# API publique
# =============================================================================


def make_engine(database_url: str) -> Engine:
    """Crée un moteur, avec les PRAGMA SQLite appliqués à chaque connexion.

    Args:
        database_url: URL SQLAlchemy ; « sqlite:// » donne une base en mémoire,
            partagée par toutes les sessions du moteur (utile aux tests).

    Returns:
        Le moteur configuré.
    """
    url = make_url(database_url)
    options: dict[str, Any] = {}

    if url.get_backend_name() == "sqlite":
        # FastAPI peut servir une requête sur un autre thread que celui qui a
        # ouvert la connexion : la vérification de SQLite doit être levée.
        options["connect_args"] = {"check_same_thread": False}
        if url.database in (None, "", ":memory:"):
            # Une base en mémoire n'existe que pour sa connexion : une seule
            # connexion partagée, sinon chaque session verrait une base vide.
            options["poolclass"] = StaticPool
        else:
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(url, **options)

    if url.get_backend_name() == "sqlite":
        event.listen(engine, "connect", _apply_sqlite_pragmas)

    return engine


@lru_cache
def get_engine() -> Engine:
    """Renvoie le moteur de l'application, créé une seule fois par processus."""
    return make_engine(get_settings().database_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Renvoie la fabrique de sessions de l'application.

    Les objets restent lisibles après commit (expire_on_commit=False) : un
    service peut renvoyer ce qu'il vient d'écrire sans nouvelle requête.
    """
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


# =============================================================================
# Fonctions internes
# =============================================================================


def _apply_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
    """Applique les PRAGMA de SQLITE_PRAGMAS à une connexion qui vient de s'ouvrir."""
    cursor = dbapi_connection.cursor()
    for pragma in SQLITE_PRAGMAS:
        cursor.execute(pragma)
    cursor.close()
