"""
===============================================================================
Tests frontend : session_card
===============================================================================
Objectif :
    Vérifier le rendu sûr et l'appel API du composant de suivi.

Lot :
    D (agenda et suivi)
===============================================================================
"""

from contextlib import nullcontext
from unittest.mock import Mock

from frontend.components import session_card


def test_session_card_escapes_chapter_title_and_displays_local_time(monkeypatch):
    markdown = Mock()
    caption = Mock()
    columns = [Mock(), Mock()]
    for column in columns:
        column.button.return_value = False
    monkeypatch.setattr(session_card.st, "container", lambda **_kwargs: nullcontext())
    monkeypatch.setattr(session_card.st, "markdown", markdown)
    monkeypatch.setattr(session_card.st, "caption", caption)
    monkeypatch.setattr(session_card.st, "info", Mock())
    monkeypatch.setattr(session_card.st, "columns", lambda _count: columns)

    session_card.render_session_card(
        {
            "id": 7,
            "chapter_id": 2,
            "chapter_title": "[cours](https://example.test)",
            "starts_at": "2026-11-16T17:00:00Z",
            "ends_at": "2026-11-16T17:45:00Z",
            "status": "planned",
        },
        "Europe/Paris",
    )

    assert "](https" not in markdown.call_args.args[0]
    assert caption.call_args.args[0] == "16/11/2026 18:00 – 18:45"


def test_session_card_updates_status_and_reruns_on_success(monkeypatch):
    buttons = [Mock(), Mock()]
    buttons[0].button.return_value = True
    buttons[1].button.return_value = False
    update = Mock()
    rerun = Mock()
    monkeypatch.setattr(session_card.st, "container", lambda **_kwargs: nullcontext())
    monkeypatch.setattr(session_card.st, "markdown", Mock())
    monkeypatch.setattr(session_card.st, "caption", Mock())
    monkeypatch.setattr(session_card.st, "info", Mock())
    monkeypatch.setattr(session_card.st, "columns", lambda _count: buttons)
    monkeypatch.setattr(session_card, "update_study_session", update)
    monkeypatch.setattr(session_card.st, "rerun", rerun)

    session_card.render_session_card(
        {
            "id": 7,
            "chapter_id": 2,
            "starts_at": "2026-11-16T17:00:00Z",
            "ends_at": "2026-11-16T17:45:00Z",
            "status": "planned",
        },
        "UTC",
    )

    update.assert_called_once_with(7, "done")
    rerun.assert_called_once_with()
