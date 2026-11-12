"""
===============================================================================
Modèle : UserSettings
===============================================================================
Objectif :
    Table user_settings : profil d'étude de l'utilisateur (P0-08), relation 1-1
    avec users.

Responsabilités :
    - Valeurs par défaut raisonnables, bornes vérifiées par la base.
    - La clé primaire est la clé étrangère vers users.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TimestampMixin, enum_type
from backend.domain.enums import MasteryGoal

# =============================================================================
# Constantes
# =============================================================================

DEFAULT_READING_SPEED_WPM = 200
DEFAULT_MAX_SESSION_MIN = 90
DEFAULT_BREAK_MIN = 15
DEFAULT_RETENTION_THRESHOLD = 0.70

# =============================================================================
# API publique
# =============================================================================


class UserSettings(TimestampMixin, Base):
    """Profil d'étude : vitesse de lecture, durée des sessions, pause, objectif."""

    __tablename__ = "user_settings"
    __table_args__ = (
        CheckConstraint("reading_speed_wpm > 0", name="reading_speed_positive"),
        CheckConstraint("max_session_min BETWEEN 15 AND 240", name="max_session_range"),
        CheckConstraint("break_min >= 0", name="break_not_negative"),
        CheckConstraint("retention_threshold BETWEEN 0 AND 1", name="retention_threshold_range"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    reading_speed_wpm: Mapped[int] = mapped_column(default=DEFAULT_READING_SPEED_WPM)
    max_session_min: Mapped[int] = mapped_column(default=DEFAULT_MAX_SESSION_MIN)
    break_min: Mapped[int] = mapped_column(default=DEFAULT_BREAK_MIN)
    mastery_goal: Mapped[MasteryGoal] = mapped_column(
        enum_type(MasteryGoal, "mastery_goal"), default=MasteryGoal.STANDARD
    )
    retention_threshold: Mapped[float] = mapped_column(default=DEFAULT_RETENTION_THRESHOLD)
    # Canal, délai avant session, activation (P2-07) ; forme fixée par le lot A en phase 3.
    notif_prefs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
