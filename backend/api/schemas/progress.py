"""
===============================================================================
Schémas : progress
===============================================================================
Objectif :
    Valider les changements de statut et les réponses du suivi de sessions.

Lot :
    D (agenda et suivi)
===============================================================================
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from backend.domain.enums import SessionKind, SessionStatus

# =============================================================================
# API publique
# =============================================================================


class StudySessionUpdate(BaseModel):
    """Statut choisi par l'étudiant pour une session."""

    status: Literal[SessionStatus.DONE, SessionStatus.MISSED]


class StudySessionRead(BaseModel):
    """Session mise à jour, sans exposer les détails internes du modèle."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    chapter_id: int
    kind: SessionKind
    starts_at: datetime
    ends_at: datetime
    status: SessionStatus
    completed_at: datetime | None


class ChapterProgressRead(BaseModel):
    """Durée des sessions terminées d'un chapitre, exprimée en minutes."""

    model_config = ConfigDict(from_attributes=True)

    chapter_id: int
    completed_minutes: float
