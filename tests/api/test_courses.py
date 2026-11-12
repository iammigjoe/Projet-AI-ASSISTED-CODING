"""
===============================================================================
Tests : courses
===============================================================================
Objectif :
    Vérifier les routes des matières (contrat : GET /courses) : avancement en
    heures et en pourcentage, modification, suppression, unicité du nom, et
    isolation entre utilisateurs. La création par import de fichier
    (POST /courses) est testée par le lot B.

Lot :
    A (socle et sécurité)
===============================================================================
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import sessionmaker

from backend.db.models import Chapter, Document, Plan, StudySession
from backend.domain.enums import DocumentType, PlanOrigin, SessionStatus
from backend.services.course_service import CourseService

COURSES = "/courses"
START = datetime(2026, 11, 16, 17, 0, tzinfo=UTC)

# =============================================================================
# Fonctions internes
# =============================================================================


@pytest.fixture
def factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def alice(make_user):
    return make_user("alice@exemple.fr")


@pytest.fixture
def bob(make_user):
    return make_user("bob@exemple.fr")


def _course(factory, user, name="Analyse 2", chapter_minutes=(), done_minutes=()):
    """Crée une matière, ses chapitres et des sessions faites sur le premier chapitre."""
    session = factory()
    course = CourseService(session).create(user.id, name)
    document = Document(
        course_id=course.id,
        filename_original="cours.md",
        storage_key=f"{course.id}.md",
        type=DocumentType.MARKDOWN,
        size_bytes=100,
        sha256="a" * 64,
        uploaded_at=START,
    )
    session.add(document)
    session.flush()
    chapters = []
    for position, minutes in enumerate(chapter_minutes):
        chapter = Chapter(
            document_id=document.id,
            title=f"Chapitre {position + 1}",
            position=position,
            word_count=1000,
            estimated_min=minutes,
        )
        session.add(chapter)
        chapters.append(chapter)
    session.flush()
    if done_minutes:
        plan = Plan(user_id=user.id, version=1, week="2026-W47", origin=PlanOrigin.GENERATED)
        session.add(plan)
        session.flush()
        starts = START
        for minutes in done_minutes:
            session.add(
                StudySession(
                    plan_id=plan.id,
                    chapter_id=chapters[0].id,
                    starts_at=starts,
                    ends_at=starts + timedelta(minutes=minutes),
                    status=SessionStatus.DONE,
                )
            )
            starts += timedelta(days=1)
    session.commit()
    session.close()
    return course


# =============================================================================
# Lecture et avancement (contrat)
# =============================================================================


def test_list_courses_has_contract_fields(client, alice, auth_headers, factory):
    _course(factory, alice, chapter_minutes=(60, 120))

    course = client.get(COURSES, headers=auth_headers(alice.id)).json()[0]

    assert {"id", "name", "hours_total", "hours_done", "progress"} <= set(course)
    assert course["hours_total"] == 3.0
    assert course["hours_done"] == 0.0
    assert course["progress"] == 0.0


def test_progress_counts_done_sessions(client, alice, auth_headers, factory):
    _course(factory, alice, chapter_minutes=(60, 60, 120), done_minutes=(60, 30))

    course = client.get(COURSES, headers=auth_headers(alice.id)).json()[0]

    assert course["hours_total"] == 4.0
    assert course["hours_done"] == 1.5
    assert course["progress"] == 37.5


def test_progress_is_capped_at_100(client, alice, auth_headers, factory):
    _course(factory, alice, chapter_minutes=(60,), done_minutes=(60, 60))

    assert client.get(COURSES, headers=auth_headers(alice.id)).json()[0]["progress"] == 100.0


def test_course_without_chapters_has_zero_progress(client, alice, auth_headers, factory):
    _course(factory, alice)

    course = client.get(COURSES, headers=auth_headers(alice.id)).json()[0]

    assert (course["hours_total"], course["progress"]) == (0.0, 0.0)


def test_list_courses_is_sorted_by_name_ignoring_case(client, alice, auth_headers, factory):
    for name in ("physique", "Algèbre", "Chimie"):
        _course(factory, alice, name=name)

    response = client.get(COURSES, headers=auth_headers(alice.id))

    assert [course["name"] for course in response.json()] == ["Algèbre", "Chimie", "physique"]


def test_manual_json_creation_is_not_the_contract(client, alice, auth_headers):
    # POST /courses attend un fichier (lot B) : un corps JSON n'est pas accepté.
    response = client.post(
        COURSES, json={"name": "Analyse", "color": "#3366FF"}, headers=auth_headers(alice.id)
    )

    assert response.status_code in (405, 422)


# =============================================================================
# Modification et suppression
# =============================================================================


def test_update_course_changes_only_sent_fields(client, alice, auth_headers, factory):
    course = _course(factory, alice)

    response = client.patch(
        f"{COURSES}/{course.id}", json={"difficulty": 2}, headers=auth_headers(alice.id)
    )

    body = response.json()
    assert (body["name"], body["difficulty"], body["color"]) == ("Analyse 2", 2, "#3366FF")


@pytest.mark.parametrize(
    "payload",
    [
        {"name": ""},
        {"name": "x" * 101},
        {"color": "blue"},
        {"difficulty": 6},
        {"user_id": 99},
        {"name": "Ligne\nsuivante"},
    ],
    ids=["empty-name", "long-name", "bad-color", "difficulty", "user-id", "newline"],
)
def test_update_with_invalid_data_returns_422(client, alice, auth_headers, factory, payload):
    course = _course(factory, alice)

    response = client.patch(f"{COURSES}/{course.id}", json=payload, headers=auth_headers(alice.id))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_rename_to_existing_name_ignoring_case_returns_409(client, alice, auth_headers, factory):
    _course(factory, alice, name="Analyse 2")
    physics = _course(factory, alice, name="Physique")

    response = client.patch(
        f"{COURSES}/{physics.id}", json={"name": "ANALYSE 2"}, headers=auth_headers(alice.id)
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_html_in_name_is_stored_as_plain_text(client, alice, auth_headers, factory):
    course = _course(factory, alice)

    response = client.patch(
        f"{COURSES}/{course.id}",
        json={"name": "<script>alert(1)</script>"},
        headers=auth_headers(alice.id),
    )

    assert response.json()["name"] == "<script>alert(1)</script>"


def test_delete_course_removes_it(client, alice, auth_headers, factory):
    course = _course(factory, alice, chapter_minutes=(60,))
    headers = auth_headers(alice.id)

    assert client.delete(f"{COURSES}/{course.id}", headers=headers).status_code == 204
    assert client.get(f"{COURSES}/{course.id}", headers=headers).status_code == 404


# =============================================================================
# Authentification et isolation
# =============================================================================


def test_courses_require_authentication(client):
    assert client.get(COURSES).status_code == 401


def test_list_shows_only_own_courses(client, alice, bob, auth_headers, factory):
    _course(factory, alice, name="Analyse 2")
    _course(factory, bob, name="Histoire")

    response = client.get(COURSES, headers=auth_headers(bob.id))

    assert [course["name"] for course in response.json()] == ["Histoire"]


@pytest.mark.parametrize(
    ("method", "body"),
    [("get", None), ("patch", {"name": "Volé"}), ("delete", None)],
)
def test_other_users_course_returns_404(client, alice, bob, auth_headers, factory, method, body):
    course = _course(factory, alice)
    kwargs = {"headers": auth_headers(bob.id)} | ({"json": body} if body else {})

    response = getattr(client, method)(f"{COURSES}/{course.id}", **kwargs)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    owner_view = client.get(f"{COURSES}/{course.id}", headers=auth_headers(alice.id)).json()
    assert owner_view["name"] == "Analyse 2"
