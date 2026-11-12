"""
===============================================================================
Modèle : User
===============================================================================
Objectif :
    Table users : le compte de l'étudiant.

Responsabilités :
    - Email unique, stocké en minuscules (vérifié par la base).
    - Mot de passe jamais stocké : seulement son hachage argon2.
    - Fuseau IANA de l'étudiant, utilisé pour toutes les conversions d'heure.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TimestampMixin
from backend.db.types import UtcDateTime

# =============================================================================
# Constantes
# =============================================================================

DEFAULT_TIMEZONE = "Europe/Paris"

# =============================================================================
# API publique
# =============================================================================


class User(TimestampMixin, Base):
    """Compte de l'étudiant ; un seul au départ (modele_donnees.md §6.7)."""

    __tablename__ = "users"
    __table_args__ = (
        # « Alice@x.fr » et « alice@x.fr » sont le même compte.
        CheckConstraint("email = lower(email)", name="email_lowercase"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # Nom IANA, pas un décalage : un décalage ne suit pas les changements d'heure.
    timezone: Mapped[str] = mapped_column(String(64), default=DEFAULT_TIMEZONE)
    # Suppression demandée : compte bloqué, lignes supprimées après nettoyage Google (RG15).
    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
