"""
===============================================================================
Modèle : Course
===============================================================================
Objectif :
    Table courses : une matière de l'étudiant (P0-02).

Responsabilités :
    - Seul lien de propriété des documents et chapitres : tout ce qui descend
      d'une matière appartient à son utilisateur.
    - Nom unique par utilisateur, couleur #RRGGBB, difficulté de 1 à 5.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TimestampMixin

# =============================================================================
# Constantes
# =============================================================================

DEFAULT_DIFFICULTY = 3
# SQLite n'a pas d'expression régulière : GLOB vérifie « # » suivi de 6 chiffres hexadécimaux.
_HEX = "[0-9A-Fa-f]"
COLOR_GLOB = "#" + _HEX * 6

# =============================================================================
# API publique
# =============================================================================


class Course(TimestampMixin, Base):
    """Matière : nom, couleur d'affichage, difficulté perçue."""

    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("user_id", "name"),
        CheckConstraint("length(name) BETWEEN 1 AND 100", name="name_length"),
        CheckConstraint(f"color GLOB '{COLOR_GLOB}'", name="color_hex"),
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="difficulty_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(7))
    difficulty: Mapped[int] = mapped_column(default=DEFAULT_DIFFICULTY)
