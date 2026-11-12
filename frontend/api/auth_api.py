"""
===============================================================================
Client HTTP : auth_api
===============================================================================
Objectif :
    Appels aux routes /auth : inscription, connexion, renouvellement,
    déconnexion, compte connecté.

Utilisé par :
    frontend/session.py, frontend/views/login.py

Exemple d'utilisation :
    tokens = auth_api.login(get_client(), "alice@exemple.fr", "phrase de passe")

Lot :
    A (socle et sécurité)
===============================================================================
"""

from typing import Any

from frontend.api.base import ApiClient

# =============================================================================
# API publique
# =============================================================================


def register(client: ApiClient, email: str, password: str, timezone: str) -> dict[str, Any]:
    """Crée le compte unique ; renvoie ses jetons (l'étudiant est connecté)."""
    return client.post(
        "/auth/register",
        json={"email": email, "password": password, "timezone": timezone},
        authenticated=False,
    )


def login(client: ApiClient, email: str, password: str) -> dict[str, Any]:
    """Échange les identifiants contre une paire de jetons."""
    return client.post(
        "/auth/login", json={"email": email, "password": password}, authenticated=False
    )


def refresh(client: ApiClient, refresh_token: str) -> dict[str, Any]:
    """Échange un jeton de rafraîchissement contre une nouvelle paire."""
    return client.post("/auth/refresh", json={"refresh_token": refresh_token}, authenticated=False)


def logout(client: ApiClient) -> None:
    """Révoque tous les jetons du compte."""
    client.post("/auth/logout")


def me(client: ApiClient) -> dict[str, Any]:
    """Renvoie le compte connecté : id, email, timezone."""
    return client.get("/auth/me")
