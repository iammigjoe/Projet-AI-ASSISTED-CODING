"""
===============================================================================
Tests : security (frontend)
===============================================================================
Objectif :
    Vérifier qu'un texte échappé ne produit ni lien, ni image, ni HTML une
    fois rendu en Markdown, et s'affiche à l'identique.

Lot :
    A (socle et sécurité)
===============================================================================
"""

import pytest
from markdown_it import MarkdownIt

from frontend.security import escape_markdown

_renderer = MarkdownIt("commonmark", {"html": True}).enable("table").enable("strikethrough")


def _render(text: str) -> str:
    return _renderer.render(text)


@pytest.mark.parametrize(
    "payload",
    [
        "[cliquez](javascript:alert(1))",
        "![image](https://tracker.example/pixel.png)",
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "<https://phishing.example>",
        "**gras** _italique_ ~~barré~~",
        "# Faux titre",
        "| a | b |\n|---|---|\n| 1 | 2 |",
        "    code indenté",
    ],
    ids=[
        "js-link",
        "image",
        "script",
        "img-onerror",
        "autolink",
        "emphasis",
        "heading",
        "table",
        "indent",
    ],
)
def test_escaped_text_renders_without_markup(payload):
    html = _render(escape_markdown(payload))

    for tag in ("<a ", "<img", "<script", "<strong", "<em", "<h1", "<table", "<code", "<del"):
        assert tag not in html, (payload, html)


def test_escaped_text_keeps_visible_characters():
    title = "Chapitre 3 : f(x) = x² + 1 [rappel]"

    rendered = _render(escape_markdown(title))

    assert "f(x) = x² + 1 [rappel]" in rendered


def test_invisible_direction_characters_are_removed():
    assert "‮" not in escape_markdown("fichier‮gnp.exe")


def test_none_becomes_empty_text():
    assert escape_markdown(None) == ""
