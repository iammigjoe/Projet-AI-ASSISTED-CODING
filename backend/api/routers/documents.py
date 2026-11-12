"""
===============================================================================
Router : POST /courses (import)
===============================================================================
Objectif :
    Importer un PDF ou un Markdown : crée la matière, le document et les
    chapitres (contrat StudyPlan, bloc 1 / P0-03).

Endpoints :
    POST  /courses   multipart champ « file » → matière + chapitres estimés

Sécurité :
    Utilisateur connecté. Débit limité (UPLOAD_LIMIT). Le user_id vient du
    jeton, jamais du formulaire. Une matière du même nom répond 409.

Lot :
    B (ingestion)
===============================================================================
"""

from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile, status

from backend.api.deps import CurrentClock, CurrentUser, DbSession
from backend.api.rate_limit import UPLOAD_LIMIT, limiter
from backend.api.schemas.documents import ChapterImportRead, CourseImportRead
from backend.domain.errors import ExtractionError
from backend.services.ingestion_service import IngestionService

# =============================================================================
# Constantes
# =============================================================================

router = APIRouter(tags=["courses"])
CourseFile = Annotated[UploadFile, File(description="Fichier PDF ou Markdown")]

# =============================================================================
# API publique
# =============================================================================


@router.post("/courses", status_code=status.HTTP_201_CREATED)
@limiter.limit(UPLOAD_LIMIT)
async def import_course(
    request: Request,
    user: CurrentUser,
    session: DbSession,
    clock: CurrentClock,
    file: CourseFile,
) -> CourseImportRead:
    """Importe un cours et renvoie la matière créée avec ses chapitres."""
    filename = file.filename or "cours"
    data = await file.read()
    if not data:
        raise ExtractionError("EMPTY_TEXT", "Fichier vide")

    service = IngestionService.from_session(session)
    imported = service.import_course(
        user.id,
        data,
        filename,
        now=clock(),
    )

    return CourseImportRead(
        id=imported.id,
        name=imported.name,
        chapters=[
            ChapterImportRead(id=chapter.id, title=chapter.title, hours=chapter.hours)
            for chapter in imported.chapters
        ],
        hours_total=imported.hours_total,
    )
