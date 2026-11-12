"""
===============================================================================
Page : Connexion
===============================================================================
Objectif :
    Se connecter, ou créer le compte unique au premier lancement (P0-01).

Appelle :
    auth_api.login, auth_api.register, session.start_session

Notes :
    - Le mot de passe n'est jamais gardé dans st.session_state.
    - L'inscription est refusée par l'API dès qu'un compte existe : la page
      affiche alors le message de l'API.

Lot :
    A (socle et sécurité)
===============================================================================
"""

import streamlit as st

from frontend.api import auth_api
from frontend.api.base import ApiError, get_client
from frontend.components.ui import page_header, show_api_error, show_flash
from frontend.session import start_session

# =============================================================================
# Constantes
# =============================================================================

MIN_PASSWORD_LENGTH = 12
TIMEZONES = (
    "Europe/Paris",
    "Europe/Brussels",
    "Europe/Zurich",
    "Europe/Luxembourg",
    "America/Montreal",
    "Africa/Casablanca",
    "Africa/Abidjan",
    "Africa/Dakar",
    "Indian/Reunion",
    "America/Guadeloupe",
)

# =============================================================================
# Page
# =============================================================================

page_header("MyPlan", "Transformez vos cours en planning de révision.")
show_flash()

login_tab, register_tab = st.tabs(["Se connecter", "Créer le compte"])

with login_tab, st.form("login"):
    email = st.text_input("Email", autocomplete="email")
    password = st.text_input("Mot de passe", type="password", autocomplete="current-password")
    if st.form_submit_button("Se connecter", type="primary"):
        if not email or not password:
            st.error("Saisissez votre email et votre mot de passe.")
        else:
            try:
                start_session(auth_api.login(get_client(), email, password))
                st.rerun()
            except ApiError as error:
                show_api_error(error)

with register_tab:
    st.caption(
        "Le premier lancement crée le compte de l'application. "
        f"Choisissez une phrase de passe d'au moins {MIN_PASSWORD_LENGTH} caractères."
    )
    with st.form("register"):
        new_email = st.text_input("Email", autocomplete="email", key="register_email")
        new_password = st.text_input(
            "Mot de passe", type="password", autocomplete="new-password", key="register_password"
        )
        confirmation = st.text_input(
            "Confirmer le mot de passe", type="password", autocomplete="new-password"
        )
        timezone = st.selectbox("Fuseau horaire", TIMEZONES)
        if st.form_submit_button("Créer le compte", type="primary"):
            if new_password != confirmation:
                st.error("Les deux mots de passe ne correspondent pas.")
            elif len(new_password) < MIN_PASSWORD_LENGTH:
                st.error(f"Le mot de passe doit faire au moins {MIN_PASSWORD_LENGTH} caractères.")
            else:
                try:
                    tokens = auth_api.register(get_client(), new_email, new_password, timezone)
                    start_session(tokens)
                    st.rerun()
                except ApiError as error:
                    show_api_error(error)
