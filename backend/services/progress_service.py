"""
===============================================================================
Service : progress
===============================================================================
Objectif :
    Mettre à jour le statut des sessions et calculer la progression par chapitre.

Responsabilités :
    - Vérifier qu'une session appartient à l'utilisateur courant.
    - Enregistrer l'heure de fin lorsqu'une session est marquée faite.
    - Calculer la progression à partir des sessions faites de tous les plans.

Lot :
    D (agenda et suivi)
===============================================================================
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Chapter, Course, Document, Plan, StudySession
from backend.domain.enums import SessionStatus
from backend.domain.errors import NotFoundError
from backend.domain.progress import ChapterProgress, calculate_progress

# =============================================================================
# API publique
# =============================================================================


class ProgressService:
    """Cas d'usage du suivi d'étude."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def update_study_session(
        self,
        user_id: int,
        study_session_id: int,
        status: SessionStatus,
        now: datetime,
    ) -> StudySession:
        """Marque une session faite ou non faite, sans exposer celles d'autrui."""
        study_session = self._session.scalar(
            select(StudySession)
            .join(Plan, Plan.id == StudySession.plan_id)
            .join(Chapter, Chapter.id == StudySession.chapter_id)
            .join(Document, Document.id == Chapter.document_id)
            .join(Course, Course.id == Document.course_id)
            .where(
                StudySession.id == study_session_id,
                Plan.user_id == user_id,
                Course.user_id == user_id,
            )
        )
        if study_session is None:
            raise NotFoundError("Session introuvable.")

        was_done = study_session.status is SessionStatus.DONE
        study_session.status = status
        if status is SessionStatus.DONE:
            if not was_done or study_session.completed_at is None:
                study_session.completed_at = now
        else:
            study_session.completed_at = None
            study_session.self_rating = None

        self._session.commit()
        return study_session

    def get_progress(self, user_id: int) -> tuple[ChapterProgress, ...]:
        """Renvoie la durée faite de chaque chapitre, toutes versions incluses."""
        chapter_ids = self._session.scalars(
            select(Chapter.id)
            .join(Document, Document.id == Chapter.document_id)
            .join(Course, Course.id == Document.course_id)
            .where(Course.user_id == user_id)
        ).all()

        completed_rows = self._session.execute(
            select(StudySession.chapter_id, StudySession.starts_at, StudySession.ends_at)
            .join(Plan, Plan.id == StudySession.plan_id)
            .join(Chapter, Chapter.id == StudySession.chapter_id)
            .join(Document, Document.id == Chapter.document_id)
            .join(Course, Course.id == Document.course_id)
            .where(
                Plan.user_id == user_id,
                Course.user_id == user_id,
                StudySession.status == SessionStatus.DONE,
            )
        )
        completed_sessions = [
            (chapter_id, int((ends_at - starts_at).total_seconds()))
            for chapter_id, starts_at, ends_at in completed_rows
        ]
        return calculate_progress(chapter_ids, completed_sessions)
