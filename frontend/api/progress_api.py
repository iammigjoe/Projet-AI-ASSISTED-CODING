"""
===============================================================================
Client HTTP : progress
===============================================================================
Objectif :
    Appeler les endpoints de suivi des sessions et de progression.

Lot :
    D (agenda et suivi)
===============================================================================
"""

from typing import Any, Literal

from frontend.api.base import get_client

StudySessionStatus = Literal["done", "missed"]


def update_study_session(study_session_id: int, status: StudySessionStatus) -> dict[str, Any]:
    """Marque une session comme faite ou non faite."""
    return get_client().patch(f"/study-sessions/{study_session_id}", json={"status": status})


def get_progress() -> list[dict[str, Any]]:
    """Renvoie l'avancement par chapitre."""
    return get_client().get("/progress")
