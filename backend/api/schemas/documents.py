"""
===============================================================================
Schémas : documents (import de cours)
===============================================================================
Objectif :
    Réponse de POST /courses (contrat StudyPlan, bloc 1).

Responsabilités :
    - Renvoyer id, name, chapters[{id, title, hours}], hours_total.
    - hours à une décimale (heures), jamais les minutes internes.

Lot :
    B (ingestion)
===============================================================================
"""

from pydantic import BaseModel, Field

# =============================================================================
# API publique
# =============================================================================


class ChapterImportRead(BaseModel):
    """Chapitre créé par l'import d'un fichier."""

    id: int
    title: str
    hours: float = Field(description="Charge estimée du chapitre, en heures.")


class CourseImportRead(BaseModel):
    """Matière créée par POST /courses avec un fichier."""

    id: int
    name: str
    chapters: list[ChapterImportRead]
    hours_total: float = Field(description="Somme des heures des chapitres.")
