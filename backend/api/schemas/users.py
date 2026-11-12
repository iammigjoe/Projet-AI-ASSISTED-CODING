"""
===============================================================================
Schémas : users
===============================================================================
Objectif :
    Ce qui entre et sort de /api/v1/settings : le profil d'étude (P0-08).

Responsabilités :
    - Mêmes bornes que la base (user_settings), pour répondre 422 avec un
      message clair au lieu d'une erreur d'intégrité.
    - Les préférences de notification (P2-07) ne sont pas encore exposées.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from pydantic import BaseModel, ConfigDict, Field

from backend.domain.enums import MasteryGoal

# =============================================================================
# API publique
# =============================================================================


class SettingsRead(BaseModel):
    """Profil d'étude de l'utilisateur connecté."""

    model_config = ConfigDict(from_attributes=True)

    reading_speed_wpm: int
    max_session_min: int
    break_min: int
    mastery_goal: MasteryGoal
    retention_threshold: float


class SettingsUpdate(BaseModel):
    """Modification partielle du profil : seuls les champs envoyés changent."""

    model_config = ConfigDict(extra="forbid")

    reading_speed_wpm: int | None = Field(default=None, ge=50, le=1000)
    max_session_min: int | None = Field(default=None, ge=15, le=240)
    break_min: int | None = Field(default=None, ge=0, le=120)
    mastery_goal: MasteryGoal | None = None
    retention_threshold: float | None = Field(default=None, ge=0.5, le=0.95)
