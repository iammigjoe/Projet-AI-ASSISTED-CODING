"""
===============================================================================
Repository : DocumentRepository
===============================================================================
Objectif :
    Persister les documents et leurs chapitres après un import (POST /courses).

Responsabilités :
    - Créer le document rattaché à une matière déjà vérifiée.
    - Créer les chapitres ordonnés avec leur durée estimée.
    - Ne pas filtrer par user_id ici : la matière a déjà été créée pour
      l'utilisateur courant (CourseRepository.add).

Utilisé par :
    IngestionService

Exemple d'utilisation :
    document = document_repository.add(course_id, ...)
    chapters = document_repository.add_chapters(document.id, detected, minutes)

Lot :
    B (ingestion)
===============================================================================
"""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.orm import Session

from backend.db.models import Chapter, Document
from backend.domain.documents import DetectedChapter
from backend.domain.enums import DocumentStatus, DocumentType

# =============================================================================
# API publique
# =============================================================================


class DocumentRepository:
    """Écriture des documents et chapitres après extraction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        course_id: int,
        *,
        filename_original: str,
        storage_key: str,
        file_type: DocumentType,
        size_bytes: int,
        sha256: str,
        status: DocumentStatus,
        uploaded_at: datetime,
        error_code: str | None = None,
    ) -> Document:
        """Crée un document ; l'appelant valide la transaction."""
        document = Document(
            course_id=course_id,
            filename_original=filename_original,
            storage_key=storage_key,
            type=file_type,
            size_bytes=size_bytes,
            sha256=sha256,
            status=status,
            error_code=error_code,
            uploaded_at=uploaded_at,
        )
        self._session.add(document)
        self._session.flush()
        return document

    def add_chapters(
        self,
        document_id: int,
        detected: Sequence[DetectedChapter],
        estimated_minutes: Sequence[int],
    ) -> list[Chapter]:
        """Crée les chapitres détectés, dans l'ordre."""
        if len(detected) != len(estimated_minutes):
            raise ValueError("detected et estimated_minutes doivent avoir la même longueur")
        chapters: list[Chapter] = []
        for chapter_data, minutes in zip(detected, estimated_minutes, strict=True):
            chapter = Chapter(
                document_id=document_id,
                title=chapter_data.title[:255],
                position=chapter_data.position,
                word_count=chapter_data.word_count,
                page_start=chapter_data.page_start,
                page_end=chapter_data.page_end,
                estimated_min=minutes,
                estimated_min_override=None,
                is_validated=False,
            )
            self._session.add(chapter)
            chapters.append(chapter)
        self._session.flush()
        return chapters
