"""
===============================================================================
Client HTTP : base
===============================================================================
Objectif :
    Client HTTP commun à tous les clients de frontend/api/ : seul point de
    contact entre Streamlit et FastAPI.

Responsabilités :
    - Joindre l'URL de l'API (MYPLAN_API_BASE_URL) et le jeton d'accès de la
      session Streamlit à chaque requête.
    - Transformer toute réponse d'erreur en ApiError(code, message), au format
      des conventions §6, pour que les pages affichent le message tel quel.
    - Ne jamais laisser une erreur réseau remonter brute jusqu'à une page.

Utilisé par :
    auth_api, courses_api, documents_api, planning_api, progress_api.

Exemple d'utilisation :
    courses = get_client().get("/courses")

Lot :
    A (socle et sécurité)
===============================================================================
"""

import os
from collections.abc import Callable
from typing import Any

import httpx

# =============================================================================
# Constantes
# =============================================================================

DEFAULT_BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
TIMEOUT_SECONDS = 30.0

# =============================================================================
# Types
# =============================================================================


class ApiError(Exception):
    """Erreur renvoyée par l'API ; message en français, affichable tel quel."""

    def __init__(
        self, status_code: int, code: str, message: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


# =============================================================================
# API publique
# =============================================================================


class ApiClient:
    """Client de l'API MyPlan, une instance par session Streamlit."""

    def __init__(
        self,
        base_url: str,
        token_getter: Callable[[], str | None],
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        """Crée le client.

        Args:
            base_url: URL de l'API, sans le préfixe /api/v1.
            token_getter: Renvoie le jeton d'accès courant, ou None si
                l'étudiant n'est pas connecté.
            transport: Transport httpx de remplacement, pour les tests.
        """
        self._token_getter = token_getter
        self._http = httpx.Client(
            base_url=base_url.rstrip("/") + API_PREFIX,
            timeout=TIMEOUT_SECONDS,
            transport=transport,
        )

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Envoie un GET et renvoie le corps JSON."""
        return self.request("GET", path, params=params)

    def post(self, path: str, json: Any = None, files: dict[str, Any] | None = None) -> Any:
        """Envoie un POST (JSON ou fichiers) et renvoie le corps JSON."""
        return self.request("POST", path, json=json, files=files)

    def patch(self, path: str, json: Any = None) -> Any:
        """Envoie un PATCH et renvoie le corps JSON."""
        return self.request("PATCH", path, json=json)

    def delete(self, path: str) -> None:
        """Envoie un DELETE."""
        self.request("DELETE", path)

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Envoie une requête et renvoie le corps JSON, ou None si vide.

        Args:
            method: Méthode HTTP.
            path: Chemin relatif à /api/v1, par exemple « /courses ».
            **kwargs: Arguments transmis à httpx (json, params, files).

        Returns:
            Le corps JSON décodé, ou None pour une réponse sans corps (204).

        Raises:
            ApiError: Si l'API répond une erreur, ou si elle ne répond pas.
        """
        headers = {}
        token = self._token_getter()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            response = self._http.request(method, path, headers=headers, **kwargs)
        except httpx.HTTPError as error:
            raise ApiError(0, "NETWORK_ERROR", "Le serveur ne répond pas. Réessayez.") from error

        if response.is_error:
            raise _to_api_error(response)
        if response.status_code == httpx.codes.NO_CONTENT or not response.content:
            return None
        return response.json()


def get_client() -> ApiClient:
    """Renvoie le client de la session Streamlit courante, créé au premier appel."""
    import streamlit as st

    from frontend.state import ACCESS_TOKEN

    if "api_client" not in st.session_state:
        st.session_state["api_client"] = ApiClient(
            base_url=os.environ.get("MYPLAN_API_BASE_URL", DEFAULT_BASE_URL),
            token_getter=lambda: st.session_state.get(ACCESS_TOKEN),
        )
    return st.session_state["api_client"]


# =============================================================================
# Fonctions internes
# =============================================================================


def _to_api_error(response: httpx.Response) -> ApiError:
    """Lit une réponse d'erreur au format commun ; repli si le corps est inattendu."""
    try:
        error = response.json()["error"]
        return ApiError(response.status_code, error["code"], error["message"], error.get("details"))
    except (ValueError, KeyError, TypeError):
        return ApiError(
            response.status_code, "UNEXPECTED_RESPONSE", "Réponse inattendue du serveur."
        )
