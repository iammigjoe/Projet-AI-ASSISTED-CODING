"""
===============================================================================
Router : study-sessions
===============================================================================
Objectif :
    Permettre à l'étudiant de marquer ses sessions faites ou non faites.

Sécurité :
    Une session appartenant à un autre utilisateur répond 404.

Lot :
    D (agenda et suivi)
===============================================================================
"""

from fastapi import APIRouter

from backend.api.deps import CurrentClock, CurrentUser, DbSession
from backend.api.schemas.progress import StudySessionRead, StudySessionUpdate
from backend.services.progress_service import ProgressService

router = APIRouter(prefix="/study-sessions", tags=["study-sessions"])


@router.patch("/{session_id}", response_model=StudySessionRead)
def update_study_session(
    session_id: int,
    payload: StudySessionUpdate,
    session: DbSession,
    user: CurrentUser,
    clock: CurrentClock,
) -> StudySessionRead:
    """Marque une session comme faite ou non faite."""
    study_session = ProgressService(session).update_study_session(
        user.id, session_id, payload.status, clock()
    )
    return StudySessionRead.model_validate(study_session)
