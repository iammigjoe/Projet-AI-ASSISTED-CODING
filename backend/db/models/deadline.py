"""
===============================================================================
Modèle : Deadline
===============================================================================
Objectif :
    Table deadlines : examens et rendus d'une matière (bloc 2 du sujet).

Responsabilités :
    - Une échéance porte sur une matière entière : toutes ses sessions doivent
      se terminer avant elle.
    - due_date est une date locale (« 2026-11-27 ») ; une session ne peut pas
      finir après minuit au début de ce jour, dans le fuseau de l'étudiant.
    - weight de 0 à 100 : avec la proximité de la date, il donne la priorité
      d'une matière dans le planning.
    - user_id est porté directement, en plus du chemin par la matière : RG4
      impose que les deux mènent au même utilisateur, ce que le service vérifie.

Lot :
    C (planification)
===============================================================================
"""

from datetime import date

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TimestampMixin, enum_type
from backend.domain.enums import DeadlineType

# =============================================================================
# API publique
# =============================================================================


class Deadline(TimestampMixin, Base):
    """Échéance : examen ou rendu, avec sa date et son poids."""

    __tablename__ = "deadlines"
    __table_args__ = (CheckConstraint("weight BETWEEN 0 AND 100", name="weight_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    type: Mapped[DeadlineType] = mapped_column(enum_type(DeadlineType, "type"))
    due_date: Mapped[date]
    weight: Mapped[int]
