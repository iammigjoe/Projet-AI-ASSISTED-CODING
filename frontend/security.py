"""
===============================================================================
Module : security (frontend)
===============================================================================
Objectif :
    Afficher le texte des utilisateurs et des cours sans qu'il soit interprété
    par Streamlit (XSS, liens piégés, mise en page détournée).

Responsabilités :
    - Échapper la syntaxe Markdown d'un texte : st.markdown, st.write et les
      libellés de nombreux composants interprètent le Markdown, et un titre de
      chapitre extrait d'un PDF peut contenir « [cliquez](javascript:...) » ou
      une image qui charge une adresse externe.
    - Retirer les caractères invisibles de direction avant affichage.

Notes :
    - Règle complète : docs/securite.md. Le HTML brut (unsafe_allow_html,
      st.html, components.html) est interdit dans frontend/ et vérifié par
      tests/frontend/test_no_raw_html.py.
    - st.text, st.code et st.dataframe n'interprètent rien : pas besoin
      d'échapper ce qu'on leur passe.

Utilisé par :
    Toutes les pages et composants qui affichent un texte saisi ou extrait.

Exemple d'utilisation :
    st.markdown(f"**Chapitre :** {escape_markdown(chapter['title'])}")

Lot :
    A (socle et sécurité)
===============================================================================
"""

import re

# =============================================================================
# Constantes
# =============================================================================

# Tout caractère qui a un sens en Markdown (CommonMark, GFM) ou en HTML.
_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~=$&:\"'])")
_INVISIBLE_CHARS = re.compile(r"[​-‏‪-‮⁦-⁩﻿]")

# =============================================================================
# API publique
# =============================================================================


def escape_markdown(text: object) -> str:
    """Rend un texte inerte pour st.markdown et les libellés de composants.

    Args:
        text: Valeur à afficher ; convertie en texte si besoin, None devient vide.

    Returns:
        Le texte, avec chaque caractère spécial du Markdown échappé et les
        caractères invisibles retirés. Il s'affiche à l'identique, sans lien,
        image, mise en forme ni HTML.
    """
    if text is None:
        return ""
    cleaned = _INVISIBLE_CHARS.sub("", str(text))
    # Les retours à la ligne gardent leur sens, mais pas l'indentation, qui
    # transformerait un paragraphe en bloc de code.
    lines = [_MARKDOWN_SPECIAL.sub(r"\\\1", line.strip()) for line in cleaned.splitlines()]
    return "  \n".join(lines)
