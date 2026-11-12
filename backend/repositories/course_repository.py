"""
===============================================================================
Repository : CourseRepository
===============================================================================
Objectif :
    Centraliser toutes les requêtes sur les matières (table courses).

Responsabilités :
    - Lire, créer, modifier et supprimer les matières d'un utilisateur.
    - Filtrer chaque requête par user_id : une matière d'un autre
      utilisateur n'est jamais trouvée.

Utilisé par :
    CourseService ; les autres lots pour vérifier qu'une matière appartient
    à l'utilisateur (documents, échéances).

Exemple d'utilisation :
    courses = course_repository.list_sorted_by_name(user_id=current_user.id)

Lot :
    A (socle et sécurité)
===============================================================================
"""

from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.db.models import Chapter, Course, Document, StudySession
from backend.domain.enums import SessionStatus

# =============================================================================
# Types
# =============================================================================


@dataclass(frozen=True)
class CourseProgress:
    """Matière et son avancement, en minutes (GET /courses du contrat)."""

    course: Course
    minutes_total: int
    minutes_done: int


# =============================================================================
# API publique
# =============================================================================


class CourseRepository:
    """Accès aux matières, toujours filtré par utilisateur."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Lecture ------------------------------------------------------------

    def list_sorted_by_name(self, user_id: int) -> list[Course]:
        """Récupère les matières d'un utilisateur, triées par nom sans tenir compte de la casse.

        Args:
            user_id: Utilisateur connecté, issu de get_current_user.

        Returns:
            Les matières de l'utilisateur, liste vide s'il n'en a aucune.
        """
        statement = (
            select(Course).where(Course.user_id == user_id).order_by(func.lower(Course.name))
        )
        return list(self._session.scalars(statement))

    def list_with_progress(
        self, user_id: int, course_id: int | None = None
    ) -> list[CourseProgress]:
        """Récupère les matières de l'utilisateur avec leur charge et le temps déjà étudié.

        La charge est la somme des durées des chapitres (correction de
        l'étudiant comprise, RG5) ; le temps étudié, la somme des sessions
        faites, tous plannings confondus (RG12).

        Args:
            user_id: Utilisateur connecté.
            course_id: Limite le résultat à cette matière, si fourni.

        Returns:
            Une entrée par matière, triées par nom sans tenir compte de la casse.
        """
        chapter_minutes = func.coalesce(Chapter.estimated_min_override, Chapter.estimated_min)
        totals = (
            select(Document.course_id, func.sum(chapter_minutes).label("minutes"))
            .join(Chapter, Chapter.document_id == Document.id)
            .group_by(Document.course_id)
            .subquery()
        )
        # Durée d'une session en minutes ; julianday lit le texte ISO 8601 UTC stocké.
        session_minutes = (
            func.julianday(StudySession.ends_at) - func.julianday(StudySession.starts_at)
        ) * 1440
        done = (
            select(Document.course_id, func.sum(session_minutes).label("minutes"))
            .join(Chapter, Chapter.document_id == Document.id)
            .join(StudySession, StudySession.chapter_id == Chapter.id)
            .where(StudySession.status == SessionStatus.DONE)
            .group_by(Document.course_id)
            .subquery()
        )
        statement = (
            select(
                Course,
                func.coalesce(totals.c.minutes, 0),
                func.coalesce(done.c.minutes, 0),
            )
            .outerjoin(totals, totals.c.course_id == Course.id)
            .outerjoin(done, done.c.course_id == Course.id)
            .where(Course.user_id == user_id)
            .order_by(func.lower(Course.name))
        )
        if course_id is not None:
            statement = statement.where(Course.id == course_id)
        return [
            CourseProgress(course=course, minutes_total=int(total), minutes_done=round(minutes))
            for course, total, minutes in self._session.execute(statement)
        ]

    def get(self, user_id: int, course_id: int) -> Course | None:
        """Récupère une matière de l'utilisateur.

        Returns:
            La matière, ou None si elle n'existe pas ou appartient à un autre
            utilisateur : l'appelant répond 404 dans les deux cas.
        """
        return self._session.scalar(
            select(Course).where(Course.id == course_id, Course.user_id == user_id)
        )

    def name_taken(self, user_id: int, name: str, except_course_id: int | None = None) -> bool:
        """Indique si l'utilisateur a déjà une matière de ce nom (casse ignorée).

        Args:
            user_id: Utilisateur connecté.
            name: Nom à vérifier.
            except_course_id: Matière à ignorer, celle qu'on renomme.
        """
        statement = select(Course.id).where(
            Course.user_id == user_id, func.lower(Course.name) == name.lower()
        )
        if except_course_id is not None:
            statement = statement.where(Course.id != except_course_id)
        return self._session.scalar(statement.limit(1)) is not None

    # --- Écriture -----------------------------------------------------------

    def add(self, user_id: int, name: str, color: str, difficulty: int) -> Course:
        """Crée une matière pour l'utilisateur ; l'appelant valide la transaction."""
        course = Course(user_id=user_id, name=name, color=color, difficulty=difficulty)
        self._session.add(course)
        self._session.flush()
        return course

    def delete(self, user_id: int, course_id: int) -> bool:
        """Supprime une matière de l'utilisateur et, par cascade, ce qui en dépend.

        Returns:
            True si une matière a été supprimée, False si elle n'existait pas
            ou appartenait à un autre utilisateur.
        """
        result = self._session.execute(
            delete(Course).where(Course.id == course_id, Course.user_id == user_id)
        )
        return result.rowcount > 0
