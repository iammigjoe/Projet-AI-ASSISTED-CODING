"""
===============================================================================
Tests : errors
===============================================================================
Objectif :
    Vérifier que toute erreur de l'API a la forme {"error": {"code", "message"}},
    sans détail technique, et que les en-têtes de sécurité sont présents.

Lot :
    A (socle et sécurité)
===============================================================================
"""

import pytest
from pydantic import BaseModel, Field

from backend.domain.errors import DomainError, NotFoundError, RegistrationClosedError


class _Payload(BaseModel):
    password: str = Field(min_length=12)


@pytest.fixture
def error_routes(app):
    @app.get("/test/domain-error")
    def domain_error():
        raise DomainError("Règle non respectée.", {"field": "x"})

    @app.get("/test/not-found")
    def not_found():
        raise NotFoundError("Matière introuvable.")

    @app.get("/test/registration-closed")
    def registration_closed():
        raise RegistrationClosedError("Le compte existe déjà.")

    @app.get("/test/crash")
    def crash():
        raise RuntimeError("SELECT * FROM users -- détail interne")

    @app.post("/test/validate")
    def validate(payload: _Payload):
        return {"ok": True}

    return app


def test_unknown_route_returns_not_found_format(client):
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "NOT_FOUND", "message": "Ressource introuvable."}}


def test_domain_error_returns_422_with_code_and_details(error_routes, client):
    response = client.get("/test/domain-error")

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "DOMAIN_ERROR",
        "message": "Règle non respectée.",
        "details": {"field": "x"},
    }


@pytest.mark.parametrize(
    ("path", "status_code", "code"),
    [
        ("/test/not-found", 404, "NOT_FOUND"),
        ("/test/registration-closed", 403, "REGISTRATION_CLOSED"),
    ],
)
def test_specific_domain_errors_map_to_their_status(error_routes, client, path, status_code, code):
    response = client.get(path)

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code


def test_validation_error_does_not_echo_input(error_routes, client):
    response = client.post("/test/validate", json={"password": "tiny-pw"})

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"]["fields"][0]["location"] == ["body", "password"]
    assert "tiny-pw" not in response.text


def test_unexpected_error_returns_500_without_internal_details(error_routes, client):
    response = client.get("/test/crash")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "SELECT" not in response.text


def test_responses_carry_security_headers(client):
    response = client.get("/api/v1/does-not-exist")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"
