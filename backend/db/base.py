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
    - Fournir enum_type() pour les colonnes à valeurs finies et leur contrainte CHECK.

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

from sqlalchemy import Enum, MetaData
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


def enum_type(enum: type[StrEnum], column: str) -> Enum:
    """Construit le type d'une colonne à valeurs finies, avec sa contrainte CHECK.

    Les valeurs stockées sont celles de l'énumération (« done », pas « DONE »),
    et la liste autorisée en base vient de l'énumération Python : un seul
    endroit à modifier (modele_donnees.md §5). La lecture rend un membre de
    l'énumération.

    Args:
        enum: Énumération dont les valeurs sont autorisées.
        column: Nom de la colonne ; la contrainte s'appelle
            ck_<table>_<column>_values (naming_convention).

    Returns:
        Le type SQLAlchemy, stocké en texte.

    Example:
        status: Mapped[SessionStatus] = mapped_column(enum_type(SessionStatus, "status"))
    """
    return Enum(
        enum,
        name=f"{column}_values",
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        length=max(len(member.value) for member in enum),
        values_callable=lambda members: [member.value for member in members],
    )
