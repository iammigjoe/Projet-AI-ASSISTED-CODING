"""
===============================================================================
Router : /api/v1/courses
===============================================================================
Objectif :
    Exposer la gestion des matières (P0-02).

Endpoints :
    GET     /api/v1/courses              Liste les matières, triées par nom
    POST    /api/v1/courses              Crée une matière
    GET     /api/v1/courses/{course_id}  Renvoie une matière
    PATCH   /api/v1/courses/{course_id}  Modifie une matière
    DELETE  /api/v1/courses/{course_id}  Supprime une matière et ce qui en dépend

Sécurité :
    Utilisateur connecté uniquement. Chaque course_id est cherché avec le
    user_id courant : une matière d'un autre utilisateur répond 404.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from fastapi import APIRouter, Response, status

from backend.api.deps import CurrentUser, DbSession
from backend.api.schemas.courses import CourseCreate, CourseRead, CourseUpdate
from backend.services.course_service import CourseService

# =============================================================================
# Constantes
# =============================================================================

router = APIRouter(prefix="/courses", tags=["courses"])

# =============================================================================
# API publique
# =============================================================================


@router.get("")
def list_courses(user: CurrentUser, session: DbSession) -> list[CourseRead]:
    """Liste les matières de l'étudiant, triées par nom."""
    return [CourseRead.model_validate(course) for course in CourseService(session).list(user.id)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, user: CurrentUser, session: DbSession) -> CourseRead:
    """Crée une matière ; 409 si le nom est déjà utilisé."""
    course = CourseService(session).create(user.id, payload.name, payload.color, payload.difficulty)
    return CourseRead.model_validate(course)


@router.get("/{course_id}")
def get_course(course_id: int, user: CurrentUser, session: DbSession) -> CourseRead:
    """Renvoie une matière de l'étudiant."""
    return CourseRead.model_validate(CourseService(session).get(user.id, course_id))


@router.patch("/{course_id}")
def update_course(
    course_id: int, payload: CourseUpdate, user: CurrentUser, session: DbSession
) -> CourseRead:
    """Modifie les champs envoyés d'une matière."""
    course = CourseService(session).update(
        user.id,
        course_id,
        name=payload.name,
        color=payload.color,
        difficulty=payload.difficulty,
    )
    return CourseRead.model_validate(course)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int, user: CurrentUser, session: DbSession) -> Response:
    """Supprime une matière, ses documents, chapitres, échéances et sessions."""
    CourseService(session).delete(user.id, course_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
