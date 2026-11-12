"""
===============================================================================
Page : Matières
===============================================================================
Objectif :
    Créer, modifier et supprimer les matières de l'étudiant (P0-02).

Appelle :
    courses_api.list_courses, create_course, update_course, delete_course

Notes :
    - Les noms viennent de l'utilisateur : toujours affichés avec escape_markdown.
    - Supprimer une matière supprime ses documents, chapitres et échéances :
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
DEFAULT_COLOR = "#3366FF"

# =============================================================================
# Page
# =============================================================================

page_header("Matières", "Chaque document et chaque échéance est rattaché à une matière.")
show_flash()
client = get_client()

with (
    st.expander("Ajouter une matière", expanded=False, icon=":material/add:"),
    st.form("create_course", clear_on_submit=True),
):
    name = st.text_input("Nom", max_chars=100)
    color = st.color_picker("Couleur", DEFAULT_COLOR)
    difficulty = st.select_slider(
        "Difficulté perçue",
        options=list(DIFFICULTY_LABELS),
        value=3,
        format_func=DIFFICULTY_LABELS.get,
    )
    if st.form_submit_button("Ajouter", type="primary"):
        if not name.strip():
            st.error("Donnez un nom à la matière.")
        else:
            try:
                courses_api.create_course(client, name, color, difficulty)
                flash(f"Matière « {name.strip()} » ajoutée.")
                st.rerun()
            except ApiError as error:
                show_api_error(error)

try:
    courses = courses_api.list_courses(client)
except ApiError as error:
    show_api_error(error)
    st.stop()

if not courses:
    st.info("Aucune matière pour l'instant. Ajoutez-en une pour envoyer vos premiers cours.")
    st.stop()

for course in courses:
    label = f"{escape_markdown(course['name'])} · {DIFFICULTY_LABELS[course['difficulty']]}"
    with st.expander(label, icon=":material/school:"):
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
            f"« {course['name']} » sera supprimée avec ses documents, chapitres et échéances.",
        ):
            try:
                courses_api.delete_course(client, course["id"])
                flash("Matière supprimée.")
                st.rerun()
            except ApiError as error:
                show_api_error(error)
