"""
===============================================================================
Module : middleware
===============================================================================
Objectif :
    Protections appliquées à toutes les requêtes, avant tout router.

Responsabilités :
    - Refuser une requête dont le corps dépasse la taille autorisée (413), en
      lisant Content-Length puis en comptant les octets réellement reçus : un
      client qui ment sur la taille ou envoie en « chunked » est arrêté aussi.
    - Refuser un en-tête Host inattendu (400).
    - Ajouter les en-têtes de sécurité à toutes les réponses : pas de
      détection de type, pas d'affichage en iframe, pas de cache, CSP qui
      interdit tout script, et HSTS en production.

Utilisé par :
    backend.main (create_app).

Exemple d'utilisation :
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_bytes)

Lot :
    A (socle et sécurité)
===============================================================================
"""

import json
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.api.errors import ErrorCode, error_body

# =============================================================================
# Constantes
# =============================================================================

BASE_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    # Les réponses contiennent des données personnelles : jamais de cache partagé.
    "Cache-Control": "no-store",
    # L'API ne sert que du JSON : aucun script, aucune ressource, aucun cadre.
    # Si une réponse était un jour interprétée comme du HTML, rien ne s'exécuterait.
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}

# Imposé au navigateur pendant un an : HTTPS uniquement. Seulement en production,
# où l'API est servie en HTTPS (Spec §4).
HSTS_HEADER = ("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

# La documentation interactive (/docs) charge ses scripts : la CSP stricte la casserait.
# Elle n'est exposée qu'en développement (backend/main.py).
_DOCS_PATHS = ("/docs", "/openapi.json")

# =============================================================================
# Types
# =============================================================================


class _BodyTooLargeError(Exception):
    """Levée par le receive surveillé quand le corps dépasse la limite."""


# =============================================================================
# API publique
# =============================================================================


class BodySizeLimitMiddleware:
    """Refuse en 413 toute requête dont le corps dépasse max_bytes."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = _content_length(scope)
        if declared is not None and declared > self.max_bytes:
            await _send_too_large(send)
            return

        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise _BodyTooLargeError
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        # except* : un middleware intermédiaire (limitation du débit) lit le corps
        # dans un groupe de tâches, qui enveloppe l'erreur dans un ExceptionGroup.
        try:
            await self.app(scope, limited_receive, tracking_send)
        except* _BodyTooLargeError:
            if not response_started:
                await _send_too_large(send)


class HostCheckMiddleware:
    """Refuse en 400 une requête dont l'en-tête Host n'est pas attendu.

    Protège contre les attaques par en-tête Host forgé (liens empoisonnés,
    DNS rebinding) : seuls les noms de MYPLAN_ALLOWED_HOSTS sont servis.
    """

    def __init__(self, app: ASGIApp, allowed_hosts: list[str]) -> None:
        self.app = app
        self.allowed_hosts = {host.lower() for host in allowed_hosts}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if _host_name(scope) not in self.allowed_hosts:
            await _send_error(send, 400, ErrorCode.INVALID_HOST, "Nom d'hôte non autorisé.")
            return
        await self.app(scope, receive, send)


class SecurityHeadersMiddleware:
    """Ajoute les en-têtes de sécurité à chaque réponse HTTP."""

    def __init__(self, app: ASGIApp, hsts: bool) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        is_docs = scope["path"].startswith(_DOCS_PATHS)

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                present = {name.lower() for name, _ in headers}
                for name, value in self._headers(is_docs):
                    if name.lower().encode() not in present:
                        headers.append((name.encode(), value.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)

    def _headers(self, is_docs: bool) -> list[tuple[str, str]]:
        headers = [
            (name, value)
            for name, value in BASE_SECURITY_HEADERS.items()
            if not (is_docs and name == "Content-Security-Policy")
        ]
        if self.hsts:
            headers.append(HSTS_HEADER)
        return headers


# =============================================================================
# Fonctions internes
# =============================================================================


def _content_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", []):
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


def _host_name(scope: Scope) -> str:
    """Nom d'hôte de la requête, sans port, en minuscules ; vide s'il manque."""
    for name, value in scope.get("headers", []):
        if name == b"host":
            host = value.decode("latin-1").strip().lower()
            if host.startswith("["):  # IPv6 : « [::1]:8000 »
                return host.split("]")[0] + "]"
            return host.split(":")[0]
    return ""


async def _send_too_large(send: Send) -> None:
    await _send_error(
        send, 413, ErrorCode.REQUEST_TOO_LARGE, "La requête dépasse la taille autorisée."
    )


async def _send_error(send: Send, status_code: int, code: ErrorCode, message: str) -> None:
    """Envoie une erreur au format commun, hors de FastAPI (middleware ASGI)."""
    body: dict[str, Any] = error_body(code, message)
    payload = json.dumps(body).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(payload)).encode()),
                (b"connection", b"close"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": payload})
