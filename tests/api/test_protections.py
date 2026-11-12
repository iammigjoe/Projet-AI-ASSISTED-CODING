"""
===============================================================================
Tests : protections
===============================================================================
Objectif :
    Vérifier les protections appliquées à toute l'API : limitation du débit,
    taille des requêtes, contrôle de Host, en-têtes de sécurité.

Lot :
    A (socle et sécurité)
===============================================================================
"""

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from backend.api.rate_limit import limiter
from backend.core.config import get_settings


@pytest.fixture
def routes(app):
    @app.post("/test/echo-size")
    async def echo_size(request: Request):
        return {"size": len(await request.body())}

    @app.post("/test/strict")
    @limiter.limit("3/minute")
    def strict(request: Request):
        return {"ok": True}

    return app


# =============================================================================
# Limitation du débit
# =============================================================================


def test_strict_route_returns_429_after_limit(routes, client):
    statuses = [client.post("/test/strict").status_code for _ in range(4)]

    assert statuses == [200, 200, 200, 429]


def test_rate_limit_error_uses_common_format_and_retry_after(routes, client):
    for _ in range(3):
        client.post("/test/strict")
    response = client.post("/test/strict")

    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert int(response.headers["Retry-After"]) > 0


# =============================================================================
# Taille des requêtes
# =============================================================================


def test_request_within_limit_is_accepted(routes, client):
    response = client.post("/test/echo-size", content=b"x" * 1024)

    assert response.json() == {"size": 1024}


def test_declared_oversized_request_returns_413(routes, client):
    too_big = get_settings().max_request_bytes + 1

    response = client.post("/test/echo-size", content=b"x" * too_big)

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_streamed_oversized_request_without_length_returns_413(routes, client):
    limit = get_settings().max_request_bytes
    chunk = b"x" * (1024 * 1024)

    def body():
        sent = 0
        while sent <= limit:
            yield chunk
            sent += len(chunk)

    response = client.post("/test/echo-size", content=body())

    assert response.status_code == 413


# =============================================================================
# Host et en-têtes
# =============================================================================


def test_unknown_host_is_refused(app):
    with TestClient(app, base_url="http://evil.example") as other_client:
        response = other_client.get("/api/v1/anything")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_HOST"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_api_responses_forbid_scripts(client):
    response = client.get("/api/v1/anything")

    assert (
        response.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
    )
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Strict-Transport-Security" not in response.headers


def test_docs_are_served_without_strict_csp_outside_prod(client):
    response = client.get("/docs")

    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers


def test_production_adds_hsts_and_hides_docs(monkeypatch):
    from backend.main import create_app

    monkeypatch.setenv("MYPLAN_ENV", "prod")
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as prod_client:
            response = prod_client.get("/docs")
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()

    assert response.status_code == 404
    assert response.headers["Strict-Transport-Security"].startswith("max-age=31536000")
