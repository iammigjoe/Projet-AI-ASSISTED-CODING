"""
===============================================================================
Module : env (Alembic)
===============================================================================
Objectif :
    Configurer Alembic pour MyPlan : base de l'application, métadonnées des
    modèles, mode « batch » indispensable à SQLite.

Responsabilités :
    - Lire l'URL de la base dans la configuration (MYPLAN_DATABASE_URL), jamais
      dans alembic.ini.
    - Exposer toutes les tables à --autogenerate en important backend.db.models.
    - Activer render_as_batch : SQLite ne sait ni supprimer ni modifier une
      colonne ; Alembic recrée alors la table.
    - Désactiver les clés étrangères pendant la migration, puis vérifier
      l'intégrité (PRAGMA foreign_key_check) avant de rendre la main.

Lève :
    RuntimeError  si la migration laisse des clés étrangères orphelines

Exemple d'utilisation :
    alembic revision --autogenerate -m "create study sessions table"
    alembic upgrade head

Lot :
    A (socle et sécurité)
===============================================================================
"""

from logging.config import fileConfig

from alembic import context

import backend.db.models  # noqa: F401  # enregistre toutes les tables dans Base.metadata
from backend.core.config import get_settings
from backend.db.base import Base
from backend.db.session import make_engine

# =============================================================================
# Configuration
# =============================================================================

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _database_url() -> str:
    """URL passée par l'appelant (tests), sinon celle de la configuration."""
    return config.attributes.get("database_url") or get_settings().database_url


# =============================================================================
# Exécution
# =============================================================================


def run_migrations_offline() -> None:
    """Écrit le SQL des migrations sans se connecter à la base."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Applique les migrations sur la base, puis vérifie les clés étrangères.

    Raises:
        RuntimeError: Si des lignes pointent vers une ligne qui n'existe plus.
    """
    engine = make_engine(_database_url())

    with engine.connect() as connection:
        # Une migration « batch » recrée la table puis supprime l'ancienne :
        # avec les clés étrangères actives, ce DROP déclencherait les
        # ON DELETE CASCADE et viderait les tables filles. Le PRAGMA n'a
        # d'effet qu'hors transaction, d'où le commit immédiat.
        connection.exec_driver_sql("PRAGMA foreign_keys = OFF")
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()

        orphans = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
        if orphans:
            raise RuntimeError(f"Clés étrangères orphelines après migration : {orphans}")

    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
