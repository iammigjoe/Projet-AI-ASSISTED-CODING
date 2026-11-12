"""
===============================================================================
Modèle : Deadline
===============================================================================
Objectif :
    Tables deadlines et deadline_chapters : examens et rendus, et les chapitres
    qu'ils concernent (P0-10).

Responsabilités :
    - due_at est un instant UTC.
    - user_id est porté directement, en plus du chemin par la matière : RG4
      impose que les deux mènent au même utilisateur, ce que le service vérifie
      (modele_donnees.md §3).

Lot :
    C (planification)
===============================================================================
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TimestampMixin, enum_type
from backend.db.types import UtcDateTime
from backend.domain.enums import DeadlineType

# =============================================================================
# Constantes
# =============================================================================

DEFAULT_IMPORTANCE = 2

# =============================================================================
# API publique
# =============================================================================


class Deadline(TimestampMixin, Base):
    """Échéance : examen ou rendu, avec sa date et son importance."""

    __tablename__ = "deadlines"
    __table_args__ = (CheckConstraint("importance BETWEEN 1 AND 3", name="importance_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    type: Mapped[DeadlineType] = mapped_column(enum_type(DeadlineType, "type"))
    due_at: Mapped[datetime] = mapped_column(UtcDateTime)
    importance: Mapped[int] = mapped_column(default=DEFAULT_IMPORTANCE)


# Association N-N : une échéance concerne 1 à N chapitres, un chapitre 0 à N échéances.
deadline_chapters = Table(
    "deadline_chapters",
    Base.metadata,
    Column("deadline_id", ForeignKey("deadlines.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "chapter_id",
        ForeignKey("chapters.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
)
