"""
===============================================================================
Tests : courses
===============================================================================
Objectif :
    Vérifier la gestion des matières (P0-02) : création, lecture, modification,
    suppression, unicité du nom, et isolation entre utilisateurs.

Lot :
    A (socle et sécurité)
===============================================================================
"""

import pytest

COURSES = "/api/v1/courses"


@pytest.fixture
def alice(make_user, auth_headers):
    user = make_user("alice@exemple.fr")
    return auth_headers(user.id)


@pytest.fixture
def bob(make_user, auth_headers):
    user = make_user("bob@exemple.fr")
    return auth_headers(user.id)


def _create(client, headers, name="Analyse 2", color="#3366ff", difficulty=4):
    return client.post(
        COURSES, json={"name": name, "color": color, "difficulty": difficulty}, headers=headers
    )


# =============================================================================
# Création et lecture
# =============================================================================


def test_create_course_returns_it_with_normalized_color(client, alice):
    response = _create(client, alice)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Analyse 2"
    assert body["color"] == "#3366FF"
    assert body["difficulty"] == 4


def test_create_course_uses_default_difficulty(client, alice):
    response = client.post(COURSES, json={"name": "Physique", "color": "#00AA00"}, headers=alice)

    assert response.json()["difficulty"] == 3


def test_list_courses_is_sorted_by_name_ignoring_case(client, alice):
    for name in ("physique", "Algèbre", "Chimie"):
        _create(client, alice, name=name)

    names = [course["name"] for course in client.get(COURSES, headers=alice).json()]

    assert names == ["Algèbre", "Chimie", "physique"]


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "color": "#3366FF"},
        {"name": "x" * 101, "color": "#3366FF"},
        {"name": "Analyse", "color": "blue"},
        {"name": "Analyse", "color": "#3366FF", "difficulty": 6},
        {"name": "Analyse", "color": "#3366FF", "user_id": 99},
        {"name": "Ligne\nsuivante", "color": "#3366FF"},
    ],
    ids=["empty-name", "long-name", "bad-color", "difficulty", "user-id", "newline"],
)
def test_create_course_with_invalid_data_returns_422(client, alice, payload):
    response = client.post(COURSES, json=payload, headers=alice)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_duplicate_name_ignoring_case_returns_409(client, alice):
    _create(client, alice, name="Analyse 2")

    response = _create(client, alice, name="analyse 2")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_html_in_name_is_stored_as_plain_text(client, alice):
    response = _create(client, alice, name="<script>alert(1)</script>")

    assert response.json()["name"] == "<script>alert(1)</script>"


# =============================================================================
# Modification et suppression
# =============================================================================


def test_update_course_changes_only_sent_fields(client, alice):
    course = _create(client, alice).json()

    response = client.patch(f"{COURSES}/{course['id']}", json={"difficulty": 2}, headers=alice)

    assert response.json() == {**course, "difficulty": 2}


def test_rename_to_existing_name_returns_409(client, alice):
    _create(client, alice, name="Analyse 2")
    physics = _create(client, alice, name="Physique").json()

    response = client.patch(f"{COURSES}/{physics['id']}", json={"name": "ANALYSE 2"}, headers=alice)

    assert response.status_code == 409


def test_rename_keeping_own_name_is_allowed(client, alice):
    course = _create(client, alice, name="Analyse 2").json()

    response = client.patch(
        f"{COURSES}/{course['id']}", json={"name": "Analyse 2", "color": "#000000"}, headers=alice
    )

    assert response.status_code == 200


def test_delete_course_removes_it(client, alice):
    course = _create(client, alice).json()

    assert client.delete(f"{COURSES}/{course['id']}", headers=alice).status_code == 204
    assert client.get(f"{COURSES}/{course['id']}", headers=alice).status_code == 404


# =============================================================================
# Authentification et isolation
# =============================================================================


def test_courses_require_authentication(client):
    assert client.get(COURSES).status_code == 401


def test_list_shows_only_own_courses(client, alice, bob):
    _create(client, alice, name="Analyse 2")
    _create(client, bob, name="Histoire")

    names = [course["name"] for course in client.get(COURSES, headers=bob).json()]

    assert names == ["Histoire"]


def test_same_name_is_allowed_for_different_users(client, alice, bob):
    _create(client, alice, name="Analyse 2")

    assert _create(client, bob, name="Analyse 2").status_code == 201


@pytest.mark.parametrize(
    ("method", "body"),
    [("get", None), ("patch", {"name": "Volé"}), ("delete", None)],
)
def test_other_users_course_returns_404(client, alice, bob, method, body):
    course = _create(client, alice).json()
    kwargs = {"headers": bob} | ({"json": body} if body else {})

    response = getattr(client, method)(f"{COURSES}/{course['id']}", **kwargs)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert client.get(f"{COURSES}/{course['id']}", headers=alice).json()["name"] == "Analyse 2"
