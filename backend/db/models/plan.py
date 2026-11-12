"""
===============================================================================
Modèle : Plan
===============================================================================
Objectif :
    Table plans : une version du planning d'un utilisateur (P0-11, P1-08).

Responsabilités :
    - Un planning couvre une semaine ISO (« 2026-W47 »), comme
      POST /plan/generate {week} du contrat.
    - Numéro de version unique par utilisateur.
    - Au plus un planning actif par utilisateur et par semaine, garanti par un
      index unique partiel (RG6, modele_donnees.md §5).

Lot :
    C (planification)
===============================================================================
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TimestampMixin, enum_type
from backend.db.types import UtcDateTime
from backend.domain.enums import PlanOrigin, PlanStatus

# =============================================================================
# API publique
# =============================================================================


class Plan(TimestampMixin, Base):
    """Version de planning : brouillon, active ou archivée."""

    __tablename__ = "plans"
    __table_args__ = (
        UniqueConstraint("user_id", "version"),
        CheckConstraint("version >= 1", name="version_positive"),
        # Format « AAAA-Www » : 8 caractères, semaine sur deux chiffres.
        CheckConstraint("week GLOB '[0-9][0-9][0-9][0-9]-W[0-9][0-9]'", name="week_format"),
        # RG6 : si deux activations arrivent en même temps, la seconde échoue.
        Index(
            "uq_plans_user_id_week_active",
            "user_id",
            "week",
            unique=True,
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    version: Mapped[int]
    week: Mapped[str] = mapped_column(String(8), index=True)
    status: Mapped[PlanStatus] = mapped_column(
        enum_type(PlanStatus, "status"), default=PlanStatus.DRAFT
    )
    origin: Mapped[PlanOrigin] = mapped_column(enum_type(PlanOrigin, "origin"))
    # Version dont celle-ci découle ; conservée si le parent disparaît.
    parent_plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id", ondelete="SET NULL"))
    activated_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
