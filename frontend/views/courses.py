"""
===============================================================================
Page : Matières
===============================================================================
Objectif :
    Suivre l'avancement des matières, les renommer, les supprimer (blocs 1 et 5).
    Une matière se crée en important un cours (page Documents, lot B).

Appelle :
    courses_api.list_courses, update_course, delete_course

Notes :
    - Les noms viennent de l'utilisateur : toujours affichés avec escape_markdown.
    - Supprimer une matière supprime ses chapitres, échéances et sessions :
      confirmation en deux temps.

Lot :
    A (socle et sécurité)
===============================================================================
"""

import streamlit as st

from frontend.api import courses_api
from frontend.api.base import ApiError, get_client
from frontend.components.ui import confirm_delete, flash, page_header, show_api_error, show_flash
from frontend.security import escape_markdown

# =============================================================================
# Constantes
# =============================================================================

DIFFICULTY_LABELS = {
    1: "Très facile",
    2: "Facile",
    3: "Moyenne",
    4: "Difficile",
    5: "Très difficile",
}

# =============================================================================
# Page
# =============================================================================

page_header(
    "Matières",
    "Chaque cours importé devient une matière. Suivez ici son avancement et ajustez sa difficulté.",
)
show_flash()
client = get_client()

try:
    courses = courses_api.list_courses(client)
except ApiError as error:
    show_api_error(error)
    st.stop()

if not courses:
    st.info("Aucune matière pour l'instant. Importez un cours (PDF ou Markdown) pour commencer.")
    st.stop()

for course in courses:
    label = (
        f"{escape_markdown(course['name'])} · {course['progress']:.0f} % · "
        f"{course['hours_done']:g} h / {course['hours_total']:g} h"
    )
    with st.expander(label, icon=":material/school:"):
        st.progress(min(course["progress"], 100) / 100)
        with st.form(f"edit_course_{course['id']}"):
            new_name = st.text_input("Nom", course["name"], max_chars=100)
            new_color = st.color_picker("Couleur", course["color"])
            new_difficulty = st.select_slider(
                "Difficulté perçue",
                options=list(DIFFICULTY_LABELS),
                value=course["difficulty"],
                format_func=DIFFICULTY_LABELS.get,
            )
            if st.form_submit_button("Enregistrer"):
                try:
                    courses_api.update_course(
                        client,
                        course["id"],
                        name=new_name,
                        color=new_color,
                        difficulty=new_difficulty,
                    )
                    flash("Matière modifiée.")
                    st.rerun()
                except ApiError as error:
                    show_api_error(error)

        if confirm_delete(
            f"course_{course['id']}",
            "Supprimer la matière",
            f"« {course['name']} » sera supprimée avec ses chapitres, échéances et sessions.",
        ):
            try:
                courses_api.delete_course(client, course["id"])
                flash("Matière supprimée.")
                st.rerun()
            except ApiError as error:
                show_api_error(error)
