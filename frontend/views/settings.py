"""
===============================================================================
Page : Paramètres
===============================================================================
Objectif :
    Régler le profil d'étude : vitesse de lecture, durée maximale d'une
    session, pause, niveau visé, seuil de révision (P0-08).

Appelle :
    courses_api.get_settings, courses_api.update_settings

Lot :
    A (socle et sécurité)
===============================================================================
"""

import streamlit as st

from frontend.api import courses_api
from frontend.api.base import ApiError, get_client
from frontend.components.ui import flash, page_header, show_api_error, show_flash

# =============================================================================
# Constantes
# =============================================================================

GOAL_LABELS = {
    "discovery": "Découverte : une première lecture",
    "standard": "Standard : comprendre et retenir l'essentiel",
    "mastery": "Maîtrise : connaître le cours en détail",
}

# =============================================================================
# Page
# =============================================================================

page_header(
    "Paramètres",
    "Ces réglages servent à estimer le temps de chaque chapitre et à découper vos sessions.",
)
show_flash()
client = get_client()

try:
    settings = courses_api.get_settings(client)
except ApiError as error:
    show_api_error(error)
    st.stop()

with st.form("settings"):
    reading_speed = st.number_input(
        "Vitesse de lecture (mots par minute)",
        min_value=50,
        max_value=1000,
        step=10,
        value=settings["reading_speed_wpm"],
        help="Un étudiant lit en moyenne 200 à 250 mots par minute un cours technique.",
    )
    max_session = st.number_input(
        "Durée maximale d'une session (minutes)",
        min_value=15,
        max_value=240,
        step=5,
        value=settings["max_session_min"],
    )
    break_minutes = st.number_input(
        "Pause entre deux sessions (minutes)",
        min_value=0,
        max_value=120,
        step=5,
        value=settings["break_min"],
    )
    goal = st.radio(
        "Niveau visé",
        options=list(GOAL_LABELS),
        index=list(GOAL_LABELS).index(settings["mastery_goal"]),
        format_func=GOAL_LABELS.get,
    )
    threshold = st.slider(
        "Seuil de révision",
        min_value=50,
        max_value=95,
        step=5,
        value=round(settings["retention_threshold"] * 100),
        format="%d %%",
        help="Une révision est proposée quand la probabilité de se souvenir d'un "
        "chapitre passe sous ce seuil.",
    )

    if st.form_submit_button("Enregistrer", type="primary"):
        try:
            courses_api.update_settings(
                client,
                reading_speed_wpm=reading_speed,
                max_session_min=max_session,
                break_min=break_minutes,
                mastery_goal=goal,
                retention_threshold=threshold / 100,
            )
            flash("Paramètres enregistrés.")
            st.rerun()
        except ApiError as error:
            show_api_error(error)
