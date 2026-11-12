"""
===============================================================================
Tests : estimation
===============================================================================
Objectif :
    Vérifier la formule du contrat (min. 1 h) et la priorité de l'override.

Lot :
    B (ingestion)
===============================================================================
"""

import pytest

from backend.domain.enums import MasteryGoal
from backend.domain.estimation import (
    StudySettings,
    effective_minutes,
    estimate_hours,
    estimate_minutes,
    minutes_to_hours,
)


def test_estimate_hours_applies_minimum_one_hour() -> None:
    settings = StudySettings(reading_speed_wpm=200, mastery_goal=MasteryGoal.STANDARD)

    # 400 mots / (200 × 60) = 0,033 h → plancher 1,0 h
    assert estimate_hours(400, settings, difficulty=3) == 1.0
    assert estimate_minutes(400, settings, difficulty=3) == 60


def test_estimate_minutes_zero_words_returns_zero() -> None:
    settings = StudySettings(reading_speed_wpm=200)

    assert estimate_minutes(0, settings, difficulty=3) == 0
    assert estimate_hours(0, settings, difficulty=3) == 0.0


def test_estimate_hours_large_chapter() -> None:
    settings = StudySettings(reading_speed_wpm=200)

    # 24 000 mots / (200 × 60) = 2,0 h
    assert estimate_hours(24_000, settings, difficulty=3) == 2.0
    assert estimate_minutes(24_000, settings, difficulty=3) == 120


def test_estimate_minutes_applies_difficulty_and_mastery() -> None:
    settings = StudySettings(reading_speed_wpm=200, mastery_goal=MasteryGoal.MASTERY)

    # 24 000 / (200 × 60) × 1.5 × 1.3 = 3.9 → 3.9 h → 234 min
    assert estimate_hours(24_000, settings, difficulty=5) == 3.9
    assert estimate_minutes(24_000, settings, difficulty=5) == 234


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


def test_minutes_to_hours_one_decimal() -> None:
    assert minutes_to_hours(60) == 1.0
    assert minutes_to_hours(90) == 1.5
