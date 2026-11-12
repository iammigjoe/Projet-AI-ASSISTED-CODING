"""
===============================================================================
Tests : deps
===============================================================================
Objectif :
    Vérifier que get_current_user n'authentifie qu'un jeton d'accès valide d'un
    compte actif, et répond 401 au format commun dans tous les autres cas.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import sessionmaker

from backend.api.deps import CurrentUser
from backend.core.security import create_access_token, create_refresh_token
from backend.db.models import User


@pytest.fixture
def me_route(app):
    @app.get("/test/me")
    def me(user: CurrentUser):
        return {"id": user.id, "email": user.email}

    return app


@pytest.fixture
def user(engine) -> User:
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    account = User(email="etudiant@exemple.fr", password_hash="argon2-hash")
    session.add(account)
    session.commit()
    session.close()
    return account


def test_valid_access_token_authenticates_user(me_route, client, user, auth_headers):
    response = client.get("/test/me", headers=auth_headers(user.id))

    assert response.status_code == 200
    assert response.json() == {"id": user.id, "email": "etudiant@exemple.fr"}


def test_missing_token_returns_401_with_bearer_challenge(me_route, client):
    response = client.get("/test/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.parametrize(
    "make_token",
    [
        lambda user_id: "not-a-token",
        lambda user_id: create_refresh_token(user_id, datetime.now(UTC)),
        lambda user_id: create_access_token(user_id, datetime.now(UTC) - timedelta(hours=2)),
    ],
    ids=["garbage", "refresh-token", "expired"],
)
def test_invalid_tokens_return_401(me_route, client, user, make_token):
    response = client.get("/test/me", headers={"Authorization": f"Bearer {make_token(user.id)}"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_token_of_unknown_user_returns_401(me_route, client, auth_headers):
    response = client.get("/test/me", headers=auth_headers(999))

    assert response.status_code == 401


def test_token_of_user_pending_deletion_returns_401(me_route, client, engine, user, auth_headers):
    session = sessionmaker(bind=engine)()
    session.get(User, user.id).deleted_at = datetime.now(UTC)
    session.commit()
    session.close()

    response = client.get("/test/me", headers=auth_headers(user.id))

    assert response.status_code == 401
