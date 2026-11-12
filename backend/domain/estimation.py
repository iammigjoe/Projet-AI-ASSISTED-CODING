"""
===============================================================================
Domaine : estimation
===============================================================================
Objectif :
    Estimer la durée d'étude d'un chapitre en minutes entières (P0-07).

Responsabilités :
    - Appliquer :
      temps = (mots / vitesse_lecture) × coeff_difficulté × coeff_objectif
    - Arrondir à la minute supérieure (ceil).
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

# Difficulté 1..5 → coefficient. Valeurs provisoires du lot B, à valider
# avec l'équipe si le ressenti des étudiants diverge.
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


# =============================================================================
# Types
# =============================================================================


@dataclass(frozen=True)
class StudySettings:
    """Profil d'étude minimal pour l'estimation (en attendant les modèles A).

    Attributes:
        reading_speed_wpm: Mots par minute, strictement positif.
        mastery_goal: Objectif de maîtrise → coefficient d'objectif.
    """

    reading_speed_wpm: int
    mastery_goal: MasteryGoal = MasteryGoal.STANDARD


# =============================================================================
# API publique
# =============================================================================


def estimate_minutes(
    word_count: int,
    settings: StudySettings,
    difficulty: int,
) -> int:
    """Estime la durée d'étude d'un chapitre, en minutes entières.

    Applique (mots / vitesse de lecture) × coefficient de difficulté
    × coefficient d'objectif (P0-07), arrondi à la minute supérieure.

    Args:
        word_count: Nombre de mots du chapitre, positif ou nul.
        settings: Profil d'étude, dont la vitesse de lecture et l'objectif.
        difficulty: Difficulté perçue de la matière, de 1 à 5.

    Returns:
        La durée estimée ; 0 pour un chapitre vide.

    Raises:
        ValueError: Si difficulty n'est pas entre 1 et 5, si la vitesse
            n'est pas > 0, ou si word_count est négatif.
    """
    if word_count < 0:
        raise ValueError("word_count doit être ≥ 0")
    if word_count == 0:
        return 0
    if settings.reading_speed_wpm <= 0:
        raise ValueError("reading_speed_wpm doit être > 0")
    if difficulty not in DIFFICULTY_COEFFICIENTS:
        raise ValueError("difficulty doit être entre 1 et 5")

    minutes = (
        (word_count / settings.reading_speed_wpm)
        * DIFFICULTY_COEFFICIENTS[difficulty]
        * MASTERY_COEFFICIENTS[settings.mastery_goal]
    )
    return max(1, math.ceil(minutes))


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
