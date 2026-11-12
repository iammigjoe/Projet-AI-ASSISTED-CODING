"""
===============================================================================
Application : main
===============================================================================
Objectif :
    Construire l'application FastAPI : middlewares, traduction des erreurs,
    routers.

Responsabilités :
    - CORS restreint aux origines de MYPLAN_CORS_ORIGINS.
    - En-têtes de sécurité sur toutes les réponses.
    - Une ligne par router, triées par ordre alphabétique (repartition_taches.md §5).

Exemple d'utilisation :
    uvicorn backend.main:app --reload

Lot :
    A (socle et sécurité)
===============================================================================
"""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.api.errors import register_error_handlers
from backend.core.config import get_settings

# =============================================================================
# Constantes
# =============================================================================

API_PREFIX = "/api/v1"

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    # Les réponses contiennent des données personnelles : jamais de cache partagé.
    "Cache-Control": "no-store",
}

# =============================================================================
# API publique
# =============================================================================


def create_app() -> FastAPI:
    """Construit l'application.

    Returns:
        L'application, prête à être servie par uvicorn ou testée par TestClient.
    """
    settings = get_settings()
    app = FastAPI(
        title="MyPlan API",
        version="0.1.0",
        # La documentation interactive n'est pas exposée en production.
        docs_url=None if settings.env == "prod" else "/docs",
        redoc_url=None,
        openapi_url=None if settings.env == "prod" else "/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        # Jeton Bearer dans l'en-tête Authorization, pas de cookie : pas de credentials.
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.middleware("http")(_add_security_headers)
    register_error_handlers(app)

    # --- Routers : une ligne par router, ordre alphabétique -----------------
    # app.include_router(courses.router, prefix=API_PREFIX)

    return app


# =============================================================================
# Fonctions internes
# =============================================================================


async def _add_security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


# =============================================================================
# Application
# =============================================================================

app = create_app()
