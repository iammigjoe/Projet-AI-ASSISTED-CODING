"""
===============================================================================
Client HTTP : documents_api
===============================================================================
Objectif :
    Appel à POST /courses : importer un fichier de cours (bloc 1).

Utilisé par :
    frontend/views/documents.py

Exemple d'utilisation :
    course = documents_api.import_course(get_client(), "statistics.md", contenu)

Lot :
    B (import)
===============================================================================
"""

from typing import Any

from frontend.api.base import ApiClient

# =============================================================================
# Constantes
# =============================================================================

# Type MIME annoncé à l'API ; elle vérifie de toute façon le contenu réel (magic bytes).
_MIME_TYPES = {".pdf": "application/pdf", ".md": "text/markdown"}

# =============================================================================
# API publique
# =============================================================================


def import_course(client: ApiClient, filename: str, content: bytes) -> dict[str, Any]:
    """Importe un fichier et renvoie la matière créée.

    Args:
        client: Client HTTP de la session.
        filename: Nom d'origine du fichier, affiché à l'étudiant.
        content: Contenu brut du fichier.

    Returns:
        {id, name, chapters: [{id, title, hours}], hours_total} (contrat).

    Raises:
        ApiError: Fichier refusé, illisible, trop lourd, ou matière déjà importée.
    """
    suffix = filename[filename.rfind(".") :].lower() if "." in filename else ""
    mime_type = _MIME_TYPES.get(suffix, "application/octet-stream")
    return client.post("/courses", files={"file": (filename, content, mime_type)})
