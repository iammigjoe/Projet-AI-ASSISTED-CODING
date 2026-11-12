"""
===============================================================================
Router : /api/v1/settings
===============================================================================
Objectif :
    Exposer le profil d'étude de l'utilisateur connecté (P0-08).

Endpoints :
    GET    /api/v1/settings  Renvoie le profil d'étude
    PATCH  /api/v1/settings  Modifie les champs envoyés

Sécurité :
    Utilisateur connecté uniquement ; le profil est toujours celui du jeton,
    il n'y a pas d'identifiant dans l'adresse.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from fastapi import APIRouter

from backend.api.deps import CurrentUser, DbSession
from backend.api.schemas.users import SettingsRead, SettingsUpdate
from backend.services.settings_service import SettingsService

# =============================================================================
# Constantes
# =============================================================================

router = APIRouter(prefix="/settings", tags=["settings"])

# =============================================================================
# API publique
# =============================================================================


@router.get("")
def get_settings(user: CurrentUser, session: DbSession) -> SettingsRead:
    """Renvoie le profil d'étude de l'étudiant."""
    return SettingsRead.model_validate(SettingsService(session).get(user.id))


@router.patch("")
def update_settings(payload: SettingsUpdate, user: CurrentUser, session: DbSession) -> SettingsRead:
    """Modifie les champs envoyés du profil d'étude."""
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    return SettingsRead.model_validate(SettingsService(session).update(user.id, changes))
