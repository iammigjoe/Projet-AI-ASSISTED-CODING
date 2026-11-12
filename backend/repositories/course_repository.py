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

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.db.models import Course

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
