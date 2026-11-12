"""
===============================================================================
Modèle : Availability
===============================================================================
Objectif :
    Table availabilities : créneaux hebdomadaires récurrents de l'étudiant
    (bloc 2 du sujet, PUT /availability).

Responsabilités :
    - Stocker les heures en heure locale de l'étudiant (« HH:MM »), pas en UTC :
      un créneau ne doit pas se décaler au changement d'heure
      (modele_donnees.md §5).
    - Refuser un créneau qui finit avant de commencer.

Lot :
    C (planification)
===============================================================================
"""

from datetime import time

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TimestampMixin
from backend.db.types import LocalTime

# =============================================================================
# API publique
# =============================================================================


class Availability(TimestampMixin, Base):
    """Créneau récurrent : un jour de la semaine, une heure de début et de fin."""

    __tablename__ = "availabilities"
    __table_args__ = (
        # 0 = lundi, comme datetime.weekday().
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_range"),
        # Le texte « HH:MM » se compare comme l'heure qu'il représente.
        CheckConstraint("ends_local > starts_local", name="ends_after_starts"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    weekday: Mapped[int]
    starts_local: Mapped[time] = mapped_column(LocalTime)
    ends_local: Mapped[time] = mapped_column(LocalTime)
