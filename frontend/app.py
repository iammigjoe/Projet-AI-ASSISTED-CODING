"""
===============================================================================
Application : app
===============================================================================
Objectif :
    Point d'entrée Streamlit : configuration de la page, connexion obligatoire,
    menu des pages.

Responsabilités :
    - Sans connexion, seule la page de connexion est accessible.
    - Déclarer le menu avec st.navigation : titres en français, ordre fixe.
    - N'afficher que les pages dont le fichier existe : chaque lot crée sa page
      et elle apparaît, sans toucher à ce fichier.
    - Bouton de déconnexion dans la barre latérale.

Exemple d'utilisation :
    streamlit run frontend/app.py

Lot :
    A (socle et sécurité)
===============================================================================
"""

import sys
from pathlib import Path

# Streamlit ajoute le dossier du script (frontend/) au chemin d'import, pas la
# racine du projet : sans cette ligne, « import frontend… » échouerait.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from frontend.security import escape_markdown  # noqa: E402
from frontend.session import current_user, is_logged_in, logout  # noqa: E402

# =============================================================================
# Constantes
# =============================================================================

# Surtout pas « pages/ » : Streamlit exécuterait directement tout fichier d'un
# dossier pages/ voisin du point d'entrée, sans passer par ce fichier ni par la
# vérification de connexion.
PAGES_DIR = Path(__file__).resolve().parent / "views"

# (fichier, titre affiché, icône) dans l'ordre du menu. Une page dont le fichier
# n'existe pas encore est ignorée (conventions §3).
MENU = (
    ("courses.py", "Matières", ":material/school:"),
    ("documents.py", "Importer", ":material/upload_file:"),
    ("availabilities.py", "Disponibilités", ":material/event_available:"),
    ("deadlines.py", "Échéances", ":material/flag:"),
    ("plan.py", "Planning", ":material/calendar_month:"),
    ("dashboard.py", "Tableau de bord", ":material/insights:"),
    ("settings.py", "Paramètres", ":material/tune:"),
)

# =============================================================================
# Application
# =============================================================================

st.set_page_config(page_title="MyPlan", page_icon=":material/menu_book:", layout="wide")

if not is_logged_in():
    navigation = st.navigation([st.Page(PAGES_DIR / "login.py", title="Connexion")])
else:
    pages = [
        st.Page(PAGES_DIR / filename, title=title, icon=icon)
        for filename, title, icon in MENU
        if (PAGES_DIR / filename).exists()
    ]
    navigation = st.navigation(pages)

    user = current_user()
    with st.sidebar:
        if user:
            st.caption(f"Connecté : {escape_markdown(user['email'])}")
        if st.button("Se déconnecter", icon=":material/logout:"):
            logout()
            st.rerun()

navigation.run()
