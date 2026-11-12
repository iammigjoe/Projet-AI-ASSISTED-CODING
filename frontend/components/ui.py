"""
===============================================================================
Composant : ui
===============================================================================
Objectif :
    Cadre commun des pages Streamlit, pour que les quatre lots produisent une
    interface cohérente (conventions §3, « Cadre commun de l'interface »).

Responsabilités :
    - En-tête de page identique partout.
    - Une seule façon d'afficher une erreur de l'API : son message en français,
      échappé, et la liste des raisons quand l'API en donne.
    - Messages qui survivent à un rerun (« Matière créée. »).
    - Confirmation en deux temps avant toute suppression.
    - Dates et heures toujours affichées dans le fuseau de l'étudiant.

Utilisé par :
    Toutes les pages de frontend/views/.

Exemple d'utilisation :
    page_header("Matières", "Les matières de vos cours.")
    try:
        courses = courses_api.list_courses(get_client())
    except ApiError as error:
        show_api_error(error)
        st.stop()

Lot :
    A (socle et sécurité)
===============================================================================
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from frontend.api.base import ApiError
from frontend.security import escape_markdown
from frontend.state import FLASH_MESSAGE

# =============================================================================
# Constantes
# =============================================================================

_WEEKDAYS = ("lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim.")
_MONTHS = (
    "janv.",
    "févr.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
)
_CONFIRM_PREFIX = "confirm_"

# =============================================================================
# API publique
# =============================================================================


def page_header(title: str, description: str | None = None) -> None:
    """Affiche le titre de la page et, en dessous, une phrase d'explication."""
    st.title(title)
    if description:
        st.caption(description)


def show_api_error(error: ApiError) -> None:
    """Affiche une erreur de l'API, message échappé, avec ses raisons éventuelles.

    Les raisons viennent de details["problems"] (mot de passe trop faible, par
    exemple), déjà rédigées en français par l'API.
    """
    st.error(escape_markdown(error.message))
    for problem in error.details.get("problems", []):
        st.markdown(f"- {escape_markdown(problem)}")


def flash(message: str) -> None:
    """Garde un message de succès à afficher au prochain affichage de page."""
    st.session_state[FLASH_MESSAGE] = message


def show_flash() -> None:
    """Affiche puis oublie le message gardé par flash(), s'il y en a un."""
    message = st.session_state.pop(FLASH_MESSAGE, None)
    if message:
        st.success(escape_markdown(message))


def confirm_delete(key: str, label: str, warning: str) -> bool:
    """Bouton de suppression en deux temps : « Supprimer », puis « Confirmer ».

    Args:
        key: Identifiant unique sur la page, par exemple f"course_{course_id}".
        label: Texte du premier bouton.
        warning: Ce qui sera perdu, affiché avant la confirmation.

    Returns:
        True une seule fois, au clic sur « Confirmer la suppression ».
    """
    state_key = _CONFIRM_PREFIX + key
    if not st.session_state.get(state_key):
        if st.button(label, key=f"{state_key}_ask"):
            st.session_state[state_key] = True
            st.rerun()
        return False

    st.warning(escape_markdown(warning))
    confirm, cancel = st.columns(2)
    if cancel.button("Annuler", key=f"{state_key}_cancel"):
        st.session_state.pop(state_key, None)
        st.rerun()
    if confirm.button("Confirmer la suppression", key=f"{state_key}_confirm", type="primary"):
        st.session_state.pop(state_key, None)
        return True
    return False


def format_local_datetime(instant: datetime | str, timezone: str) -> str:
    """Affiche un instant UTC de l'API dans le fuseau de l'étudiant.

    Args:
        instant: datetime avec fuseau, ou texte ISO 8601 renvoyé par l'API.
        timezone: Nom IANA du compte (current_user()["timezone"]).

    Returns:
        Par exemple « lun. 16 nov. 18:00 ».
    """
    if isinstance(instant, str):
        instant = datetime.fromisoformat(instant.replace("Z", "+00:00"))
    local = instant.astimezone(ZoneInfo(timezone))
    weekday = _WEEKDAYS[local.weekday()]
    month = _MONTHS[local.month - 1]
    return f"{weekday} {local.day} {month} {local:%H:%M}"
