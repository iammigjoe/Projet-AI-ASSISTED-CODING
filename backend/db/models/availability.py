"""
===============================================================================
Modèle : Availability
===============================================================================
Objectif :
    Tables availabilities et availability_exceptions : créneaux hebdomadaires
    récurrents et exceptions ponctuelles (P0-09).

Responsabilités :
    - Stocker les heures en heure locale de l'étudiant (« HH:MM »), pas en UTC :
      un créneau ne doit pas se décaler au changement d'heure
      (modele_donnees.md §5).
    - Refuser un créneau qui finit avant de commencer.

Lot :
    C (planification)
===============================================================================
"""

from datetime import date, time

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TimestampMixin, enum_type
from backend.db.types import LocalTime
from backend.domain.enums import ExceptionKind

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
        CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="valid_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    weekday: Mapped[int]
    starts_local: Mapped[time] = mapped_column(LocalTime)
    ends_local: Mapped[time] = mapped_column(LocalTime)
    valid_from: Mapped[date]
    valid_to: Mapped[date | None]


class AvailabilityException(TimestampMixin, Base):
    """Jour bloqué ou créneau ajouté, à une date précise."""

    __tablename__ = "availability_exceptions"
    __table_args__ = (
        # Les deux heures sont renseignées ensemble, ou aucune (journée entière).
        CheckConstraint("(starts_local IS NULL) = (ends_local IS NULL)", name="times_both_or_none"),
        CheckConstraint(
            "starts_local IS NULL OR ends_local > starts_local", name="ends_after_starts"
        ),
        # Une journée entière ne peut être que bloquée : un créneau ajouté a des heures.
        CheckConstraint("starts_local IS NOT NULL OR kind = 'blocked'", name="whole_day_blocked"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[date]
    starts_local: Mapped[time | None] = mapped_column(LocalTime)
    ends_local: Mapped[time | None] = mapped_column(LocalTime)
    kind: Mapped[ExceptionKind] = mapped_column(enum_type(ExceptionKind, "kind"))
