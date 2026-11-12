"""
===============================================================================
Module : errors
===============================================================================
Objectif :
    Donner à toutes les erreurs de l'API la même forme
    {"error": {"code", "message", "details"}} (conventions §6).

Responsabilités :
    - Déclarer la liste des codes d'erreur, à un seul endroit.
    - Traduire en réponse JSON : ApiError, erreurs métier, validation
      Pydantic, erreurs HTTP de Starlette, exceptions imprévues.
    - Ne jamais renvoyer de détail technique (trace, requête SQL, valeur saisie).

Utilisé par :
    backend.main (register_error_handlers), les routers et backend.api.deps.

Exemple d'utilisation :
    raise ApiError(401, ErrorCode.UNAUTHORIZED, "Connexion requise.")

Lot :
    A (socle et sécurité) ; chaque lot ajoute ses codes à la fin de sa section.
===============================================================================
"""

import logging
from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.domain.errors import (
    DomainError,
    InvalidCredentialsError,
    NotFoundError,
    RegistrationClosedError,
    TooManyLoginAttemptsError,
)

# =============================================================================
# Constantes
# =============================================================================

logger = logging.getLogger(__name__)


class ErrorCode(StrEnum):
    """Codes d'erreur publiés ; un code ne change jamais une fois publié."""

    # --- Commun (lot A) ---------------------------------------------------
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    REGISTRATION_CLOSED = "REGISTRATION_CLOSED"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    TOO_MANY_LOGIN_ATTEMPTS = "TOO_MANY_LOGIN_ATTEMPTS"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    WEAK_PASSWORD = "WEAK_PASSWORD"  # noqa: S105  # code d'erreur, pas un secret
    REQUEST_TOO_LARGE = "REQUEST_TOO_LARGE"
    INVALID_HOST = "INVALID_HOST"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    # --- Ingestion (lot B) ------------------------------------------------
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"

    # --- Planification (lot C) --------------------------------------------
    PLAN_NOT_FEASIBLE = "PLAN_NOT_FEASIBLE"

    # --- Agenda et suivi (lot D) ------------------------------------------
    GOOGLE_NOT_CONNECTED = "GOOGLE_NOT_CONNECTED"


# Codes HTTP des erreurs métier qui ne répondent pas 422.
_DOMAIN_STATUS: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    RegistrationClosedError: status.HTTP_403_FORBIDDEN,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    TooManyLoginAttemptsError: status.HTTP_429_TOO_MANY_REQUESTS,
}

# Erreurs HTTP levées par Starlette elle-même (route inconnue, méthode refusée).
_HTTP_CODES: dict[int, tuple[ErrorCode, str]] = {
    status.HTTP_401_UNAUTHORIZED: (ErrorCode.UNAUTHORIZED, "Connexion requise."),
    status.HTTP_404_NOT_FOUND: (ErrorCode.NOT_FOUND, "Ressource introuvable."),
    status.HTTP_405_METHOD_NOT_ALLOWED: (
        ErrorCode.METHOD_NOT_ALLOWED,
        "Méthode non autorisée sur cette adresse.",
    ),
    status.HTTP_413_CONTENT_TOO_LARGE: (
        ErrorCode.REQUEST_TOO_LARGE,
        "La requête dépasse la taille autorisée.",
    ),
}

# =============================================================================
# API publique
# =============================================================================


class ApiError(Exception):
    """Erreur à renvoyer telle quelle au client, avec son code HTTP."""

    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Crée l'erreur.

        Args:
            status_code: Code HTTP de la réponse.
            code: Code stable, testé par le frontend.
            message: Explication en français, affichable telle quelle.
            details: Données structurées propres au code (optionnel).
            headers: En-têtes à ajouter (WWW-Authenticate pour un 401).
        """
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        self.headers = headers


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Construit le corps JSON d'une erreur, au format des conventions §6."""
    body: dict[str, Any] = {"code": code, "message": message}
    if details:
        body["details"] = details
    return {"error": body}


def register_error_handlers(app: FastAPI) -> None:
    """Branche la traduction de toutes les erreurs sur l'application.

    Args:
        app: L'application FastAPI.
    """
    app.add_exception_handler(ApiError, _handle_api_error)  # type: ignore[arg-type]
    app.add_exception_handler(DomainError, _handle_domain_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_unexpected_error)


# =============================================================================
# Fonctions internes
# =============================================================================


async def _handle_api_error(_request: Request, error: ApiError) -> JSONResponse:
    return JSONResponse(
        error_body(error.code, error.message, error.details),
        status_code=error.status_code,
        headers=error.headers,
    )


async def _handle_domain_error(_request: Request, error: DomainError) -> JSONResponse:
    status_code = _DOMAIN_STATUS.get(type(error), status.HTTP_422_UNPROCESSABLE_CONTENT)
    headers = None
    if isinstance(error, TooManyLoginAttemptsError):
        headers = {"Retry-After": str(error.retry_after_seconds)}
    return JSONResponse(
        error_body(error.code, error.message, error.details),
        status_code=status_code,
        headers=headers,
    )


async def _handle_validation_error(
    _request: Request, error: RequestValidationError
) -> JSONResponse:
    # La valeur saisie (« input ») n'est pas renvoyée : elle peut contenir un
    # mot de passe ou un contenu que le frontend afficherait tel quel.
    fields = [
        {"location": [str(part) for part in item["loc"]], "message": item["msg"]}
        for item in error.errors()
    ]
    return JSONResponse(
        error_body(
            ErrorCode.VALIDATION_ERROR,
            "Certaines données envoyées sont invalides.",
            {"fields": fields},
        ),
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


async def _handle_http_error(_request: Request, error: StarletteHTTPException) -> JSONResponse:
    code, message = _HTTP_CODES.get(
        error.status_code, (ErrorCode.INTERNAL_ERROR, "La requête n'a pas pu être traitée.")
    )
    return JSONResponse(
        error_body(code, message), status_code=error.status_code, headers=error.headers
    )


async def _handle_unexpected_error(_request: Request, error: Exception) -> JSONResponse:
    # La trace part dans les journaux, jamais dans la réponse.
    logger.exception("Erreur imprévue", exc_info=error)
    return JSONResponse(
        error_body(ErrorCode.INTERNAL_ERROR, "Une erreur inattendue est survenue."),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
