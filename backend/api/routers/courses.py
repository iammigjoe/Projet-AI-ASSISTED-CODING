"""
===============================================================================
Router : /courses
===============================================================================
Objectif :
    Exposer les matières et leur avancement (bloc 1 du sujet, P0-02).

Endpoints :
    GET     /courses              Liste les matières et leur avancement (contrat)
    GET     /courses/{course_id}  Renvoie une matière et son avancement
    PATCH   /courses/{course_id}  Modifie le nom, la couleur ou la difficulté
    DELETE  /courses/{course_id}  Supprime une matière et ce qui en dépend

    POST /courses (multipart, import d'un fichier) appartient au lot B :
    backend/api/routers/documents.py.

Sécurité :
    Utilisateur connecté uniquement. Chaque course_id est cherché avec le
    user_id courant : une matière d'un autre utilisateur répond 404.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from fastapi import APIRouter, Response, status

from backend.api.deps import CurrentUser, DbSession
from backend.api.schemas.courses import CourseRead, CourseUpdate
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
    """Liste les matières de l'étudiant avec leur avancement, triées par nom."""
    return [
        CourseRead.from_minutes(item.course, item.minutes_total, item.minutes_done)
        for item in CourseService(session).list(user.id)
    ]


@router.get("/{course_id}")
def get_course(course_id: int, user: CurrentUser, session: DbSession) -> CourseRead:
    """Renvoie une matière de l'étudiant et son avancement."""
    item = CourseService(session).get_progress(user.id, course_id)
    return CourseRead.from_minutes(item.course, item.minutes_total, item.minutes_done)


@router.patch("/{course_id}")
def update_course(
    course_id: int, payload: CourseUpdate, user: CurrentUser, session: DbSession
) -> CourseRead:
    """Modifie les champs envoyés d'une matière."""
    service = CourseService(session)
    service.update(
        user.id,
        course_id,
        name=payload.name,
        color=payload.color,
        difficulty=payload.difficulty,
    )
    item = service.get_progress(user.id, course_id)
    return CourseRead.from_minutes(item.course, item.minutes_total, item.minutes_done)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int, user: CurrentUser, session: DbSession) -> Response:
    """Supprime une matière, ses documents, chapitres, échéances et sessions."""
    CourseService(session).delete(user.id, course_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
