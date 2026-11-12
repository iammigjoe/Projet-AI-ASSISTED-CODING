"""
===============================================================================
Domaine : estimation
===============================================================================
Objectif :
    Estimer la charge d'étude d'un chapitre (SPEC bloc 1 / P0-07).

Responsabilités :
    - Appliquer :
      heures = max(1, mots / (vitesse_lecture × 60) × coeff_difficulté
                   × coeff_objectif)
    - Stocker en minutes entières (estimated_min), minimum 60 pour un
      chapitre non vide.
    - Ne jamais écraser une durée saisie à la main : effective_minutes
      préfère estimated_min_override.

Pur :
    Ni base, ni réseau, ni horloge.

Utilisé par :
    IngestionService

Exemple d'utilisation :
    minutes = estimate_minutes(400, StudySettings(200, MasteryGoal.STANDARD), 3)

Lot :
    B (ingestion)
===============================================================================
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from backend.domain.enums import MasteryGoal

# =============================================================================
# Constantes
# =============================================================================

DIFFICULTY_COEFFICIENTS: dict[int, float] = {
    1: 0.8,
    2: 0.9,
    3: 1.0,
    4: 1.2,
    5: 1.5,
}

MASTERY_COEFFICIENTS: dict[MasteryGoal, float] = {
    MasteryGoal.DISCOVERY: 0.8,
    MasteryGoal.STANDARD: 1.0,
    MasteryGoal.MASTERY: 1.3,
}

MIN_CHAPTER_HOURS = 1.0


# =============================================================================
# Types
# =============================================================================


@dataclass(frozen=True)
class StudySettings:
    """Profil d'étude pour l'estimation.

    Attributes:
        reading_speed_wpm: Mots par minute, strictement positif.
        mastery_goal: Objectif de maîtrise → coefficient d'objectif.
    """

    reading_speed_wpm: int
    mastery_goal: MasteryGoal = MasteryGoal.STANDARD


# =============================================================================
# API publique
# =============================================================================


def estimate_hours(
    word_count: int,
    settings: StudySettings,
    difficulty: int,
) -> float:
    """Estime la charge d'un chapitre en heures (contrat POST /courses).

    Args:
        word_count: Nombre de mots du chapitre, positif ou nul.
        settings: Profil d'étude, dont la vitesse de lecture et l'objectif.
        difficulty: Difficulté perçue de la matière, de 1 à 5.

    Returns:
        Heures à une décimale ; 0 pour un chapitre vide ; au moins 1.0 sinon.

    Raises:
        ValueError: Si difficulty n'est pas entre 1 et 5, si la vitesse
            n'est pas > 0, ou si word_count est négatif.
    """
    raw = _raw_hours(word_count, settings, difficulty)
    if word_count == 0:
        return 0.0
    return round(max(MIN_CHAPTER_HOURS, raw), 1)


def estimate_minutes(
    word_count: int,
    settings: StudySettings,
    difficulty: int,
) -> int:
    """Estime la durée d'étude d'un chapitre, en minutes entières.

    Dérive de estimate_hours : minimum 60 minutes pour un chapitre non vide.

    Args:
        word_count: Nombre de mots du chapitre, positif ou nul.
        settings: Profil d'étude, dont la vitesse de lecture et l'objectif.
        difficulty: Difficulté perçue de la matière, de 1 à 5.

    Returns:
        La durée estimée ; 0 pour un chapitre vide.
    """
    hours = estimate_hours(word_count, settings, difficulty)
    if hours == 0:
        return 0
    return max(60, math.ceil(hours * 60))


def effective_minutes(
    estimated_min: int,
    estimated_min_override: int | None,
) -> int:
    """Durée utilisée par le planificateur (RG5).

    Args:
        estimated_min: Valeur calculée par estimate_minutes.
        estimated_min_override: Correction manuelle ; prioritaire si renseignée.

    Returns:
        L'override s'il est > 0, sinon estimated_min.

    Raises:
        ValueError: Si l'override est fourni mais ≤ 0.
    """
    if estimated_min_override is None:
        return estimated_min
    if estimated_min_override <= 0:
        raise ValueError("estimated_min_override doit être > 0")
    return estimated_min_override


def minutes_to_hours(minutes: int) -> float:
    """Convertit des minutes en heures à une décimale (réponse API)."""
    return round(minutes / 60, 1)


# =============================================================================
# Fonctions internes
# =============================================================================


def _raw_hours(word_count: int, settings: StudySettings, difficulty: int) -> float:
    if word_count < 0:
        raise ValueError("word_count doit être ≥ 0")
    if settings.reading_speed_wpm <= 0:
        raise ValueError("reading_speed_wpm doit être > 0")
    if difficulty not in DIFFICULTY_COEFFICIENTS:
        raise ValueError("difficulty doit être entre 1 et 5")
    if word_count == 0:
        return 0.0
    return (
        (word_count / (settings.reading_speed_wpm * 60))
        * DIFFICULTY_COEFFICIENTS[difficulty]
        * MASTERY_COEFFICIENTS[settings.mastery_goal]
    )
