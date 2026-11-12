"""
===============================================================================
Service : IngestionService
===============================================================================
Objectif :
    Enchaîner validation, stockage, parsing, détection, estimation et
    enregistrement en base pour POST /courses (bloc 1).

Responsabilités :
    - accept_upload : taille + magic bytes + écriture UUID.
    - process_stored / process_path : parse → detect → estimate.
    - import_course : crée la matière, le document et les chapitres.

Dépendances :
    Session SQLAlchemy, UploadValidator, LocalFileStorage, ParserRegistry,
    CourseRepository, DocumentRepository, SettingsService

Utilisé par :
    backend/api/routers/documents.py

Lève :
    ExtractionError, FileTooLargeError, UnsupportedFileTypeError, ConflictError

Exemple d'utilisation :
    result = service.import_course(user_id, data, "cours.md", now=clock())

Lot :
    B (ingestion)
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.db.models.course import DEFAULT_COLOR, DEFAULT_DIFFICULTY
from backend.domain.chapter_detection import detect_chapters
from backend.domain.documents import DetectedChapter, ParsedDocument
from backend.domain.enums import DocumentStatus, DocumentType
from backend.domain.errors import ConflictError
from backend.domain.estimation import (
    StudySettings,
    estimate_minutes,
    minutes_to_hours,
)
from backend.integrations.parsers.base import ParserRegistry
from backend.integrations.parsers.markdown_parser import MarkdownParser
from backend.integrations.parsers.pdf_parser import PdfParser
from backend.integrations.storage.local_file_storage import LocalFileStorage
from backend.integrations.storage.upload_validator import UploadValidator
from backend.repositories.course_repository import CourseRepository
from backend.repositories.document_repository import DocumentRepository
from backend.services.settings_service import SettingsService

# =============================================================================
# Types
# =============================================================================


@dataclass(frozen=True)
class AcceptedUpload:
    """Métadonnées d'un fichier accepté, prêtes pour la table documents."""

    filename_original: str
    storage_key: str
    file_type: DocumentType
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class EstimatedChapter:
    """Chapitre détecté + durée calculée (avant persistance)."""

    chapter: DetectedChapter
    estimated_min: int


@dataclass(frozen=True)
class IngestionResult:
    """Sortie de process_stored, sans écriture en base."""

    chapters: tuple[EstimatedChapter, ...]
    parsed: ParsedDocument


@dataclass(frozen=True)
class ImportedChapter:
    """Chapitre persisté, prêt pour la réponse API."""

    id: int
    title: str
    hours: float


@dataclass(frozen=True)
class ImportedCourse:
    """Matière créée par l'import d'un fichier."""

    id: int
    name: str
    chapters: tuple[ImportedChapter, ...]
    hours_total: float


# =============================================================================
# API publique
# =============================================================================


class IngestionService:
    """Orchestration upload → extraction → matière + chapitres en base."""

    def __init__(
        self,
        session: Session,
        validator: UploadValidator,
        storage: LocalFileStorage,
        parsers: ParserRegistry,
    ) -> None:
        self._session = session
        self._validator = validator
        self._storage = storage
        self._parsers = parsers
        self._courses = CourseRepository(session)
        self._documents = DocumentRepository(session)
        self._settings = SettingsService(session)

    @classmethod
    def from_session(cls, session: Session) -> IngestionService:
        """Branche les implémentations locales (storage + parseurs)."""
        config = get_settings()
        return cls(
            session=session,
            validator=UploadValidator(config.max_upload_bytes),
            storage=LocalFileStorage(config.storage_dir),
            parsers=ParserRegistry([MarkdownParser(), PdfParser()]),
        )

    def accept_upload(self, data: bytes, filename_original: str) -> AcceptedUpload:
        """Valide et stocke le fichier sous un nom généré."""
        file_type = self._validator.validate(data[:4096], len(data))
        storage_key = self._storage.save(data, file_type)
        return AcceptedUpload(
            filename_original=filename_original,
            storage_key=storage_key,
            file_type=file_type,
            size_bytes=len(data),
            sha256=LocalFileStorage.sha256(data),
        )

    def process_stored(
        self,
        storage_key: str,
        settings: StudySettings,
        difficulty: int,
        file_type: DocumentType | None = None,
    ) -> IngestionResult:
        """Parse le fichier stocké, détecte et estime les chapitres."""
        path = self._storage.open(storage_key)
        resolved_type = file_type or _file_type_from_key(storage_key)
        return self.process_path(path, resolved_type, settings, difficulty)

    def process_path(
        self,
        path: Path,
        file_type: DocumentType,
        settings: StudySettings,
        difficulty: int,
    ) -> IngestionResult:
        """Enchaîne parse → detect → estimate sur un chemin déjà connu."""
        parser = self._parsers.for_type(file_type)
        parsed = parser.parse(path)
        detected = detect_chapters(parsed)
        estimated = tuple(
            EstimatedChapter(
                chapter=chapter,
                estimated_min=estimate_minutes(
                    chapter.word_count,
                    settings,
                    difficulty,
                ),
            )
            for chapter in detected
        )
        return IngestionResult(chapters=estimated, parsed=parsed)

    def import_course(
        self,
        user_id: int,
        data: bytes,
        filename_original: str,
        *,
        now: datetime,
        difficulty: int = DEFAULT_DIFFICULTY,
    ) -> ImportedCourse:
        """Importe un fichier : matière + document + chapitres.

        Args:
            user_id: Utilisateur connecté.
            data: Octets du fichier multipart.
            filename_original: Nom affiché, jamais écrit sur disque.
            now: Instant d'upload (horloge injectée).
            difficulty: Difficulté initiale de la matière (défaut 3).

        Returns:
            La matière créée et ses chapitres, heures à une décimale.

        Raises:
            ConflictError: Une matière du même nom existe déjà.
            ExtractionError: Fichier illisible, vide ou scanné.
            FileTooLargeError / UnsupportedFileTypeError: Validation refusée.
        """
        accepted = self.accept_upload(data, filename_original)
        profile = self._settings.get(user_id)
        study = StudySettings(
            reading_speed_wpm=profile.reading_speed_wpm,
            mastery_goal=profile.mastery_goal,
        )
        try:
            result = self.process_stored(
                accepted.storage_key,
                settings=study,
                difficulty=difficulty,
                file_type=accepted.file_type,
            )
        except Exception:
            self._delete_stored(accepted.storage_key)
            raise

        name = _course_name(result.parsed, filename_original)
        if self._courses.name_taken(user_id, name):
            self._delete_stored(accepted.storage_key)
            raise ConflictError(f"Vous avez déjà une matière nommée « {name} ».")

        course = self._courses.add(user_id, name, DEFAULT_COLOR, difficulty)
        document = self._documents.add(
            course.id,
            filename_original=accepted.filename_original,
            storage_key=accepted.storage_key,
            file_type=accepted.file_type,
            size_bytes=accepted.size_bytes,
            sha256=accepted.sha256,
            status=DocumentStatus.READY,
            uploaded_at=now,
        )
        detected = tuple(item.chapter for item in result.chapters)
        minutes = tuple(item.estimated_min for item in result.chapters)
        chapters = self._documents.add_chapters(document.id, detected, minutes)
        self._session.commit()

        imported = tuple(
            ImportedChapter(
                id=chapter.id,
                title=chapter.title,
                hours=minutes_to_hours(chapter.estimated_min),
            )
            for chapter in chapters
        )
        hours_total = round(sum(item.hours for item in imported), 1)
        return ImportedCourse(
            id=course.id,
            name=course.name,
            chapters=imported,
            hours_total=hours_total,
        )

    def _delete_stored(self, storage_key: str) -> None:
        """Efface un fichier stocké après un échec d'extraction ou de conflit."""
        try:
            path = self._storage.open(storage_key)
        except (FileNotFoundError, ValueError):
            return
        path.unlink(missing_ok=True)


# =============================================================================
# Fonctions internes
# =============================================================================


def _file_type_from_key(storage_key: str) -> DocumentType:
    """Extension contrôlée uniquement (.pdf / .md), jamais le nom d'origine."""
    lower = storage_key.lower()
    if lower.endswith(".pdf"):
        return DocumentType.PDF
    if lower.endswith(".md"):
        return DocumentType.MARKDOWN
    raise ValueError(f"extension inconnue pour {storage_key}")


def _course_name(parsed: ParsedDocument, filename_original: str) -> str:
    """Nom de la matière : titre # du Markdown, sinon nom du fichier."""
    for block in parsed.blocks:
        if block.heading_level == 1 and block.text.strip():
            return block.text.strip()[:100]
    stem = Path(filename_original).stem.strip() or "Cours importé"
    return stem[:100]
