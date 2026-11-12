"""
===============================================================================
Tests : progress
===============================================================================
Objectif :
    Vérifier l'agrégation pure de la progression par chapitre.

Lot :
    D (agenda et suivi)
===============================================================================
"""

from backend.domain.progress import ChapterProgress, calculate_progress


def test_progress_sums_completed_sessions_across_plans_and_keeps_empty_chapters():
    progress = calculate_progress(
        [2, 1, 3],
        [(1, 2700), (1, 900), (2, 1800), (99, 3600)],
    )

    assert progress == (
        ChapterProgress(chapter_id=1, completed_minutes=60),
        ChapterProgress(chapter_id=2, completed_minutes=30),
        ChapterProgress(chapter_id=3, completed_minutes=0),
    )
