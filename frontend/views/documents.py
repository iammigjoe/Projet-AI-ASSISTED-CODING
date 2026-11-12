"""
===============================================================================
Page : Importer
===============================================================================
Objectif :
    Importer des cours (PDF ou Markdown) : chaque fichier devient une matière,
    avec ses chapitres et une charge en heures (bloc 1).

Appelle :
    documents_api.import_course

Notes :
    - Plusieurs fichiers à la fois ; l'échec de l'un n'empêche pas les autres.
    - Noms de fichiers et titres de chapitres viennent de l'utilisateur :
      échappés avant tout affichage en Markdown.
    - Le filtre .pdf / .md du navigateur n'est qu'un confort : l'API vérifie
      le contenu réel du fichier.

Lot :
    B (import) ; écrite par le lot A pour débloquer la démo.
===============================================================================
"""

import streamlit as st

from frontend.api import documents_api
from frontend.api.base import ApiError, get_client
from frontend.components.ui import page_header, show_flash
from frontend.security import escape_markdown

# =============================================================================
# Constantes
# =============================================================================

# Aligné sur MYPLAN_MAX_UPLOAD_BYTES et .streamlit/config.toml (maxUploadSize).
MAX_UPLOAD_MB = 20

# =============================================================================
# Page
# =============================================================================

page_header(
    "Importer un cours",
    "Envoyez un PDF ou un fichier Markdown : MyPlan en tire les chapitres et une "
    "charge en heures (au moins 1 h par chapitre).",
)
show_flash()
client = get_client()

uploads = st.file_uploader(
    "Fichiers de cours",
    type=["pdf", "md"],
    accept_multiple_files=True,
    help=f"PDF ou Markdown, {MAX_UPLOAD_MB} Mo au plus par fichier.",
)

if st.button("Importer", type="primary", disabled=not uploads):
    imported = 0
    for upload in uploads:
        name = escape_markdown(upload.name)
        try:
            course = documents_api.import_course(client, upload.name, upload.getvalue())
        except ApiError as error:
            st.error(f"{name} : {escape_markdown(error.message)}")
            continue

        imported += 1
        chapters = course["chapters"]
        st.success(
            f"{name} → « {escape_markdown(course['name'])} » : "
            f"{len(chapters)} chapitre(s), {course['hours_total']:g} h"
        )
        # st.dataframe n'interprète pas le contenu : pas d'échappement nécessaire.
        st.dataframe(
            [{"Chapitre": chapter["title"], "Heures": chapter["hours"]} for chapter in chapters],
            hide_index=True,
            use_container_width=True,
        )

    if imported:
        st.page_link(
            "views/courses.py", label="Voir l'avancement des matières", icon=":material/school:"
        )
