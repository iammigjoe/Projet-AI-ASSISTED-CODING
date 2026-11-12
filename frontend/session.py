"""
===============================================================================
Module : session
===============================================================================
Objectif :
    État de connexion de l'étudiant dans la session Streamlit.

Responsabilités :
    - Garder les jetons en mémoire serveur (st.session_state), jamais dans le
      navigateur : ni cookie, ni stockage local (Spec §4).
    - Renouveler les jetons après expiration du jeton d'accès.
    - Déconnecter : révoquer les jetons côté API, puis tout oublier côté Streamlit.

Utilisé par :
    frontend/app.py, frontend/views/login.py, frontend/api/base.py (refresher).

Exemple d'utilisation :
    if not is_logged_in():
        st.switch_page("views/login.py")

Lot :
    A (socle et sécurité)
===============================================================================
"""

from contextlib import suppress
from typing import Any

import streamlit as st

from frontend.api import auth_api
from frontend.api.base import ApiError, get_client
from frontend.state import ACCESS_TOKEN, CURRENT_USER, FLASH_MESSAGE, REFRESH_TOKEN

# =============================================================================
# API publique
# =============================================================================


def is_logged_in() -> bool:
    """Indique si la session détient un jeton d'accès."""
    return bool(st.session_state.get(ACCESS_TOKEN))


def start_session(tokens: dict[str, Any]) -> None:
    """Enregistre les jetons d'une connexion réussie et charge le compte."""
    st.session_state[ACCESS_TOKEN] = tokens["access_token"]
    st.session_state[REFRESH_TOKEN] = tokens["refresh_token"]
    st.session_state[CURRENT_USER] = auth_api.me(get_client())


def refresh_tokens() -> bool:
    """Renouvelle les jetons ; en cas d'échec, oublie la session.

    Returns:
        True si de nouveaux jetons sont en place et la requête peut être
        rejouée ; False si l'étudiant doit se reconnecter.
    """
    refresh_token = st.session_state.get(REFRESH_TOKEN)
    if not refresh_token:
        return False
    try:
        tokens = auth_api.refresh(get_client(), refresh_token)
    except ApiError:
        clear_session("Votre session a expiré. Reconnectez-vous.")
        return False
    st.session_state[ACCESS_TOKEN] = tokens["access_token"]
    st.session_state[REFRESH_TOKEN] = tokens["refresh_token"]
    return True


def logout() -> None:
    """Révoque les jetons côté API puis oublie la session, même si l'API ne répond pas."""
    # Déjà expirée ou API injoignable : la session locale est oubliée quand même.
    with suppress(ApiError):
        auth_api.logout(get_client())
    clear_session("Vous êtes déconnecté.")


def clear_session(message: str | None = None) -> None:
    """Oublie jetons et compte ; garde un message à afficher sur la page de connexion."""
    for key in (ACCESS_TOKEN, REFRESH_TOKEN, CURRENT_USER):
        st.session_state.pop(key, None)
    if message:
        st.session_state[FLASH_MESSAGE] = message


def current_user() -> dict[str, Any] | None:
    """Renvoie le compte connecté (id, email, timezone), ou None."""
    return st.session_state.get(CURRENT_USER)
