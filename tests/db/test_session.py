"""
===============================================================================
Tests : session
===============================================================================
Objectif :
    Vérifier que chaque connexion SQLite applique les PRAGMA dont dépendent les
    cascades et la concurrence (modele_donnees.md §5).

Lot :
    A (socle et sécurité)
===============================================================================
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.db.session import make_engine


def test_connection_enables_foreign_keys():
    engine = make_engine("sqlite://")

    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1


def test_file_database_uses_wal_and_busy_timeout(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'sub' / 'myplan.db'}")

    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA journal_mode")).scalar_one() == "wal"
        assert connection.execute(text("PRAGMA busy_timeout")).scalar_one() == 5000

    assert (tmp_path / "sub" / "myplan.db").exists()
    engine.dispose()


def test_foreign_key_violation_is_rejected():
    engine = make_engine("sqlite://")

    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE parents (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE children ("
                "id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parents(id))"
            )
        )

    with engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(text("INSERT INTO children (id, parent_id) VALUES (1, 42)"))


def test_in_memory_database_is_shared_between_connections():
    engine = make_engine("sqlite://")

    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE shared (id INTEGER PRIMARY KEY)"))

    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM shared")).scalar_one() == 0
