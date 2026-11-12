"""
===============================================================================
Tests : auth
===============================================================================
Objectif :
    Vérifier de bout en bout l'inscription, la connexion, le renouvellement des
    jetons et la déconnexion, avec leurs protections : inscription fermée,
    politique de mots de passe, réponse identique pour un email inconnu,
    attente après échecs, révocation.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.core.login_throttle import FREE_ATTEMPTS
from backend.db.models import User, UserSettings

EMAIL = "etudiant@exemple.fr"
PASSWORD = "une phrase de passe solide"

# =============================================================================
# Fonctions internes
# =============================================================================


def _register(client, email=EMAIL, password=PASSWORD, **extra):
    return client.post("/auth/register", json={"email": email, "password": password, **extra})


def _login(client, email=EMAIL, password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Inscription
# =============================================================================


def test_register_creates_account_with_settings_and_returns_tokens(client, engine):
    response = _register(client, email="  Etudiant@Exemple.FR ", timezone="America/Montreal")

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 15 * 60

    session = sessionmaker(bind=engine)()
    user = session.scalar(select(User))
    assert user.email == EMAIL
    assert user.timezone == "America/Montreal"
    assert user.password_hash.startswith("$argon2")
    assert session.get(UserSettings, user.id) is not None
    session.close()


def test_register_when_account_exists_returns_403(client):
    _register(client)

    response = _register(client, email="autre@exemple.fr")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "REGISTRATION_CLOSED"


def test_register_with_weak_password_lists_problems(client):
    response = _register(client, password="motdepasse")

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "WEAK_PASSWORD"
    assert any("12 caractères" in problem for problem in error["details"]["problems"])


@pytest.mark.parametrize("timezone", ["Mars/Olympus", "../../etc/passwd", "+01:00"])
def test_register_with_unknown_timezone_returns_422(client, timezone):
    response = _register(client, timezone=timezone)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_register_rejects_unknown_fields(client):
    response = _register(client, token_version=99)

    assert response.status_code == 422


def test_register_response_never_contains_password(client):
    response = _register(client)

    assert PASSWORD not in response.text
    assert "argon2" not in response.text


# =============================================================================
# Connexion
# =============================================================================


def test_login_with_valid_credentials_returns_tokens(client):
    _register(client)

    response = _login(client, email="ETUDIANT@exemple.fr")

    assert response.status_code == 200
    me = client.get("/auth/me", headers=_bearer(response.json()["access_token"]))
    assert me.json()["email"] == EMAIL


def test_wrong_password_and_unknown_email_get_identical_responses(client):
    _register(client)

    wrong_password = _login(client, password="pas le bon mot de passe")
    unknown_email = _login(client, email="inconnu@exemple.fr")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert wrong_password.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_repeated_failures_trigger_wait_with_retry_after(client):
    _register(client)
    for _ in range(FREE_ATTEMPTS):
        assert _login(client, password="mauvais mot de passe").status_code == 401

    blocked = _login(client)

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "TOO_MANY_LOGIN_ATTEMPTS"
    assert int(blocked.headers["Retry-After"]) > 0


def test_successful_login_resets_failure_count(client):
    _register(client)
    for _ in range(FREE_ATTEMPTS - 1):
        _login(client, password="mauvais mot de passe")

    assert _login(client).status_code == 200
    for _ in range(FREE_ATTEMPTS - 1):
        _login(client, password="mauvais mot de passe")
    assert _login(client).status_code == 200


def test_login_of_account_pending_deletion_is_refused(client, engine):
    _register(client)
    session = sessionmaker(bind=engine)()
    session.scalar(select(User)).deleted_at = datetime.now(UTC)
    session.commit()
    session.close()

    assert _login(client).status_code == 401


# =============================================================================
# Jetons
# =============================================================================


def test_refresh_returns_new_working_tokens(client):
    tokens = _register(client).json()

    response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    me = client.get("/auth/me", headers=_bearer(response.json()["access_token"]))
    assert me.status_code == 200


def test_access_token_cannot_be_used_to_refresh(client):
    tokens = _register(client).json()

    response = client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]})

    assert response.status_code == 401


def test_refresh_token_cannot_access_the_api(client):
    tokens = _register(client).json()

    response = client.get("/auth/me", headers=_bearer(tokens["refresh_token"]))

    assert response.status_code == 401


def test_logout_revokes_access_and_refresh_tokens(client):
    tokens = _register(client).json()

    logout = client.post("/auth/logout", headers=_bearer(tokens["access_token"]))

    assert logout.status_code == 204
    assert client.get("/auth/me", headers=_bearer(tokens["access_token"])).status_code == 401
    refresh = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 401


def test_login_after_logout_works_again(client):
    tokens = _register(client).json()
    client.post("/auth/logout", headers=_bearer(tokens["access_token"]))

    new_tokens = _login(client).json()

    assert client.get("/auth/me", headers=_bearer(new_tokens["access_token"])).status_code == 200


def test_logout_requires_authentication(client):
    assert client.post("/auth/logout").status_code == 401


def test_me_never_exposes_secrets(client):
    tokens = _register(client).json()

    me = client.get("/auth/me", headers=_bearer(tokens["access_token"])).json()

    assert set(me) == {"id", "email", "timezone"}
