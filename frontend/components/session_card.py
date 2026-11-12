"""
===============================================================================
Composant : session_card
===============================================================================
Objectif :
    Afficher une session de planning et ses actions de suivi.

Utilisé par :
    La page Planning du lot C.

Lot :
    D (agenda et suivi)
===============================================================================
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st

from frontend.api.base import ApiError
from frontend.api.progress_api import StudySessionStatus, update_study_session
from frontend.security import escape_markdown

# =============================================================================
# API publique
# =============================================================================


def render_session_card(study_session: Mapping[str, Any], timezone_name: str) -> None:
    """Affiche une session, ses horaires locaux et les actions de suivi."""
    session_id = study_session["id"]
    status = study_session["status"]
    if (
        not isinstance(session_id, int)
        or not isinstance(status, str)
        or status not in {"planned", "done", "missed"}
    ):
        raise ValueError("La session ne contient pas un identifiant ou un statut valide.")

    chapter_title = study_session.get("chapter_title", f"Chapitre {study_session['chapter_id']}")
    start = _local_datetime(study_session["starts_at"], timezone_name)
    end = _local_datetime(study_session["ends_at"], timezone_name)

    with st.container(border=True):
        st.markdown(f"**{escape_markdown(chapter_title)}**")
        st.caption(f"{start:%d/%m/%Y %H:%M} – {end:%H:%M}")

        if status == "done":
            st.success("Session faite")
        elif status == "missed":
            st.warning("Session non faite")
        else:
            st.info("Session à faire")

        columns = st.columns(2)
        if status != "done" and columns[0].button(
            "Marquer faite", key=f"study-session-{session_id}-done"
        ):
            _update_status(session_id, "done")
        if status != "missed" and columns[1].button(
            "Marquer non faite", key=f"study-session-{session_id}-missed"
        ):
            _update_status(session_id, "missed")


# =============================================================================
# Fonctions internes
# =============================================================================


def _local_datetime(value: str | datetime, timezone_name: str) -> datetime:
    """Convertit un instant API en heure locale, en refusant les données naïves."""
    instant = datetime.fromisoformat(value) if isinstance(value, str) else value
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Les horaires de session doivent inclure leur fuseau.")
    return instant.astimezone(ZoneInfo(timezone_name))


def _update_status(study_session_id: int, status: StudySessionStatus) -> None:
    try:
        update_study_session(study_session_id, status)
    except ApiError as error:
        st.error(error.message)
    else:
        st.rerun()
