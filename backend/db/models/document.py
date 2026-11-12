"""
===============================================================================
Modèle : Document
===============================================================================
Objectif :
    Table documents : un fichier PDF ou Markdown rattaché à une matière (P0-03).

Responsabilités :
    - Le fichier est désigné par storage_key (UUID + extension), jamais par un
      chemin ni par le nom d'origine (modele_donnees.md §5).
    - Suivre l'extraction : statut et code d'erreur (P0-04, P1-06).

Lot :
    B (ingestion)
===============================================================================
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TimestampMixin, enum_type
from backend.db.types import UtcDateTime
from backend.domain.enums import DocumentStatus, DocumentType

# =============================================================================
# API publique
# =============================================================================


class Document(TimestampMixin, Base):
    """Fichier de cours envoyé par l'étudiant et son état d'extraction."""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="size_not_negative"),
        CheckConstraint("length(sha256) = 64", name="sha256_length"),
        # Un code d'erreur n'a de sens que pour un document en échec.
        CheckConstraint("error_code IS NULL OR status = 'failed'", name="error_code_when_failed"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    # Affiché à l'étudiant uniquement ; jamais utilisé pour écrire sur le disque.
    filename_original: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(64), unique=True)
    type: Mapped[DocumentType] = mapped_column(enum_type(DocumentType, "type"))
    size_bytes: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[DocumentStatus] = mapped_column(
        enum_type(DocumentStatus, "status"), default=DocumentStatus.PENDING
    )
    # EMPTY_TEXT, SCANNED_PDF, TIMEOUT… (modele_donnees.md §1, documents).
    error_code: Mapped[str | None] = mapped_column(String(50))
    uploaded_at: Mapped[datetime] = mapped_column(UtcDateTime)
