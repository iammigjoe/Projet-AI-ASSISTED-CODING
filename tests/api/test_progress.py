"""
===============================================================================
Tests API : progress et study-sessions
===============================================================================
Objectif :
    Vérifier la mise à jour des statuts, l'isolation utilisateur et RG12.

Lot :
    D (agenda et suivi)
===============================================================================
"""

from datetime import datetime

from backend.db.models import Chapter, Course, Document, Plan, StudySession, User
from backend.domain.enums import (
    DocumentType,
    PlanOrigin,
    PlanStatus,
    SessionStatus,
)
from tests.fixtures.factories import DEFAULT_SESSION_START, make_study_session


def _create_chapter(db_session, email: str, suffix: str) -> tuple[User, Chapter]:
    user = User(email=email, password_hash="argon2-hash")
    db_session.add(user)
    db_session.flush()

    course = Course(user_id=user.id, name=f"Mathématiques {suffix}", color="#3366FF")
    db_session.add(course)
    db_session.flush()

    document = Document(
        course_id=course.id,
        filename_original="cours.pdf",
        storage_key=f"{suffix}-document.pdf",
        type=DocumentType.PDF,
        size_bytes=1024,
        sha256=suffix.encode().hex().ljust(64, "0")[:64],
        uploaded_at=DEFAULT_SESSION_START,
    )
    db_session.add(document)
    db_session.flush()

    chapter = Chapter(
        document_id=document.id,
        title=f"Chapitre {suffix}",
        position=0,
        word_count=1000,
        estimated_min=60,
    )
    db_session.add(chapter)
    db_session.flush()
    return user, chapter


def _create_plan(db_session, user: User, version: int, status: PlanStatus) -> Plan:
    plan = Plan(
        user_id=user.id,
        version=version,
        status=status,
        origin=PlanOrigin.GENERATED,
    )
    db_session.add(plan)
    db_session.flush()
    return plan


def _create_session(
    db_session,
    plan: Plan,
    chapter: Chapter,
    *,
    status: SessionStatus,
    duration_min: int = 45,
) -> StudySession:
    study_session = make_study_session(
        plan_id=plan.id,
        chapter_id=chapter.id,
        duration_min=duration_min,
        status=status,
        completed_at=DEFAULT_SESSION_START if status is SessionStatus.DONE else None,
    )
    db_session.add(study_session)
    db_session.flush()
    return study_session


def test_patch_study_session_marks_done_and_missed(client, db_session, auth_headers):
    user, chapter = _create_chapter(db_session, "alice@example.test", "alice")
    plan = _create_plan(db_session, user, 1, PlanStatus.ACTIVE)
    study_session = _create_session(db_session, plan, chapter, status=SessionStatus.PLANNED)
    db_session.commit()

    response = client.patch(
        f"/api/v1/study-sessions/{study_session.id}",
        headers=auth_headers(user.id),
        json={"status": "done"},
    )

    assert response.status_code == 200
    done = response.json()
    assert done["status"] == "done"
    assert done["completed_at"] is not None

    response = client.patch(
        f"/api/v1/study-sessions/{study_session.id}",
        headers=auth_headers(user.id),
        json={"status": "missed"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "missed"
    assert response.json()["completed_at"] is None


def test_patch_study_session_hides_another_users_session(client, db_session, auth_headers):
    owner, chapter = _create_chapter(db_session, "owner@example.test", "owner")
    plan = _create_plan(db_session, owner, 1, PlanStatus.ACTIVE)
    study_session = _create_session(db_session, plan, chapter, status=SessionStatus.PLANNED)
    other_user, _ = _create_chapter(db_session, "other@example.test", "other")
    db_session.commit()

    response = client.patch(
        f"/api/v1/study-sessions/{study_session.id}",
        headers=auth_headers(other_user.id),
        json={"status": "done"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_get_progress_sums_done_sessions_across_plans_for_current_user(
    client, db_session, auth_headers
):
    user, chapter = _create_chapter(db_session, "alice@example.test", "alice")
    first_plan = _create_plan(db_session, user, 1, PlanStatus.ARCHIVED)
    second_plan = _create_plan(db_session, user, 2, PlanStatus.ACTIVE)
    _create_session(db_session, first_plan, chapter, status=SessionStatus.DONE, duration_min=30)
    _create_session(db_session, second_plan, chapter, status=SessionStatus.DONE, duration_min=45)
    _create_session(db_session, second_plan, chapter, status=SessionStatus.MISSED, duration_min=60)

    other_user, other_chapter = _create_chapter(db_session, "bob@example.test", "bob")
    other_plan = _create_plan(db_session, other_user, 1, PlanStatus.ACTIVE)
    _create_session(db_session, other_plan, other_chapter, status=SessionStatus.DONE)
    db_session.commit()

    response = client.get("/api/v1/progress", headers=auth_headers(user.id))

    assert response.status_code == 200
    assert response.json() == [{"chapter_id": chapter.id, "completed_minutes": 75.0}]


def test_patch_done_session_preserves_original_completion_time(client, db_session, auth_headers):
    user, chapter = _create_chapter(db_session, "alice@example.test", "alice")
    plan = _create_plan(db_session, user, 1, PlanStatus.ACTIVE)
    study_session = _create_session(db_session, plan, chapter, status=SessionStatus.DONE)
    original_completed_at = study_session.completed_at
    db_session.commit()

    response = client.patch(
        f"/api/v1/study-sessions/{study_session.id}",
        headers=auth_headers(user.id),
        json={"status": "done"},
    )

    assert response.status_code == 200
    assert datetime.fromisoformat(response.json()["completed_at"]) == original_completed_at


def test_patch_study_session_rejects_planned_status(client, db_session, auth_headers):
    user, chapter = _create_chapter(db_session, "alice@example.test", "alice")
    plan = _create_plan(db_session, user, 1, PlanStatus.ACTIVE)
    study_session = _create_session(db_session, plan, chapter, status=SessionStatus.PLANNED)
    db_session.commit()

    response = client.patch(
        f"/api/v1/study-sessions/{study_session.id}",
        headers=auth_headers(user.id),
        json={"status": "planned"},
    )

    assert response.status_code == 422
