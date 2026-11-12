"""
===============================================================================
Router : /auth
===============================================================================
Objectif :
    Exposer l'inscription, la connexion, le renouvellement des jetons et la
    déconnexion (P0-01).

Endpoints :
    POST  /auth/register  Crée le compte unique (fermé ensuite : 403)
    POST  /auth/login     Échange email et mot de passe contre des jetons
    POST  /auth/refresh   Échange un jeton de rafraîchissement contre une nouvelle paire
    POST  /auth/logout    Révoque tous les jetons du compte
    GET   /auth/me        Renvoie le compte connecté

Sécurité :
    register, login et refresh sont publics, et limités par IP (rate_limit.py) ;
    login applique en plus l'attente exponentielle après échecs. logout et me
    exigent un jeton d'accès valide.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from backend.api.deps import CurrentClock, CurrentUser, DbSession
from backend.api.rate_limit import LOGIN_LIMIT, REGISTER_LIMIT, limiter
from backend.api.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPairRead,
    UserRead,
)
from backend.core.login_throttle import LoginThrottle, get_login_throttle
from backend.services.auth_service import AuthService, AuthTokens

# =============================================================================
# Constantes
# =============================================================================

router = APIRouter(prefix="/auth", tags=["auth"])

Throttle = Annotated[LoginThrottle, Depends(get_login_throttle)]

# =============================================================================
# API publique
# =============================================================================


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit(REGISTER_LIMIT)
def register(
    request: Request,
    payload: RegisterRequest,
    session: DbSession,
    clock: CurrentClock,
    throttle: Throttle,
) -> TokenPairRead:
    """Crée le compte unique et connecte l'étudiant."""
    tokens = AuthService(session, clock, throttle).register(
        payload.email, payload.password, payload.timezone
    )
    return _token_pair(tokens)


@router.post("/login")
@limiter.limit(LOGIN_LIMIT)
def login(
    request: Request,
    payload: LoginRequest,
    session: DbSession,
    clock: CurrentClock,
    throttle: Throttle,
) -> TokenPairRead:
    """Connecte l'étudiant avec son email et son mot de passe."""
    tokens = AuthService(session, clock, throttle).login(
        payload.email, payload.password, _client_ip(request)
    )
    return _token_pair(tokens)


@router.post("/refresh")
@limiter.limit(LOGIN_LIMIT)
def refresh(
    request: Request,
    payload: RefreshRequest,
    session: DbSession,
    clock: CurrentClock,
    throttle: Throttle,
) -> TokenPairRead:
    """Renouvelle les jetons avant l'expiration du jeton d'accès."""
    tokens = AuthService(session, clock, throttle).refresh(payload.refresh_token)
    return _token_pair(tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    user: CurrentUser, session: DbSession, clock: CurrentClock, throttle: Throttle
) -> Response:
    """Déconnecte l'étudiant sur tous ses appareils."""
    AuthService(session, clock, throttle).logout(user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me")
def me(user: CurrentUser) -> UserRead:
    """Renvoie le compte connecté."""
    return UserRead.model_validate(user)


# =============================================================================
# Fonctions internes
# =============================================================================


def _token_pair(tokens: AuthTokens) -> TokenPairRead:
    return TokenPairRead(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
