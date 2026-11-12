"""
===============================================================================
Tests : schemas common
===============================================================================
Objectif :
    Vérifier que les types de texte partagés nettoient, bornent et refusent les
    caractères dangereux.

Lot :
    A (socle et sécurité)
===============================================================================
"""

import pytest
from pydantic import BaseModel, ValidationError

from backend.api.schemas.common import EmailAddress, MultilineText, SingleLineText


class _Form(BaseModel):
    name: SingleLineText[20]
    notes: MultilineText[200] | None = None
    email: EmailAddress | None = None


def test_single_line_text_is_stripped_and_normalized():
    # « e » + accent combinant devient « é » (NFC).
    assert _Form(name="  Résumé  ").name == "Résumé"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "x" * 21,
        "line one\nline two",
        "tab\tinside",
        "null\x00byte",
        "fichier‮gnp.exe",
        "zero​width",
    ],
    ids=["empty", "blank", "too-long", "newline", "tab", "nul", "rtl-override", "zero-width"],
)
def test_single_line_text_refuses_dangerous_values(value):
    with pytest.raises(ValidationError):
        _Form(name=value)


def test_html_is_kept_as_plain_data():
    # Pas de filtrage du HTML à l'entrée : il est échappé à l'affichage.
    assert _Form(name="<b>Analyse</b>").name == "<b>Analyse</b>"


def test_multiline_text_keeps_line_breaks():
    assert _Form(name="ok", notes="ligne 1\r\nligne 2").notes == "ligne 1\nligne 2"


def test_email_is_lowercased():
    assert _Form(name="ok", email=" Alice@Exemple.FR ").email == "alice@exemple.fr"


@pytest.mark.parametrize("value", ["alice", "alice@", "@exemple.fr", "a b@exemple.fr"])
def test_invalid_email_is_refused(value):
    with pytest.raises(ValidationError):
        _Form(name="ok", email=value)
