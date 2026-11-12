"""
===============================================================================
Service : SettingsService
===============================================================================
Objectif :
    Lire et modifier le profil d'étude de l'utilisateur (P0-08).

Responsabilités :
    - Toujours renvoyer un profil : il est créé avec le compte
      (UserRepository.create).
    - Ne modifier que les champs fournis.

Dépendances :
    Session SQLAlchemy

Utilisé par :
    backend/api/routers/settings.py ; les lots B et C lisent le profil pour
    l'estimation et le planificateur.

Exemple d'utilisation :
    settings = SettingsService(session).get(user.id)

Lot :
    A (socle et sécurité)
===============================================================================
"""

from typing import Any

from sqlalchemy.orm import Session

from backend.db.models import UserSettings

# =============================================================================
# Constantes
# =============================================================================

_EDITABLE_FIELDS = frozenset(
    {"reading_speed_wpm", "session_minutes", "break_min", "mastery_goal", "retention_threshold"}
)

# =============================================================================
# API publique
# =============================================================================


class SettingsService:
    """Cas d'usage du profil d'étude."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: int) -> UserSettings:
        """Renvoie le profil d'étude de l'utilisateur.

        Raises:
            LookupError: Si le profil manque, ce qui signale une donnée corrompue :
                il est créé avec le compte.
        """
        settings = self._session.get(UserSettings, user_id)
        if settings is None:
            raise LookupError(f"Profil d'étude absent pour l'utilisateur {user_id}")
        return settings

    def update(self, user_id: int, changes: dict[str, Any]) -> UserSettings:
        """Applique les champs fournis au profil.

        Args:
            user_id: Utilisateur connecté.
            changes: Champs à modifier, déjà validés par SettingsUpdate ; un
                champ absent reste inchangé.

        Raises:
            ValueError: Si un champ n'est pas modifiable.
        """
        unknown = set(changes) - _EDITABLE_FIELDS
        if unknown:
            raise ValueError(f"Champs non modifiables : {sorted(unknown)}")

        settings = self.get(user_id)
        for field, value in changes.items():
            setattr(settings, field, value)
        self._session.commit()
        return settings
