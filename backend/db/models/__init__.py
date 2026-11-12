"""
===============================================================================
Modèles : backend.db.models
===============================================================================
Objectif :
    Importer chaque modèle, pour que toutes les tables soient enregistrées dans
    Base.metadata (Alembic, création des tables de test).

Lot :
    A (socle et sécurité) ; chaque lot ajoute ici l'import de ses modèles.
===============================================================================
"""

# =============================================================================
# Imports des modèles, un par ligne, triés
# =============================================================================

from backend.db.models.availability import Availability, AvailabilityException
from backend.db.models.chapter import Chapter
from backend.db.models.course import Course
from backend.db.models.deadline import Deadline, deadline_chapters
from backend.db.models.document import Document
from backend.db.models.plan import Plan
from backend.db.models.study_session import StudySession
from backend.db.models.user import User
from backend.db.models.user_settings import UserSettings

__all__ = [
    "Availability",
    "AvailabilityException",
    "Chapter",
    "Course",
    "Deadline",
    "Document",
    "Plan",
    "StudySession",
    "User",
    "UserSettings",
    "deadline_chapters",
]
