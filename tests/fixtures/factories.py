"""
===============================================================================
Fabriques : données de test
===============================================================================
Objectif :
    Construire des sessions d'étude de test sans passer par le planificateur.

Lot :
    D (agenda et suivi)
===============================================================================
"""

from datetime import UTC, datetime, timedelta

from backend.db.models import StudySession
from backend.domain.enums import SessionKind, SessionStatus

DEFAULT_SESSION_START = datetime(2026, 11, 16, 17, 0, tzinfo=UTC)


def make_study_session(
    *,
    plan_id: int = 1,
    chapter_id: int = 1,
    starts_at: datetime = DEFAULT_SESSION_START,
    duration_min: int = 45,
    kind: SessionKind = SessionKind.STUDY,
    status: SessionStatus = SessionStatus.PLANNED,
    self_rating: int | None = None,
    completed_at: datetime | None = None,
) -> StudySession:
    """Crée un objet StudySession non persistant avec des valeurs par défaut valides."""
    if duration_min <= 0:
        raise ValueError("duration_min doit être strictement positif")

    return StudySession(
        plan_id=plan_id,
        chapter_id=chapter_id,
        kind=kind,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=duration_min),
        status=status,
        self_rating=self_rating,
        completed_at=completed_at,
    )
