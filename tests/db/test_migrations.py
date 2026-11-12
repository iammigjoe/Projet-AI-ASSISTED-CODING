"""
===============================================================================
Tests : migrations
===============================================================================
Objectif :
    Vérifier que les migrations s'appliquent et s'annulent, qu'elles décrivent
    exactement les modèles, et qu'il n'y a qu'une seule tête Alembic.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory

import backend.db.models  # noqa: F401  # enregistre toutes les tables
from backend.db.base import Base
from backend.db.session import make_engine

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def alembic_config(tmp_path):
    config = Config(str(ROOT / "alembic.ini"))
    url = f"sqlite:///{tmp_path / 'migrations.db'}"
    config.attributes["database_url"] = url
    return config, url


def test_alembic_has_a_single_head():
    script = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))

    assert len(script.get_heads()) == 1


def test_migrations_match_models(alembic_config):
    config, url = alembic_config
    command.upgrade(config, "head")

    engine = make_engine(url)
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()

    assert differences == []


def test_migrations_downgrade_and_upgrade_again(alembic_config):
    config, _ = alembic_config

    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
