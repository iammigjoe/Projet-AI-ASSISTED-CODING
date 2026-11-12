"""
===============================================================================
Router : progress
===============================================================================
Objectif :
    Exposer l'avancement des chapitres de l'utilisateur connecté.

Lot :
    D (agenda et suivi)
===============================================================================
"""

from fastapi import APIRouter

from backend.api.deps import CurrentUser, DbSession
from backend.api.schemas.progress import ChapterProgressRead
from backend.services.progress_service import ProgressService

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("", response_model=list[ChapterProgressRead])
def get_progress(session: DbSession, user: CurrentUser) -> list[ChapterProgressRead]:
    """Renvoie les minutes faites par chapitre, depuis toutes les versions."""
    return [
        ChapterProgressRead.model_validate(progress)
        for progress in ProgressService(session).get_progress(user.id)
    ]
