"""
===============================================================================
Tests : estimation
===============================================================================
Objectif :
    Vérifier la formule P0-07, le cas zéro mot et la priorité de l'override.

Lot :
    B (ingestion)
===============================================================================
"""

import pytest

from backend.domain.enums import MasteryGoal
from backend.domain.estimation import (
    StudySettings,
    effective_minutes,
    estimate_minutes,
)


def test_estimate_minutes_standard_difficulty_three() -> None:
    settings = StudySettings(reading_speed_wpm=200, mastery_goal=MasteryGoal.STANDARD)

    # 400 mots / 200 wpm × 1.0 × 1.0 = 2 minutes
    assert estimate_minutes(400, settings, difficulty=3) == 2


def test_estimate_minutes_zero_words_returns_zero() -> None:
    settings = StudySettings(reading_speed_wpm=200)

    assert estimate_minutes(0, settings, difficulty=3) == 0


def test_estimate_minutes_rounds_up() -> None:
    settings = StudySettings(reading_speed_wpm=200)

    # 1 mot / 200 × 1.0 = 0.005 → ceil → 1
    assert estimate_minutes(1, settings, difficulty=3) == 1


def test_estimate_minutes_applies_difficulty_and_mastery() -> None:
    settings = StudySettings(reading_speed_wpm=200, mastery_goal=MasteryGoal.MASTERY)

    # 200 / 200 × 1.5 × 1.3 = 1.95 → 2
    assert estimate_minutes(200, settings, difficulty=5) == 2


def test_estimate_minutes_rejects_invalid_difficulty() -> None:
    settings = StudySettings(reading_speed_wpm=200)

    with pytest.raises(ValueError):
        estimate_minutes(100, settings, difficulty=9)


def test_effective_minutes_prefers_override() -> None:
    assert effective_minutes(30, 45) == 45
    assert effective_minutes(30, None) == 30


def test_effective_minutes_rejects_non_positive_override() -> None:
    with pytest.raises(ValueError):
        effective_minutes(30, 0)
