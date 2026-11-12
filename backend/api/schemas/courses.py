"""
===============================================================================
Schémas : courses
===============================================================================
Objectif :
    Ce qui entre et sort des routes /courses (bloc 1 du sujet, P0-02).

Responsabilités :
    - Renvoyer l'avancement de chaque matière en heures et en pourcentage.
    - Modification : nom nettoyé et borné, couleur #RRGGBB, difficulté de 1 à 5 ;
      tout champ inconnu est refusé (user_id compris : il vient du jeton).
    - La création passe par POST /courses avec un fichier (lot B, import).

Lot :
    A (socle et sécurité)
===============================================================================
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.api.schemas.common import HexColor, SingleLineText

# =============================================================================
# API publique
# =============================================================================


class CourseUpdate(BaseModel):
    """Modification partielle d'une matière : seuls les champs envoyés changent."""

    model_config = ConfigDict(extra="forbid")

    name: SingleLineText[100] | None = None
    color: HexColor | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)


class CourseRead(BaseModel):
    """Matière et son avancement (contrat : GET /courses).

    Champs du contrat : id, name, hours_total, hours_done, progress.
    Extensions : color, difficulty.
    """

    id: int
    name: str
    hours_total: float = Field(description="Charge estimée des chapitres, en heures.")
    hours_done: float = Field(description="Temps des sessions faites, en heures.")
    progress: float = Field(description="hours_done / hours_total, en pourcentage de 0 à 100.")
    color: str
    difficulty: int

    @classmethod
    def from_minutes(cls, course: Any, minutes_total: int, minutes_done: int) -> "CourseRead":
        """Construit la réponse à partir d'une matière et de ses minutes.

        Args:
            course: Matière (id, name, color, difficulty).
            minutes_total: Charge estimée de ses chapitres.
            minutes_done: Durée de ses sessions faites.
        """
        progress = (
            min(100.0, round(100 * minutes_done / minutes_total, 1)) if minutes_total else 0.0
        )
        return cls(
            id=course.id,
            name=course.name,
            hours_total=round(minutes_total / 60, 1),
            hours_done=round(minutes_done / 60, 1),
            progress=progress,
            color=course.color,
            difficulty=course.difficulty,
        )
