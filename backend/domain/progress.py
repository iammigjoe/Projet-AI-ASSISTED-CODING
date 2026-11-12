"""
===============================================================================
Domaine : progress
===============================================================================
Objectif :
    Calculer les minutes d'étude terminées par chapitre, tous plannings confondus.

Pur :
    Aucun accès à la base, au réseau ou à l'horloge.

Lot :
    D (agenda et suivi)
===============================================================================
"""

from collections.abc import Iterable
from dataclasses import dataclass

# =============================================================================
# API publique
# =============================================================================


@dataclass(frozen=True)
class ChapterProgress:
    """Durée totale des sessions terminées pour un chapitre."""

    chapter_id: int
    completed_minutes: float


def calculate_progress(
    chapter_ids: Iterable[int],
    completed_sessions: Iterable[tuple[int, int]],
) -> tuple[ChapterProgress, ...]:
    """Agrège les durées des sessions faites, en conservant les chapitres à zéro.

    Args:
        chapter_ids: Chapitres appartenant à l'utilisateur.
        completed_sessions: Paires (chapter_id, durée en secondes) des sessions faites.

    Returns:
        Une entrée triée par identifiant de chapitre, exprimée en minutes.
    """
    completed_seconds = dict.fromkeys(chapter_ids, 0)
    for chapter_id, duration_seconds in completed_sessions:
        if chapter_id in completed_seconds:
            completed_seconds[chapter_id] += duration_seconds

    return tuple(
        ChapterProgress(chapter_id, seconds / 60)
        for chapter_id, seconds in sorted(completed_seconds.items())
    )
