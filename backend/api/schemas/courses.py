"""
===============================================================================
Schémas : courses
===============================================================================
Objectif :
    Ce qui entre et sort des routes /api/v1/courses (P0-02).

Responsabilités :
    - Nom nettoyé et borné, couleur #RRGGBB, difficulté de 1 à 5.
    - Refuser tout champ inconnu (user_id compris : il vient du jeton).

Lot :
    A (socle et sécurité)
===============================================================================
"""

from pydantic import BaseModel, ConfigDict, Field

from backend.api.schemas.common import HexColor, SingleLineText
from backend.db.models.course import DEFAULT_DIFFICULTY

# =============================================================================
# API publique
# =============================================================================


class CourseCreate(BaseModel):
    """Création d'une matière."""

    model_config = ConfigDict(extra="forbid")

    name: SingleLineText[100]
    color: HexColor
    difficulty: int = Field(default=DEFAULT_DIFFICULTY, ge=1, le=5)


class CourseUpdate(BaseModel):
    """Modification partielle d'une matière : seuls les champs envoyés changent."""

    model_config = ConfigDict(extra="forbid")

    name: SingleLineText[100] | None = None
    color: HexColor | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)


class CourseRead(BaseModel):
    """Matière renvoyée par l'API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str
    difficulty: int
