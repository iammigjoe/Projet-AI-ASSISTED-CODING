"""
===============================================================================
Module : deps
===============================================================================
Objectif :
    Dépendances FastAPI communes : session de base de données, utilisateur
    connecté, horloge.

Responsabilités :
    - Ouvrir une session par requête, l'annuler en cas d'erreur, la fermer
      toujours.
    - Authentifier chaque requête protégée par un jeton d'accès Bearer ; le
      user_id vient toujours d'ici, jamais du corps ni des paramètres (Spec §4).
    - Répondre 401 UNAUTHORIZED sans dire pourquoi le jeton est refusé.

Utilisé par :
    Tous les routers.

Exemple d'utilisation :
    @router.get("/courses")
    def list_courses(user: CurrentUser, session: DbSession) -> list[CourseRead]: ...

Lot :
    A (socle et sécurité)
===============================================================================
"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.api.errors import ApiError, ErrorCode
from backend.core.clock import Clock, get_clock
from backend.core.security import InvalidTokenError, TokenType, decode_token
from backend.db.models import User
from backend.db.session import get_session_factory
from backend.repositories.user_repository import UserRepository

# =============================================================================
# Constantes
# =============================================================================

# auto_error=False : l'absence de jeton passe par notre format d'erreur, pas
# par la réponse par défaut de FastAPI.
_bearer = HTTPBearer(auto_error=False)

# =============================================================================
# API publique
# =============================================================================


def get_db() -> Iterator[Session]:
    """Ouvre une session pour la durée de la requête.

    Les services valident eux-mêmes leurs transactions ; ici, tout ce qui n'a
    pas été validé est annulé, et la session est toujours fermée.
    """
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """Authentifie la requête et renvoie l'utilisateur connecté.

    Raises:
        ApiError: 401 UNAUTHORIZED si le jeton est absent, invalide, expiré, de
            type « refresh », révoqué, ou si le compte n'existe plus.
    """
    if credentials is None:
        raise _unauthorized()
    try:
        claims = decode_token(credentials.credentials, TokenType.ACCESS)
    except InvalidTokenError:
        raise _unauthorized() from None

    user = UserRepository(session).get_active(claims.user_id)
    # Version différente : le jeton a été révoqué (déconnexion, mot de passe changé).
    if user is None or user.token_version != claims.token_version:
        raise _unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentClock = Annotated[Clock, Depends(get_clock)]

# =============================================================================
# Fonctions internes
# =============================================================================


def _unauthorized() -> ApiError:
    return ApiError(
        status.HTTP_401_UNAUTHORIZED,
        ErrorCode.UNAUTHORIZED,
        "Connexion requise.",
        headers={"WWW-Authenticate": "Bearer"},
    )
