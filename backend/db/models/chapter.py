"""
===============================================================================
Modèle : Chapter
===============================================================================
Objectif :
    Table chapters : une partie d'un document, unité de planification (P0-05).

Responsabilités :
    - Garder la durée calculée (estimated_min) et la correction de l'étudiant
      (estimated_min_override) séparément : un recalcul n'écrase jamais la
      correction (RG5).
    - Ordre unique des chapitres dans un document.

Lot :
    B (ingestion)
===============================================================================
"""

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TimestampMixin

# =============================================================================
# API publique
# =============================================================================


class Chapter(TimestampMixin, Base):
    """Chapitre détecté puis validé par l'étudiant."""

    __tablename__ = "chapters"
    __table_args__ = (
        UniqueConstraint("document_id", "position"),
        CheckConstraint("position >= 0", name="position_not_negative"),
        CheckConstraint("word_count >= 0", name="word_count_not_negative"),
        CheckConstraint("estimated_min >= 0", name="estimated_min_not_negative"),
        CheckConstraint(
            "estimated_min_override IS NULL OR estimated_min_override > 0",
            name="override_positive",
        ),
        CheckConstraint(
            "page_start IS NULL OR page_end IS NULL OR page_end >= page_start",
            name="page_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    position: Mapped[int]
    word_count: Mapped[int]
    # PDF uniquement : sert à scinder et à retrouver le passage à résumer.
    page_start: Mapped[int | None]
    page_end: Mapped[int | None]
    estimated_min: Mapped[int]
    estimated_min_override: Mapped[int | None]
    is_validated: Mapped[bool] = mapped_column(default=False)

    @property
    def effective_min(self) -> int:
        """Durée retenue par le planificateur : la correction si elle existe (RG5)."""
        if self.estimated_min_override is not None:
            return self.estimated_min_override
        return self.estimated_min
