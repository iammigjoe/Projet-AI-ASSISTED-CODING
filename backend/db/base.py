"""
===============================================================================
Module : base
===============================================================================
Objectif :
    Base déclarative commune à tous les modèles SQLAlchemy.

Responsabilités :
    - Fixer les noms des contraintes et index (naming_convention), pour
      qu'Alembic génère les mêmes noms sur toutes les machines (conventions §4).
    - Fournir les colonnes created_at et updated_at de toutes les tables d'entité.
    - Fournir check_in() pour les contraintes CHECK construites depuis une énumération.

Utilisé par :
    backend/db/models, backend/db/migrations/env.py

Exemple d'utilisation :
    class Course(TimestampMixin, Base):
        __tablename__ = "courses"

Lot :
    A (socle et sécurité)
===============================================================================
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from backend.db.types import UtcDateTime, utc_now

# =============================================================================
# Constantes
# =============================================================================

NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}

# =============================================================================
# API publique
# =============================================================================


class Base(DeclarativeBase):
    """Classe mère de tous les modèles."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """Colonnes created_at et updated_at, instants UTC remplis automatiquement."""

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now, onupdate=utc_now)


def check_in(column: str, enum: type[StrEnum], name: str | None = None) -> CheckConstraint:
    """Construit un CHECK (column IN (...)) à partir d'une énumération.

    La liste des valeurs vient de l'énumération Python : un seul endroit à
    modifier (modele_donnees.md §5).

    Args:
        column: Nom de la colonne vérifiée.
        enum: Énumération dont les valeurs sont autorisées.
        name: Nom de la règle ; par défaut « <column>_values ».

    Returns:
        La contrainte, nommée ck_<table>_<name> par la naming_convention.

    Example:
        __table_args__ = (check_in("status", SessionStatus),)
    """
    values = ", ".join(f"'{member.value}'" for member in enum)
    return CheckConstraint(f"{column} IN ({values})", name=name or f"{column}_values")
