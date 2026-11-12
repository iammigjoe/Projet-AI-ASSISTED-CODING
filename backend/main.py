"""
===============================================================================
Application : main
===============================================================================
Objectif :
    Construire l'application FastAPI : protections, traduction des erreurs,
    routers.

Responsabilités :
    - Empiler les protections dans l'ordre où elles doivent agir (voir
      create_app) : en-têtes de sécurité, contrôle de Host, taille des
      requêtes, CORS, limitation du débit.
    - Ne pas exposer la documentation interactive en production.
    - Une ligne par router, triées par ordre alphabétique (repartition_taches.md §5).

Exemple d'utilisation :
    uvicorn backend.main:app --reload

Lot :
    A (socle et sécurité)
===============================================================================
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.api.errors import register_error_handlers
from backend.api.middleware import (
    BodySizeLimitMiddleware,
    HostCheckMiddleware,
    SecurityHeadersMiddleware,
)
from backend.api.rate_limit import handle_rate_limit_exceeded, limiter
from backend.api.routers import auth, courses, settings
from backend.core.config import get_settings

# =============================================================================
# Constantes
# =============================================================================

# Routes du contrat sans préfixe : POST /courses, GET /plan.ics… (STUDYPLAN_SPEC §3).
API_PREFIX = ""

# =============================================================================
# API publique
# =============================================================================


def create_app() -> FastAPI:
    """Construit l'application.

    Returns:
        L'application, prête à être servie par uvicorn ou testée par TestClient.
    """
    config = get_settings()
    is_prod = config.env == "prod"
    app = FastAPI(
        title="MyPlan API",
        version="0.1.0",
        docs_url=None if is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if is_prod else "/openapi.json",
    )

    # Starlette exécute en premier le dernier middleware ajouté : la liste
    # ci-dessous va donc de l'intérieur (près des routes) vers l'extérieur.
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origin_list,
        # Jeton Bearer dans l'en-tête Authorization, pas de cookie : pas de credentials.
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=config.max_request_bytes)
    app.add_middleware(HostCheckMiddleware, allowed_hosts=config.allowed_host_list)
    # Le plus à l'extérieur : même un refus 400 ou 413 porte les en-têtes de sécurité.
    app.add_middleware(SecurityHeadersMiddleware, hsts=is_prod)

    register_error_handlers(app)
    app.add_exception_handler(RateLimitExceeded, handle_rate_limit_exceeded)  # type: ignore[arg-type]

    # --- Routers : une ligne par router, ordre alphabétique -----------------
    app.include_router(auth.router, prefix=API_PREFIX)
    app.include_router(courses.router, prefix=API_PREFIX)
    app.include_router(settings.router, prefix=API_PREFIX)

    return app


# =============================================================================
# Application
# =============================================================================

app = create_app()
