"""
===============================================================================
Service : IngestionService
===============================================================================
Objectif :
    Enchaîner validation, stockage, parsing, détection et estimation sans
    mélanger ces responsabilités (SRP, diagramme §2).

Responsabilités :
    - accept_upload : taille + magic bytes + écriture UUID + métadonnées.
    - process_stored : parse → detect_chapters → estimate_minutes.
    - Ne pas toucher à SQLAlchemy : le branchement DB attend le lot A.

Dépendances :
    UploadValidator, FileStorage, ParserRegistry

Utilisé par :
    DocumentsRouter (quand le lot A aura posé l'API)

Lève :
    ExtractionError

Exemple d'utilisation :
    accepted = service.accept_upload(data, "cours.md")
    result = service.process_stored(accepted.storage_key, settings, difficulty=3)

Lot :
    B (ingestion)
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.domain.chapter_detection import detect_chapters
from backend.domain.documents import DetectedChapter
from backend.domain.enums import DocumentType
from backend.domain.estimation import StudySettings, estimate_minutes
from backend.integrations.parsers.base import ParserRegistry
from backend.integrations.storage.local_file_storage import LocalFileStorage
from backend.integrations.storage.upload_validator import UploadValidator


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


# =============================================================================
# API publique
# =============================================================================


class IngestionService:
    """Orchestration upload → extraction → chapitres estimés."""

    def __init__(
        self,
        validator: UploadValidator,
        storage: LocalFileStorage,
        parsers: ParserRegistry,
    ) -> None:
        self._validator = validator
        self._storage = storage
        self._parsers = parsers

    def accept_upload(self, data: bytes, filename_original: str) -> AcceptedUpload:
        """Valide et stocke le fichier sous un nom généré.

        Args:
            data: Octets bruts reçus de l'API.
            filename_original: Nom affiché à l'étudiant, jamais écrit sur disque.

        Returns:
            Métadonnées à persister (course_id / user_id viendront du router).
        """
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
        """Parse le fichier stocké, détecte et estime les chapitres.

        Args:
            storage_key: Clé renvoyée par accept_upload.
            settings: Vitesse de lecture et objectif (provisoires tant que A
                n'a pas livré user_settings).
            difficulty: Difficulté de la matière, 1 à 5.
            file_type: Si omis, déduit de l'extension contrôlée de la clé.

        Returns:
            Chapitres avec estimated_min.
        """
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
        return IngestionResult(chapters=estimated)


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
