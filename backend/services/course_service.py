"""
===============================================================================
Service : CourseService
===============================================================================
Objectif :
    Gérer les matières d'un utilisateur (P0-02).

Responsabilités :
    - Refuser deux matières du même nom chez un même utilisateur, casse
      ignorée (« Analyse 2 » et « analyse 2 ») : 409 CONFLICT.
    - Répondre « introuvable » pour une matière d'un autre utilisateur.
    - Supprimer une matière avec tout ce qui en dépend (cascade en base).

Dépendances :
    Session SQLAlchemy

Utilisé par :
    backend/api/routers/courses.py

Lève :
    NotFoundError  matière inexistante ou d'un autre utilisateur
    ConflictError  nom déjà utilisé par une autre matière de l'utilisateur

Notes :
    Supprimer une matière supprime en base ses documents, chapitres, échéances
    et sessions. Les fichiers sur le disque et les événements Google ne sont
    pas concernés par la cascade : leur nettoyage viendra avec IngestionService
    (lot B) et CalendarSyncService (lot D), modele_donnees.md §5.

Exemple d'utilisation :
    course = CourseService(session).create(user.id, "Analyse 2", "#3366FF", difficulty=4)

Lot :
    A (socle et sécurité)
===============================================================================
"""

from sqlalchemy.orm import Session

from backend.db.models import Course
from backend.domain.errors import ConflictError, NotFoundError
from backend.repositories.course_repository import CourseRepository

# =============================================================================
# Constantes
# =============================================================================

NOT_FOUND_MESSAGE = "Matière introuvable."

# =============================================================================
# API publique
# =============================================================================


class CourseService:
    """Cas d'usage des matières."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._courses = CourseRepository(session)

    def list(self, user_id: int) -> list[Course]:
        """Liste les matières de l'utilisateur, triées par nom."""
        return self._courses.list_sorted_by_name(user_id)

    def get(self, user_id: int, course_id: int) -> Course:
        """Renvoie une matière de l'utilisateur.

        Raises:
            NotFoundError: Si elle n'existe pas ou appartient à un autre utilisateur.
        """
        course = self._courses.get(user_id, course_id)
        if course is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)
        return course

    def create(self, user_id: int, name: str, color: str, difficulty: int) -> Course:
        """Crée une matière.

        Raises:
            ConflictError: Si l'utilisateur a déjà une matière de ce nom.
        """
        self._ensure_name_free(user_id, name)
        course = self._courses.add(user_id, name, color, difficulty)
        self._session.commit()
        return course

    def update(
        self,
        user_id: int,
        course_id: int,
        name: str | None = None,
        color: str | None = None,
        difficulty: int | None = None,
    ) -> Course:
        """Modifie les champs fournis d'une matière ; None laisse un champ inchangé.

        Raises:
            NotFoundError: Si la matière n'existe pas ou appartient à un autre utilisateur.
            ConflictError: Si le nouveau nom est déjà pris par une autre matière.
        """
        course = self.get(user_id, course_id)
        if name is not None and name != course.name:
            self._ensure_name_free(user_id, name, except_course_id=course.id)
            course.name = name
        if color is not None:
            course.color = color
        if difficulty is not None:
            course.difficulty = difficulty
        self._session.commit()
        return course

    def delete(self, user_id: int, course_id: int) -> None:
        """Supprime une matière et tout ce qui en dépend.

        Raises:
            NotFoundError: Si la matière n'existe pas ou appartient à un autre utilisateur.
        """
        if not self._courses.delete(user_id, course_id):
            raise NotFoundError(NOT_FOUND_MESSAGE)
        self._session.commit()

    # --- Fonctions internes -------------------------------------------------

    def _ensure_name_free(
        self, user_id: int, name: str, except_course_id: int | None = None
    ) -> None:
        if self._courses.name_taken(user_id, name, except_course_id):
            raise ConflictError(f"Vous avez déjà une matière nommée « {name} ».")
