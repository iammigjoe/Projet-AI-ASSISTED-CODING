"""
===============================================================================
Module : state
===============================================================================
Objectif :
    Déclarer les clés de st.session_state, pour qu'aucune page n'écrive une clé
    en dur (conventions §3).

Exemple d'utilisation :
    st.session_state[ACCESS_TOKEN] = tokens["access_token"]

Lot :
    A (socle et sécurité) ; chaque lot ajoute ses clés à la fin du fichier.
===============================================================================
"""

# =============================================================================
# Constantes
# =============================================================================

# Noms de clés, pas des secrets : ruff (S105) les prend pour des mots de passe.
ACCESS_TOKEN = "access_token"  # noqa: S105
REFRESH_TOKEN = "refresh_token"  # noqa: S105
CURRENT_USER = "current_user"
