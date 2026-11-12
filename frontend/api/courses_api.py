"""
===============================================================================
Client HTTP : courses_api
===============================================================================
Objectif :
    Appels aux routes /courses et /settings.

Utilisé par :
    frontend/views/courses.py, frontend/views/settings.py ; les autres lots
    pour proposer la liste des matières (documents, échéances).

Exemple d'utilisation :
    courses = courses_api.list_courses(get_client())

Lot :
    A (socle et sécurité)
===============================================================================
"""

from typing import Any

from frontend.api.base import ApiClient

# =============================================================================
# Matières
# =============================================================================


def list_courses(client: ApiClient) -> list[dict[str, Any]]:
    """Liste les matières et leur avancement (hours_total, hours_done, progress), triées par nom."""
    return client.get("/courses")


def update_course(client: ApiClient, course_id: int, **changes: Any) -> dict[str, Any]:
    """Modifie les champs fournis d'une matière (name, color, difficulty)."""
    return client.patch(f"/courses/{course_id}", json=changes)


def delete_course(client: ApiClient, course_id: int) -> None:
    """Supprime une matière et tout ce qui en dépend."""
    client.delete(f"/courses/{course_id}")


# =============================================================================
# Profil d'étude
# =============================================================================


def get_settings(client: ApiClient) -> dict[str, Any]:
    """Renvoie le profil d'étude."""
    return client.get("/settings")


def update_settings(client: ApiClient, **changes: Any) -> dict[str, Any]:
    """Modifie les champs fournis du profil d'étude."""
    return client.patch("/settings", json=changes)
