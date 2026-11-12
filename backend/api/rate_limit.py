"""
===============================================================================
Module : rate_limit
===============================================================================
Objectif :
    Limiter le nombre de requêtes par adresse IP, contre la force brute et
    l'épuisement du serveur (Spec §4 : rate limiting sur connexion et upload).

Responsabilités :
    - Une limite par défaut sur toute l'API (DEFAULT_LIMIT).
    - Des limites plus strictes, à poser par décorateur sur les routes
      sensibles : connexion, inscription, envoi de fichier.
    - Répondre 429 RATE_LIMITED au format commun, avec Retry-After.

Utilisé par :
    backend.main (middleware et gestion du 429) ; les routers de connexion,
    d'inscription (lot A) et d'upload (lot B), par décorateur.

Exemple d'utilisation :
    @router.post("/auth/login")
    @limiter.limit(LOGIN_LIMIT)
    def login(request: Request, ...): ...   # « request » est obligatoire

Notes :
    - Stockage en mémoire : suffisant pour le serveur unique du MVP.
    - Derrière un reverse proxy, l'adresse vue est celle du proxy : il faudra
      alors lancer uvicorn avec --proxy-headers et n'accepter que ce proxy.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.api.errors import ErrorCode, error_body

# =============================================================================
# Constantes
# =============================================================================

DEFAULT_LIMIT = "120/minute"
LOGIN_LIMIT = "10/minute"
REGISTER_LIMIT = "5/hour"
UPLOAD_LIMIT = "30/hour"

# =============================================================================
# API publique
# =============================================================================

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[DEFAULT_LIMIT],
    storage_uri="memory://",
)


async def handle_rate_limit_exceeded(_request: Request, error: RateLimitExceeded) -> JSONResponse:
    """Répond 429 au format commun, en indiquant quand réessayer."""
    retry_after = error.limit.limit.get_expiry()
    return JSONResponse(
        error_body(
            ErrorCode.RATE_LIMITED,
            "Trop de requêtes. Réessayez dans quelques instants.",
            {"retry_after_seconds": retry_after},
        ),
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        headers={"Retry-After": str(retry_after)},
    )
