"""
===============================================================================
Tests : settings
===============================================================================
Objectif :
    Vérifier la lecture et la modification du profil d'étude (P0-08), ses
    valeurs par défaut et ses bornes.

Lot :
    A (socle et sécurité)
===============================================================================
"""

import pytest

SETTINGS = "/api/v1/settings"


@pytest.fixture
def headers(make_user, auth_headers):
    return auth_headers(make_user().id)


def test_new_account_has_default_settings(client, headers):
    response = client.get(SETTINGS, headers=headers)

    assert response.json() == {
        "reading_speed_wpm": 200,
        "max_session_min": 90,
        "break_min": 15,
        "mastery_goal": "standard",
        "retention_threshold": 0.7,
    }


def test_update_changes_only_sent_fields(client, headers):
    response = client.patch(
        SETTINGS, json={"max_session_min": 60, "mastery_goal": "mastery"}, headers=headers
    )

    body = response.json()
    assert (body["max_session_min"], body["mastery_goal"]) == (60, "mastery")
    assert body["reading_speed_wpm"] == 200
    assert client.get(SETTINGS, headers=headers).json() == body


@pytest.mark.parametrize(
    "payload",
    [
        {"max_session_min": 5},
        {"max_session_min": 600},
        {"reading_speed_wpm": 0},
        {"break_min": -1},
        {"mastery_goal": "expert"},
        {"retention_threshold": 1.5},
        {"notif_prefs": {"channel": "sms"}},
    ],
    ids=["session-short", "session-long", "speed", "break", "goal", "threshold", "unknown"],
)
def test_invalid_settings_return_422(client, headers, payload):
    response = client.patch(SETTINGS, json=payload, headers=headers)

    assert response.status_code == 422


def test_settings_require_authentication(client):
    assert client.get(SETTINGS).status_code == 401


def test_each_user_sees_only_own_settings(client, make_user, auth_headers):
    alice = auth_headers(make_user("alice@exemple.fr").id)
    bob = auth_headers(make_user("bob@exemple.fr").id)

    client.patch(SETTINGS, json={"reading_speed_wpm": 300}, headers=alice)

    assert client.get(SETTINGS, headers=bob).json()["reading_speed_wpm"] == 200
