"""
===============================================================================
Modèle : StudySession
===============================================================================
Objectif :
    Table study_sessions : une plage d'étude d'un chapitre dans un planning
    (P0-11, P0-13).

Responsabilités :
    - Instants UTC, fin strictement après le début.
    - Auto-évaluation de 1 à 5, seulement sur une session faite (RG9).
    - Exportée en .ics (bloc 4) : aucun identifiant externe à garder.

Lot :
    D (agenda et suivi)
===============================================================================
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TimestampMixin, enum_type
from backend.db.types import UtcDateTime
from backend.domain.enums import SessionKind, SessionStatus

# =============================================================================
# API publique
# =============================================================================


class StudySession(TimestampMixin, Base):
    """Session d'étude ou de révision, et son suivi."""

    __tablename__ = "study_sessions"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ends_after_starts"),
        CheckConstraint("self_rating IS NULL OR self_rating BETWEEN 1 AND 5", name="rating_range"),
        CheckConstraint("self_rating IS NULL OR status = 'done'", name="rating_when_done"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[SessionKind] = mapped_column(
        enum_type(SessionKind, "kind"), default=SessionKind.STUDY
    )
    starts_at: Mapped[datetime] = mapped_column(UtcDateTime)
    ends_at: Mapped[datetime] = mapped_column(UtcDateTime)
    status: Mapped[SessionStatus] = mapped_column(
        enum_type(SessionStatus, "status"), default=SessionStatus.PLANNED
    )
    self_rating: Mapped[int | None]
    completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
